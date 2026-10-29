"""Every Hail Mary table outcome uses real offensive/supplemental rolls only."""

import pytest

from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.models import ResultKind
from bowl_bound.penalties import prepare_hail_mary
from tests.synthetic_teams import team_chart


@pytest.mark.parametrize(
    ("roll", "kind", "yards"),
    [
        (OffensiveRoll(1, 0, 0), ResultKind.YARDS, 35),
        (OffensiveRoll(1, 3, 5), ResultKind.YARDS, 35),
        (OffensiveRoll(1, 4, 5), ResultKind.TOUCHDOWN, None),
        (OffensiveRoll(2, 0, 0), ResultKind.INTERCEPTION, 35),
        (OffensiveRoll(2, 3, 0), ResultKind.INTERCEPTION, 35),
        (OffensiveRoll(2, 4, 0), ResultKind.YARDS, 4),
        (OffensiveRoll(2, 0, 5), ResultKind.YARDS, 4),
        (OffensiveRoll(2, 4, 2), ResultKind.INTERCEPTION, 35),
        (OffensiveRoll(2, 4, 5), ResultKind.INTERCEPTION, 35),
        (OffensiveRoll(3, 0, 0), ResultKind.INCOMPLETE, None),
        (OffensiveRoll(3, 3, 5), ResultKind.INCOMPLETE, None),
        (OffensiveRoll(3, 4, 5), ResultKind.INCOMPLETE, None),
    ],
)
def test_outcomes_and_exact_roll_consumption(roll, kind, yards) -> None:
    extra = [] if roll.total == 19 or 30 <= roll.total <= 38 else [OffensiveRoll(1, 0, 0)]
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice([roll, *extra, sentinel])
    p = prepare_hail_mary(team_chart("Home"), dice)
    assert p.resolution.result.kind is kind
    assert p.resolution.result.yards == yards
    assert p.resolution.result.defense.kind is ResultKind.NO_CHANGE
    assert p.resolution.trace[0].section == "hail_mary"
    assert all(e.section != "defense" for e in p.resolution.trace)
    assert dice.offensive() == sentinel
    if roll.total == 39:
        assert p.penalties[0].yards == 15 and p.penalties[0].automatic_first_down


def test_hurried_hail_mary_keeps_printed_pi_per_user_policy() -> None:
    p = prepare_hail_mary(
        team_chart("Home"),
        ScriptedDice([OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0)]),
        hurried=True,
    )
    assert p.penalties[0].yards == 15 and not p.pre_snap
