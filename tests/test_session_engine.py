from pick_ltl.session.engine import classify_trace, next_pair, refine_session, reclassify_trace
from pick_ltl.session.models import (
    CandidateFormulaState,
    CandidateOrigin,
    FinalResult,
    SeedFormulaResult,
    SessionState,
    TraceClassification,
)


def test_next_pair_single_candidate_fallback(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.session.engine.build_final_result",
        lambda candidate, title, message="": FinalResult(
            title=title,
            formula=candidate.formula if candidate else None,
            explanation=candidate.explanation if candidate else "",
            english="",
            message=message,
        ),
    )

    session = SessionState(
        prompt="Eventually r",
        seed=SeedFormulaResult(formula="F(r)", explanation="seed"),
        candidate_states=[
            CandidateFormulaState(
                formula="F(r)",
                explanation="seed",
                origin=CandidateOrigin(kind="seed"),
            )
        ],
        mode="single_candidate",
        message="We could only get this one.",
    )

    result = next_pair(session)
    assert result.mode == "single_candidate"
    assert result.final_result.formula == "F(r)"


def test_classify_trace_eliminates_competitor_and_finalizes(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.session.engine.is_trace_satisfied",
        lambda trace, formula: (trace == "good") == (formula == "A"),
    )
    monkeypatch.setattr(
        "pick_ltl.session.engine.build_final_result",
        lambda candidate, title, message="": FinalResult(
            title=title,
            formula=candidate.formula if candidate else None,
            explanation=candidate.explanation if candidate else "",
            english="",
            message=message,
        ),
    )

    session = SessionState(
        candidate_states=[
            CandidateFormulaState(
                formula="A",
                explanation="seed",
                origin=CandidateOrigin(kind="seed"),
            ),
            CandidateFormulaState(
                formula="B",
                explanation="variant",
                origin=CandidateOrigin(kind="semantic_mutation"),
            ),
        ],
        history=[
            TraceClassification(trace="good", classification="accept", matching_candidates=[], source="pair", timestamp=1),
        ],
        mode="voting",
    )

    result = classify_trace(session, "good", "accept")
    assert result.mode == "final_result"
    assert result.final_result.formula == "A"
    loser = next(candidate for candidate in result.candidate_states if candidate.formula == "B")
    assert loser.eliminated is True


def test_refine_session_replays_history(monkeypatch):
    replayed = []

    monkeypatch.setattr(
        "pick_ltl.session.engine.generate_seed_formulas",
        lambda prompt, provider: [SeedFormulaResult(formula="G(r)", explanation=f"seed:{prompt}")],
    )
    monkeypatch.setattr(
        "pick_ltl.session.engine.create_initial_session",
        lambda prompt, provider, seeds: SessionState(
            prompt=prompt,
            provider=provider,
            seed=seeds[0],
            seeds=seeds,
            candidate_states=[
                CandidateFormulaState(
                    formula="G(r)",
                    explanation="seed",
                    origin=CandidateOrigin(kind="seed"),
                )
            ],
            mode="single_candidate",
        ),
    )

    def fake_classify(session, trace, classification, source="pair"):
        replayed.append((trace, classification, source))
        return session

    monkeypatch.setattr("pick_ltl.session.engine.classify_trace", fake_classify)

    session = SessionState(
        prompt="old",
        provider={"kind": "ollama"},
        history=[
            TraceClassification(trace="t1", classification="accept", matching_candidates=[], source="pair", timestamp=1),
            TraceClassification(trace="t2", classification="reject", matching_candidates=[], source="manual", timestamp=2),
        ],
    )

    refined = refine_session(session, "new prompt")
    assert refined.prompt == "new prompt"
    assert replayed == [("t1", "accept", "pair"), ("t2", "reject", "manual")]


def test_reclassify_trace_recalculates_votes_and_reopens_voting(monkeypatch):
    monkeypatch.setattr(
        "pick_ltl.session.engine.is_trace_satisfied",
        lambda trace, formula: formula == "A" and trace in {"good1", "good2"},
    )
    monkeypatch.setattr(
        "pick_ltl.session.engine.build_final_result",
        lambda candidate, title, message="": FinalResult(
            title=title,
            formula=candidate.formula if candidate else None,
            explanation=candidate.explanation if candidate else "",
            english="",
            message=message,
        ),
    )

    session = SessionState(
        candidate_states=[
            CandidateFormulaState(
                formula="A",
                explanation="seed",
                origin=CandidateOrigin(kind="seed"),
            ),
            CandidateFormulaState(
                formula="B",
                explanation="variant",
                origin=CandidateOrigin(kind="semantic_mutation"),
            ),
        ],
        history=[
            TraceClassification(trace="good1", classification="accept", matching_candidates=[], source="pair", timestamp=1),
            TraceClassification(trace="good2", classification="accept", matching_candidates=[], source="pair", timestamp=2),
        ],
        mode="final_result",
    )

    session = reclassify_trace(session, 1, "unsure")

    assert session.mode == "voting"
    assert session.final_result is None
    assert session.history[1].classification == "unsure"
    candidate_a = next(candidate for candidate in session.candidate_states if candidate.formula == "A")
    candidate_b = next(candidate for candidate in session.candidate_states if candidate.formula == "B")
    assert candidate_a.positive_votes == 1
    assert candidate_b.negative_votes == 1
    assert candidate_b.eliminated is False
