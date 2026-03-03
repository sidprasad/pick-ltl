from __future__ import annotations

import re

from ..llm.base import ProviderError
from ..llm.manager import build_provider
from ..ltl.ltlnode import parse_ltl_string
from ..ltl.traceprocessor import getFormulaLiterals
from ..session.models import AtomSpec, SeedFormulaResult


ATOM_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


SEED_SYSTEM_PROMPT = """You turn natural-language temporal requirements into a single LTL formula.
Return only one JSON object with keys:
- formula: one LTL formula
- explanation: short explanation
- atoms: array of {name, meaning}
- warnings: optional short warnings

Rules:
- Output valid JSON only.
- Produce exactly one formula.
- Use only short proposition names.
- Do not return alternatives.
- No Markdown fences.
"""


def _normalize_atoms(formula: str, raw_atoms: list[dict]) -> list[AtomSpec]:
    atoms: list[AtomSpec] = []
    seen: set[str] = set()
    for item in raw_atoms:
        atom = AtomSpec.from_dict(item if isinstance(item, dict) else {})
        if not atom.name or atom.name in seen or not ATOM_RE.match(atom.name):
            continue
        if not atom.meaning:
            atom.meaning = atom.name
        atoms.append(atom)
        seen.add(atom.name)

    formula_atoms = sorted(getFormulaLiterals(formula))
    for atom_name in formula_atoms:
        if atom_name not in seen:
            atoms.append(AtomSpec(name=atom_name, meaning=atom_name))
            seen.add(atom_name)
    return atoms


def generate_seed_formula(prompt: str, provider_payload: dict) -> SeedFormulaResult:
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    provider = build_provider(provider_payload)
    payload = provider.complete_json(SEED_SYSTEM_PROMPT, f"Description:\n{prompt.strip()}")
    formula = str(payload.get("formula", "")).strip()
    if not formula:
        raise ProviderError("Model did not return a formula.")

    formula = str(parse_ltl_string(formula))
    explanation = str(payload.get("explanation", "")).strip() or "Seed formula proposed by the language model."
    atoms = _normalize_atoms(formula, payload.get("atoms", []))
    warnings = [str(item).strip() for item in payload.get("warnings", []) if str(item).strip()]
    return SeedFormulaResult(formula=formula, explanation=explanation, atoms=atoms, warnings=warnings)

