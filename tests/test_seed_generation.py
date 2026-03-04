import pytest

from pick_ltl.llm.base import ProviderError
from pick_ltl.ltl.ltlnode import LTLParseError, parse_ltl_string
from pick_ltl.services.seed_generation import generate_seed_formula, generate_seed_formulas
from tests.fakes import FakeLLMProvider


def test_generate_seed_formulas_use_provider_and_normalize_atoms(monkeypatch):
    fake = FakeLLMProvider(
        {
            "atoms": [{"name": "r", "meaning": "red is on"}],
            "warnings": ["ambiguous timing"],
            "seeds": [
                {"formula": "G(r -> F(b))", "explanation": "seed explanation"},
                {"formula": "F(r)", "explanation": "backup explanation"},
            ],
        }
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    seeds = generate_seed_formulas("when red then eventually blue", {"kind": "ollama"})

    assert [seed.formula for seed in seeds] == ["(G (r -> (F b)))", "(F r)"]
    assert seeds[0].explanation == "seed explanation"
    assert [atom.name for atom in seeds[0].atoms] == ["r", "b"]
    assert [atom.meaning for atom in seeds[0].atoms] == ["red is on", "b"]
    assert fake.calls and "when red then eventually blue" in fake.calls[0]["user_prompt"]


def test_generate_seed_formula_normalizes_common_local_model_syntax(monkeypatch):
    fake = FakeLLMProvider(
        {
            "atoms": [{"name": "P", "meaning": "red is on"}, {"name": "Q", "meaning": "blue is on"}],
            "warnings": [],
            "seeds": [
                {"formula": r"\(G(P -> F(Q))\)", "explanation": "seed explanation"},
                {"formula": "F(P)", "explanation": "alt explanation"},
            ],
        }
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    seeds = generate_seed_formulas("when red then eventually blue", {"kind": "ollama"})

    assert seeds[0].formula == "(G (p -> (F q)))"
    assert [atom.name for atom in seeds[0].atoms] == ["p", "q"]


def test_generate_seed_formula_normalizes_escaped_operators(monkeypatch):
    fake = FakeLLMProvider(
        {
            "atoms": [{"name": "r", "meaning": "red is on"}, {"name": "p", "meaning": "pressure is on"}],
            "warnings": [],
            "seeds": [
                {"formula": r"\G (r \U p)", "explanation": "seed explanation"},
                {"formula": "F(r)", "explanation": "alt explanation"},
            ],
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
            "atoms": [],
            "warnings": [],
            "seeds": [
                {"formula": r"\(P R U\)", "explanation": "seed explanation"},
                {"formula": r"\(Q R U\)", "explanation": "alt explanation"},
            ],
        }
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    with pytest.raises(ProviderError):
        generate_seed_formula("broken formula", {"kind": "ollama"})


def test_generate_seed_formula_repairs_malformed_formula_with_second_query(monkeypatch):
    fake = FakeLLMProvider(
        [
            {
                "atoms": [{"name": "P", "meaning": "pressure is on"}],
                "warnings": [],
                "seeds": [
                    {"formula": r"\(P R U\)", "explanation": "bad seed explanation"},
                    {"formula": r"\(Q R U\)", "explanation": "also bad"},
                ],
            },
            {
                "atoms": [
                    {"name": "p", "meaning": "pressure is on"},
                    {"name": "q", "meaning": "quality signal is on"},
                ],
                "warnings": ["repaired from malformed output"],
                "seeds": [
                    {"formula": "G(p -> F(q))", "explanation": "repaired explanation"},
                    {"formula": "F(p)", "explanation": "alternate repaired explanation"},
                ],
            },
        ]
    )
    monkeypatch.setattr("pick_ltl.services.seed_generation.build_provider", lambda payload: fake)

    seeds = generate_seed_formulas("when pressure then eventually quality", {"kind": "ollama"})

    assert seeds[0].formula == "(G (p -> (F q)))"
    assert seeds[0].explanation == "repaired explanation"
    assert [atom.name for atom in seeds[0].atoms] == ["p", "q"]
    assert "Initial model output required formula repair." in seeds[0].warnings
    assert len(fake.calls) == 2
    assert "Malformed formulas:" in fake.calls[1]["user_prompt"]
