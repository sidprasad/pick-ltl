from __future__ import annotations

import json
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


SEED_SYSTEM_PROMPT = """You are an LTL-generation assistant.
Given a natural-language temporal requirement, generate exactly one plausible LTL formula and a small atom glossary.

Return ONLY a single JSON object with this shape:
{
  "formula": "<LTL_FORMULA>",
  "explanation": "<SHORT_EXPLANATION>",
  "atoms": [
    {"name": "<atom>", "meaning": "<what it means>"}
  ],
  "warnings": ["<optional warning 1>", "<optional warning 2>"]
}

Output rules:
- Output must be valid JSON. No backticks, comments, or extra text.
- Return exactly one formula, not alternatives.
- "formula" must be a string.
- "explanation" must be a short string.
- "atoms" must be an array of objects with keys "name" and "meaning".
- "warnings" must be an array. Use [] when there are no warnings.

LTL syntax rules:
- Use ASCII LTL only.
- Unary operators: G, F, X, !
- Binary operators: U, &, |, ->
- Grouping: parentheses ()
- Proposition names must be lowercase letters/digits only, like r, b, p1, req, grant
- Do not use backslashes anywhere in the formula.
- Do not escape operators or parentheses.
- Do not use LaTeX syntax.
- Do not use English words like ALWAYS or EVENTUALLY in the formula; use G and F instead.
- Do not use alternate formulas or prose outside the JSON object.

Valid formula examples:
- G(r -> F(b))
- G(req -> F(grant))
- X(p1)
- (r U g)

Invalid formula examples:
- \\G (r \\U b)
- \\(G(r)\\)
- $G(r)$
- ALWAYS(r)
- EVENTUALLY(b)
"""


SEED_REPAIR_SYSTEM_PROMPT = """You repair malformed LTL model output.
Given an original natural-language requirement and a previous malformed result, extract or repair exactly one plausible LTL formula and return only one JSON object.

Return ONLY a single JSON object with this shape:
{
  "formula": "<LTL_FORMULA>",
  "explanation": "<SHORT_EXPLANATION>",
  "atoms": [
    {"name": "<atom>", "meaning": "<what it means>"}
  ],
  "warnings": ["<optional warning 1>", "<optional warning 2>"]
}

Output rules:
- Output must be valid JSON. No backticks, comments, or extra text.
- Return exactly one repaired formula, not alternatives.
- Preserve the intended meaning of the original requirement when possible.
- If the previous result already suggests a formula, repair/extract it rather than inventing a completely different interpretation.

LTL syntax rules:
- Use ASCII LTL only.
- Unary operators: G, F, X, !
- Binary operators: U, &, |, ->
- Grouping: parentheses ()
- Proposition names must be lowercase letters/digits only, like r, b, p1, req, grant
- Do not use backslashes anywhere in the formula.
- Do not use LaTeX syntax.
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


def _parse_formula_or_raise(formula: str) -> str:
    normalized_formula = _sanitize_formula(formula)
    return str(parse_ltl_string(normalized_formula))


def _repair_seed_payload(provider, prompt: str, payload: dict, malformed_formula: str) -> dict:
    repair_payload = provider.complete_json(
        SEED_REPAIR_SYSTEM_PROMPT,
        "\n".join(
            [
                f"Original requirement:\n{prompt.strip()}",
                "",
                f"Malformed formula:\n{malformed_formula}",
                "",
                "Previous JSON object:",
                json.dumps(payload, ensure_ascii=True),
            ]
        ),
    )
    repaired_warnings = repair_payload.get("warnings", [])
    if isinstance(repaired_warnings, list):
        repair_payload["warnings"] = [
            str(item).strip() for item in repaired_warnings if str(item).strip()
        ] + ["Initial model output required formula repair."]
    else:
        repair_payload["warnings"] = ["Initial model output required formula repair."]
    return repair_payload


def generate_seed_formula(prompt: str, provider_payload: dict) -> SeedFormulaResult:
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    provider = build_provider(provider_payload)
    payload = provider.complete_json(SEED_SYSTEM_PROMPT, f"Description:\n{prompt.strip()}")
    formula = str(payload.get("formula", "")).strip()
    if not formula:
        raise ProviderError("Model did not return a formula.")

    try:
        formula = _parse_formula_or_raise(formula)
    except LTLParseError as exc:
        try:
            payload = _repair_seed_payload(provider, prompt, payload, formula)
            repaired_formula = str(payload.get("formula", "")).strip()
            if not repaired_formula:
                raise ProviderError("Model repair pass did not return a formula.")
            formula = _parse_formula_or_raise(repaired_formula)
        except (ProviderError, LTLParseError) as repair_exc:
            raise ProviderError(
                "Model returned an invalid LTL formula and the repair pass did not recover it. "
                "Try a more instruction-following model, revise the prompt, or use a model that follows structured output more reliably. "
                f"Received: {formula!r}"
            ) from repair_exc
    explanation = str(payload.get("explanation", "")).strip() or "Seed formula proposed by the language model."
    atoms = _normalize_atoms(formula, payload.get("atoms", []))
    warnings = [str(item).strip() for item in payload.get("warnings", []) if str(item).strip()]
    return SeedFormulaResult(formula=formula, explanation=explanation, atoms=atoms, warnings=warnings)
