from pick_ltl.app import create_app
from pick_ltl.llm.base import ProviderError
from pick_ltl.session.models import SeedFormulaResult, SessionState


def test_seed_route_with_mocked_generator(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.api.routes.generate_seed_formula",
        lambda prompt, provider: SeedFormulaResult(
            formula="G(r)",
            explanation="seed",
            warnings=[],
            atoms=[],
        ),
    )

    app = create_app()
    client = app.test_client()
    response = client.post("/api/seed/generate", json={"prompt": "always r", "provider": {"kind": "ollama"}})
    assert response.status_code == 200
    assert response.get_json()["formula"] == "G(r)"


def test_build_candidates_route_can_return_single_candidate(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.api.routes.create_initial_session",
        lambda prompt, provider, seed: SessionState(
            prompt=prompt,
            provider=provider,
            seed=seed,
            mode="single_candidate",
            message="We could only get this one.",
        ),
    )

    app = create_app()
    client = app.test_client()
    response = client.post(
        "/api/candidates/build",
        json={
            "prompt": "always r",
            "provider": {"kind": "ollama"},
            "seed": {"formula": "G(r)", "explanation": "seed", "atoms": [], "warnings": []},
        },
    )
    assert response.status_code == 200
    assert response.get_json()["mode"] == "single_candidate"


def test_seed_route_returns_400_for_invalid_model_formula(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.api.routes.generate_seed_formula",
        lambda prompt, provider: (_ for _ in ()).throw(ProviderError("Model returned an invalid LTL formula.")),
    )

    app = create_app()
    client = app.test_client()
    response = client.post("/api/seed/generate", json={"prompt": "always r", "provider": {"kind": "ollama"}})

    assert response.status_code == 400
    assert "invalid LTL formula" in response.get_json()["error"]
