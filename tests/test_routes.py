from pick_ltl.app import create_app
from pick_ltl.llm.base import ProviderError
from pick_ltl.session.models import SeedFormulaResult, SessionState


def test_seed_route_with_mocked_generator(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.api.routes.generate_seed_formulas",
        lambda prompt, provider: [
            SeedFormulaResult(formula="G(r)", explanation="seed", warnings=[], atoms=[]),
            SeedFormulaResult(formula="F(r)", explanation="alt", warnings=[], atoms=[]),
        ],
    )

    app = create_app()
    client = app.test_client()
    response = client.post("/api/seed/generate", json={"prompt": "always r", "provider": {"kind": "ollama"}})
    assert response.status_code == 200
    assert response.get_json()["formula"] == "G(r)"
    assert len(response.get_json()["seeds"]) == 2


def test_build_candidates_route_can_return_single_candidate(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.api.routes.create_initial_session",
        lambda prompt, provider, seeds: SessionState(
            prompt=prompt,
            provider=provider,
            seed=seeds[0] if seeds else None,
            seeds=seeds,
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
            "seeds": [
                {"formula": "G(r)", "explanation": "seed", "atoms": [], "warnings": []},
                {"formula": "F(r)", "explanation": "alt", "atoms": [], "warnings": []},
            ],
        },
    )
    assert response.status_code == 200
    assert response.get_json()["mode"] == "single_candidate"


def test_seed_route_returns_400_for_invalid_model_formula(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.api.routes.generate_seed_formulas",
        lambda prompt, provider: (_ for _ in ()).throw(ProviderError("Model returned an invalid LTL formula.")),
    )

    app = create_app()
    client = app.test_client()
    response = client.post("/api/seed/generate", json={"prompt": "always r", "provider": {"kind": "ollama"}})

    assert response.status_code == 400
    assert "invalid LTL formula" in response.get_json()["error"]


def test_reclassify_route_returns_updated_session(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.api.routes.reclassify_trace",
        lambda session, history_index, classification: SessionState(
            prompt=session.prompt,
            provider=session.provider,
            mode="voting",
            message=f"{history_index}:{classification}",
        ),
    )

    app = create_app()
    client = app.test_client()
    response = client.post(
        "/api/session/reclassify",
        json={
            "session": {"prompt": "always r", "provider": {"kind": "ollama"}, "history": []},
            "history_index": 0,
            "classification": "accept",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "0:accept"
