from __future__ import annotations

import re

from ..llm.base import ProviderError
from ..llm.manager import build_provider
from ..ltl.ltlnode import LTLParseError, parse_ltl_string
from ..ltl.traceprocessor import getFormulaLiterals
from ..session.models import AtomSpec, SeedFormulaResult


ATOM_RE = re.compile(r"^[a-z0-9]+$")
FORMULA_PREFIX_RE = re.compile(r"^(?:ltl|formula)\s*:\s*", re.IGNORECASE)
FORMULA_TOKEN_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
ESCAPED_OPERATOR_RE = re.compile(r"\\+(X|AFTER|NEXT_STATE|F|EVENTUALLY|G|ALWAYS|U|UNTIL)\b", re.IGNORECASE)
UNICODE_REPLACEMENTS = {
    "¬": "!",
    "∧": "&",
    "∨": "|",
    "→": "->",
    "⇒": "->",
    "↔": "<->",
    "◇": "F",
    "□": "G",
}
OPERATOR_WORDS = {"X", "AFTER", "NEXT_STATE", "F", "EVENTUALLY", "G", "ALWAYS", "U", "UNTIL"}


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
- Use ASCII LTL syntax, not LaTeX.
- Use lowercase proposition names like r, b, p1.
- Do not use backslashes anywhere in the formula.
- Do not escape operators or parentheses.
- Valid example formula: G(r -> F(b))
- Invalid example formulas: \\G (r \\U b), \\(G(r)\\), $G(r)$
- Do not return alternatives.
- No Markdown fences.
"""


def _normalize_atom_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return normalized


def _normalize_formula_token(match: re.Match[str]) -> str:
    token = match.group(0)
    upper = token.upper()
    if upper in OPERATOR_WORDS:
        return upper
    return _normalize_atom_name(token)


def _sanitize_formula(formula: str) -> str:
    normalized = str(formula).strip()
    normalized = normalized.strip("`$")
    normalized = normalized.replace("\\\\", "\\")
    normalized = normalized.replace("\\(", "(").replace("\\)", ")")
    normalized = normalized.replace("\\[", "(").replace("\\]", ")")
    normalized = normalized.replace("\\{", "(").replace("\\}", ")")
    normalized = ESCAPED_OPERATOR_RE.sub(lambda match: match.group(1).upper(), normalized)
    for source, target in UNICODE_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    if normalized.startswith("```") and normalized.endswith("```"):
        normalized = "\n".join(normalized.splitlines()[1:-1]).strip()
    normalized = FORMULA_PREFIX_RE.sub("", normalized).strip()
    normalized = FORMULA_TOKEN_RE.sub(_normalize_formula_token, normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _normalize_atoms(formula: str, raw_atoms: list[dict]) -> list[AtomSpec]:
    atoms: list[AtomSpec] = []
    seen: set[str] = set()
    for item in raw_atoms:
        atom = AtomSpec.from_dict(item if isinstance(item, dict) else {})
        atom.name = _normalize_atom_name(atom.name)
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

    normalized_formula = _sanitize_formula(formula)
    try:
        formula = str(parse_ltl_string(normalized_formula))
    except LTLParseError as exc:
        raise ProviderError(
            "Model returned an invalid LTL formula. "
            "Try a more instruction-following model, revise the prompt, or use a model that follows structured output more reliably. "
            f"Received: {formula!r}"
        ) from exc
    explanation = str(payload.get("explanation", "")).strip() or "Seed formula proposed by the language model."
    atoms = _normalize_atoms(formula, payload.get("atoms", []))
    warnings = [str(item).strip() for item in payload.get("warnings", []) if str(item).strip()]
    return SeedFormulaResult(formula=formula, explanation=explanation, atoms=atoms, warnings=warnings)
