from __future__ import annotations

import random
from contextlib import contextmanager

from ..ltl.ltlnode import LTLNode, parse_ltl_string
from ..ltl.traceprocessor import getFormulaLiterals
from ..mutation.ranking import rank_formulas
from ..mutation.semantic import MisconceptionCode, getAllApplicableMisconceptions
from ..mutation.syntactic import applyRandomMutationNotEquivalentTo
from ..session.models import CandidateFormulaState, CandidateOrigin, SeedFormulaResult, SessionState


MUTATION_EXPLANATIONS = {
    MisconceptionCode.Precedence.value: "Groups one part of the rule differently from the main interpretation.",
    MisconceptionCode.BadStateIndex.value: "Shifts when a sub-rule is expected to happen.",
    MisconceptionCode.BadStateQuantification.value: "Changes whether part of the property is meant to hold always or eventually.",
    MisconceptionCode.ExclusiveU.value: "Treats the until-condition as more exclusive than the seed interpretation.",
    MisconceptionCode.ImplicitF.value: "Drops an eventuality requirement from the seed interpretation.",
    MisconceptionCode.ImplicitG.value: "Drops an always/for-all-future requirement from the seed interpretation.",
    MisconceptionCode.OtherImplicit.value: "Under-constrains the seed interpretation by removing part of the temporal structure.",
    MisconceptionCode.WeakU.value: "Reads an until-condition as if the right side may never need to happen.",
}


@contextmanager
def deterministic_random(seed: str):
    state = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(state)


def _normalize_formula(formula: str, allowed_atoms: set[str]) -> str | None:
    try:
        normalized = str(parse_ltl_string(formula))
    except Exception:
        return None

    if allowed_atoms and not set(getFormulaLiterals(normalized)).issubset(allowed_atoms):
        return None
    return normalized


def _is_equivalent(formula: str, existing: list[str]) -> bool:
    return any(LTLNode.equiv(formula, other) for other in existing)


def build_candidates(seed: SeedFormulaResult, target_count: int = 4) -> list[CandidateFormulaState]:
    node = parse_ltl_string(seed.formula)
    allowed_atoms = {atom.name for atom in seed.atoms}

    candidates = [
        CandidateFormulaState(
            formula=seed.formula,
            explanation=seed.explanation,
            origin=CandidateOrigin(kind="seed"),
        )
    ]
    seen_formulas = [seed.formula]
    semantic_pool: list[dict] = []

    with deterministic_random(seed.formula):
        for result in getAllApplicableMisconceptions(node):
            formula = _normalize_formula(str(result.node), allowed_atoms)
            if not formula or formula in seen_formulas or _is_equivalent(formula, seen_formulas):
                continue
            code = result.misconception.value
            semantic_pool.append(
                {
                    "formula": formula,
                    "explanation": MUTATION_EXPLANATIONS.get(
                        code,
                        "Conceptual variant of the main interpretation.",
                    ),
                    "origin": CandidateOrigin(kind="semantic_mutation", misconception_code=code),
                    "equivalents": [],
                }
            )

    for item in rank_formulas(seed.formula, semantic_pool):
        if len(candidates) >= target_count:
            break
        seen_formulas.append(item["formula"])
        candidates.append(
            CandidateFormulaState(
                formula=item["formula"],
                explanation=item["explanation"],
                origin=item["origin"],
            )
        )

    attempts = 0
    existing_nodes = [parse_ltl_string(candidate.formula) for candidate in candidates]
    while len(candidates) < target_count and attempts < 32:
        attempts += 1
        with deterministic_random(f"{seed.formula}:{attempts}"):
            mutated = applyRandomMutationNotEquivalentTo(node, existing_nodes, maxAttempts=32)
        if mutated is None:
            continue
        formula = _normalize_formula(str(mutated), allowed_atoms)
        if not formula or formula in seen_formulas or _is_equivalent(formula, seen_formulas):
            continue
        seen_formulas.append(formula)
        existing_nodes.append(parse_ltl_string(formula))
        candidates.append(
            CandidateFormulaState(
                formula=formula,
                explanation="Operator-level variant of the main interpretation.",
                origin=CandidateOrigin(kind="syntactic_mutation", misconception_code=None),
            )
        )

    return candidates


def create_initial_session(prompt: str, provider: dict, seed: SeedFormulaResult, target_count: int = 4) -> SessionState:
    candidates = build_candidates(seed, target_count=target_count)
    mode = "voting"
    message = ""
    if len(candidates) == 1:
        mode = "single_candidate"
        message = "We could only get this one."

    return SessionState(
        prompt=prompt,
        provider=provider,
        seed=seed,
        candidate_states=candidates,
        warnings=list(seed.warnings),
        mode=mode,
        message=message,
    )

