import pytest

from pick_ltl.llm.base import ProviderError
from pick_ltl.ltl.ltlnode import LTLParseError, parse_ltl_string
from pick_ltl.services.seed_generation import generate_seed_formula
from tests.fakes import FakeLLMProvider


def test_generate_seed_formula_uses_provider_and_normalizes_atoms(monkeypatch):
    fake = FakeLLMProvider(
        {
            "formula": "G(r -> F(b))",
            "explanation": "seed explanation",
            "atoms": [{"name": "r", "meaning": "red is on"}],
            "warnings": ["ambiguous timing"],
        }
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    seed = generate_seed_formula("when red then eventually blue", {"kind": "ollama"})

    assert seed.formula == "(G (r -> (F b)))"
    assert seed.explanation == "seed explanation"
    assert [atom.name for atom in seed.atoms] == ["r", "b"]
    assert [atom.meaning for atom in seed.atoms] == ["red is on", "b"]
    assert fake.calls and "when red then eventually blue" in fake.calls[0]["user_prompt"]


def test_generate_seed_formula_normalizes_common_local_model_syntax(monkeypatch):
    fake = FakeLLMProvider(
        {
            "formula": r"\(G(P -> F(Q))\)",
            "explanation": "seed explanation",
            "atoms": [{"name": "P", "meaning": "red is on"}, {"name": "Q", "meaning": "blue is on"}],
            "warnings": [],
        }
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    seed = generate_seed_formula("when red then eventually blue", {"kind": "ollama"})

    assert seed.formula == "(G (p -> (F q)))"
    assert [atom.name for atom in seed.atoms] == ["p", "q"]


def test_parse_ltl_string_raises_clean_error_for_invalid_formula():
    with pytest.raises(LTLParseError):
        parse_ltl_string(r"\(P R U\)")


def test_generate_seed_formula_returns_provider_error_for_invalid_formula(monkeypatch):
    fake = FakeLLMProvider(
        {
            "formula": r"\(P R U\)",
            "explanation": "seed explanation",
            "atoms": [],
            "warnings": [],
        }
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    with pytest.raises(ProviderError):
        generate_seed_formula("broken formula", {"kind": "ollama"})
