"""Cross-project rare allocation controls retain the unrounded target mass."""

import pytest

from tools.chartgen import generate


@pytest.mark.parametrize("seed", [1, 7, 8306])
@pytest.mark.parametrize("target", [0.92, 1.0, 1.08], ids=["below-tie", "tie", "above-tie"])
def test_sparse_allocation_uses_float_distance_before_tie_breaking(
    seed: int, target: float
) -> None:
    weights = {10: 2, 11: 214}
    selected = generate.nearest_mass_rows(weights, target / 216, seed=seed)
    # A pre-rounded target of one would incorrectly choose zero for 1.08.
    assert sum(weights[row] for row in selected) == (2 if target > 1 else 0)


@pytest.mark.parametrize("seed", [1, 7, 8306])
def test_final_column_keeps_closer_rare_mass_after_a_light_row_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, seed: int
) -> None:
    # The physical distribution has one mass-one row. After that row has been
    # consumed, the nearest available nonzero mass is two, not one.
    weights = {row: mass for row, mass in generate.offensive_weights().items() if mass != 1}
    assert sum(weights.values()) == 215
    monkeypatch.setattr(generate, "offensive_weights", lambda: dict(weights))
    tokens = generate._column([4], [("INT", 1.08 / 215)], seed=seed, locations={"INT": [17]})
    assert sum(weights[row] for row, token in tokens.items() if token == "INT 17") == 2
    assert set(tokens.values()) == {"4", "INT 17"}
    assert tokens == generate._column(
        [4], [("INT", 1.08 / 215)], seed=seed, locations={"INT": [17]}
    )
