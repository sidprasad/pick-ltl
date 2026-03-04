from pick_ltl.ltl.traceprocessor import getFormulaLiterals


def test_get_formula_literals_only_returns_atoms_in_formula():
    assert getFormulaLiterals("G(r -> F(b))") == {"r", "b"}
