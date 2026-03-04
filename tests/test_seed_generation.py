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


def test_generate_seed_formula_normalizes_escaped_operators(monkeypatch):
    fake = FakeLLMProvider(
        {
            "formula": r"\G (r \U p)",
            "explanation": "seed explanation",
            "atoms": [{"name": "r", "meaning": "red is on"}, {"name": "p", "meaning": "pressure is on"}],
            "warnings": [],
        }
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    seed = generate_seed_formula("always r until p", {"kind": "ollama"})

    assert seed.formula == "(G (r U p))"


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


def test_generate_seed_formula_repairs_malformed_formula_with_second_query(monkeypatch):
    fake = FakeLLMProvider(
        [
            {
                "formula": r"\(P R U\)",
                "explanation": "bad seed explanation",
                "atoms": [{"name": "P", "meaning": "pressure is on"}],
                "warnings": [],
            },
            {
                "formula": "G(p -> F(q))",
                "explanation": "repaired explanation",
                "atoms": [
                    {"name": "p", "meaning": "pressure is on"},
                    {"name": "q", "meaning": "quality signal is on"},
                ],
                "warnings": ["repaired from malformed output"],
            },
        ]
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    seed = generate_seed_formula("when pressure then eventually quality", {"kind": "ollama"})

    assert seed.formula == "(G (p -> (F q)))"
    assert seed.explanation == "repaired explanation"
    assert [atom.name for atom in seed.atoms] == ["p", "q"]
    assert "Initial model output required formula repair." in seed.warnings
    assert len(fake.calls) == 2
    assert "Malformed formula:" in fake.calls[1]["user_prompt"]
