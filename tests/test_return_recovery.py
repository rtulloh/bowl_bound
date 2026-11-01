"""Shared synthetic recovery calculations for scrimmage and special-team returns."""

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.return_recovery import ReturnOrigin, ReturnStart, resolve_recovery


def test_recovery_uses_field_origin_and_only_the_recovery_roll() -> None:
    roll = OffensiveRoll(1, 2, 3)
    result = resolve_recovery(ReturnOrigin(65), 5, range(20, 30), ScriptedDice([roll]))

    assert result.spot == 60
    assert result.depth_roll is None
    assert result.recovery_roll == roll
    assert result.retained is False


def test_end_line_safety_does_not_consume_a_recovery_roll() -> None:
    result = resolve_recovery(ReturnOrigin(109), -1, range(10, 20), ScriptedDice([]))

    assert result.safety
    assert result.spot == 110
    assert result.recovery_roll is None


def test_end_zone_depth_roll_precedes_recovery_roll() -> None:
    depth = OffensiveRoll(3, 1, 2)
    recovery = OffensiveRoll(1, 1, 0)
    result = resolve_recovery(
        ReturnOrigin(100),
        110,
        range(20, 30),
        ScriptedDice([depth, recovery]),
    )

    assert result.spot == -3
    assert result.depth_roll == depth
    assert result.recovery_roll == recovery
    assert result.retained is False


@pytest.mark.parametrize("origin", [0, -1, True])
def test_return_origin_requires_a_positive_field_coordinate(origin: object) -> None:
    with pytest.raises(ValueError, match="return origin"):
        ReturnOrigin(origin)  # type: ignore[arg-type]


def test_return_start_pairs_field_state_with_actual_live_origin() -> None:
    field = FieldState(Possession.AWAY, 99, 1, 10)
    start = ReturnStart(field, ReturnOrigin(104))

    assert start.state == field
    assert start.origin.yards_to_goal == 104


@pytest.mark.parametrize(
    ("spot", "origin"),
    [(98, 104), (99, 98)],
)
def test_return_start_rejects_mismatched_field_and_live_coordinates(spot: int, origin: int) -> None:
    state = FieldState(Possession.AWAY, spot, 1, min(10, spot))

    with pytest.raises(ValueError, match="representable spot"):
        ReturnStart(state, ReturnOrigin(origin))
