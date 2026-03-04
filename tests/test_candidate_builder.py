from pick_ltl.services.candidate_builder import build_candidates
from pick_ltl.session.models import AtomSpec, SeedFormulaResult


def test_assign_dynamic_thresholds_lowers_threshold_for_barely_distinguishable_pair(monkeypatch):
    seeds = [
        SeedFormulaResult(formula="F(r)", explanation="seed 1", atoms=[AtomSpec(name="r", meaning="r")]),
        SeedFormulaResult(formula="G(r)", explanation="seed 2", atoms=[AtomSpec(name="r", meaning="r")]),
    ]

    monkeypatch.setattr("pick_ltl.services.candidate_builder.getAllApplicableMisconceptions", lambda node: [])
    monkeypatch.setattr("pick_ltl.services.candidate_builder._count_distinguishing_witnesses", lambda *args, **kwargs: 1)

    candidates = build_candidates(seeds)

    assert len(candidates) == 2
    assert all(candidate.elimination_threshold == 1 for candidate in candidates)
