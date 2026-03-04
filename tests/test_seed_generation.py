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

