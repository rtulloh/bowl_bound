"""Scoring ledger and dedicated PAT outcomes: synthetic evidence only."""

from dataclasses import FrozenInstanceError, replace
from itertools import product

import pytest

from bowl_bound.dice import (
    BLACK_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.game_state import Possession
from bowl_bound.scoring import ScoreKind, ScoreLedger, resolve_pat
from tests.synthetic_teams import team_chart


def test_ledger_is_immutable_and_reconciles_every_scoring_kind() -> None:
    ledger = ScoreLedger()
    awards = [
        (Possession.HOME, ScoreKind.TOUCHDOWN),
        (Possession.HOME, ScoreKind.PAT),
        (Possession.AWAY, ScoreKind.FIELD_GOAL),
        (Possession.AWAY, ScoreKind.SAFETY),
        (Possession.HOME, ScoreKind.TWO_POINT),
        (Possession.AWAY, ScoreKind.CONVERSION_RETURN),
    ]
    for number, (scorer, kind) in enumerate(awards, 1):
        previous = ledger
        ledger = ledger.award(scorer, kind, play_number=number)
        assert len(previous.events) == number - 1
    assert ledger.totals == (9, 7)
    assert [event.points for event in ledger.events] == [6, 1, 3, 2, 2, 2]
    assert [event.number for event in ledger.events] == list(range(1, 7))
    with pytest.raises(FrozenInstanceError):
        ledger.events = ()


@pytest.mark.parametrize("play_number", [0, -1, True, 1.5])
def test_ledger_rejects_invalid_play_numbers(play_number: object) -> None:
    with pytest.raises(ValueError):
        ScoreLedger().award(Possession.HOME, ScoreKind.PAT, play_number=play_number)


def test_ledger_refuses_duplicate_or_out_of_order_awards() -> None:
    ledger = ScoreLedger().award(Possession.HOME, ScoreKind.TOUCHDOWN, play_number=3)
    for number in (2, 3):
        with pytest.raises(ValueError, match="order"):
            ledger.award(Possession.AWAY, ScoreKind.SAFETY, play_number=number)


def test_pat_enumerates_all_216_physical_rolls_against_dedicated_outcomes() -> None:
    chart = team_chart("Synthetic PAT")
    chart = replace(
        chart,
        pat_outcomes=tuple(
            replace(row, good=row.roll not in {16, 26}) for row in chart.pat_outcomes
        ),
    )
    count = 0
    for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        roll = OffensiveRoll(*faces)
        result = resolve_pat(chart, ScriptedDice([roll]))
        assert result.good is (roll.total not in {16, 26})
        assert result.points == (0 if roll.total in {16, 26} else 1)
        assert result.roll == roll and result.outcome.roll == roll.total
        count += 1
    assert count == 216


def test_pat_does_not_consult_or_reroll_a_conflicting_field_goal_column() -> None:
    from tests.test_special_teams import special_chart, yards

    chart = special_chart("Synthetic", field_goal=yards(99))
    chart = replace(
        chart, pat_outcomes=tuple(replace(row, good=False) for row in chart.pat_outcomes)
    )
    result = resolve_pat(chart, ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert not result.good and result.points == 0
