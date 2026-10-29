"""RULE-011: distinguish a new-possession return from an original-play recovery."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import NormalizedCell, Play, ResultKind, SpecialTeamsColumn, TeamChart
from bowl_bound.session import PlaySession
from bowl_bound.turnovers import (
    resolve_end_zone_recovery_return,
    resolve_fumble,
    resolve_interception,
)
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance


def return_fumbler(location: int, advance: int | None) -> TeamChart:
    chart = replace(team_chart("Returning", defense=0), recovery_range=range(10, 40))
    fumble = NormalizedCell(ResultKind.FUMBLE, provenance(), yards=location)
    finish = (
        NormalizedCell(ResultKind.TOUCHDOWN, provenance()) if advance is None else yards(advance)
    )
    return replace(
        chart,
        special_teams=tuple(
            replace(row, cell=fumble if row.roll == 10 else finish)
            if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN
            else row
            for row in chart.special_teams
        ),
    )


@pytest.mark.parametrize("side", list(Possession))
@pytest.mark.parametrize("end_zone", [False, True])
@pytest.mark.parametrize("recovery,advance", [(10, 0), (17, 5), (17, None)])
def test_returner_recovery_starts_new_series_or_scores_defensive_touchdown(
    side: Possession,
    end_zone: bool,
    recovery: int,
    advance: int | None,
) -> None:
    chart = return_fumbler(8 if end_zone else 3, advance)
    opponent = team_chart("Original", defense=0)
    rolls = [
        OffensiveRoll(1, 0, 0),
        OffensiveRoll(1, 0, 0) if recovery == 10 else OffensiveRoll(1, 4, 3),
    ]
    if recovery == 17:
        rolls.append(OffensiveRoll(2, 0, 0))
    sentinel = OffensiveRoll(3, 0, 0)
    dice = ScriptedDice([*rolls, sentinel])
    if end_zone:
        result = resolve_end_zone_recovery_return(chart, opponent, side, dice, end_zone_depth=5)
    else:
        result = resolve_interception(
            FieldState(side.other, 60, 3, 8),
            location=20,
            interceptor=chart,
            opponent=opponent,
            choice="return",
            dice=dice,
        )
    assert len(result.trace) == len(rolls)
    assert [entry.roll for entry in result.trace] == rolls
    assert dice.offensive() == sentinel
    if advance is None:
        assert result.outcome.value == "defensive_touchdown" and result.state is None
        assert result.points == ((6, 0) if side is Possession.HOME else (0, 6))
    else:
        assert result.outcome.value == "defensive_recovery"
        assert result.state == FieldState(side, (97 if end_zone else 57) - advance, 1, 10)
        assert result.points == (0, 0)


@pytest.mark.parametrize("side", list(Possession))
@pytest.mark.parametrize("advance", [False, True])
def test_original_fourth_down_own_recovery_labels_turnover_on_downs(
    side: Possession,
    advance: bool,
) -> None:
    chart = return_fumbler(0, -1)
    rolls = (
        [OffensiveRoll(1, 4, 3), OffensiveRoll(2, 0, 0)] if advance else [OffensiveRoll(1, 0, 0)]
    )
    result = resolve_fumble(
        FieldState(side, 63, 4, 8),
        location=2,
        fumbler=chart,
        opponent=team_chart("Opponent"),
        dice=ScriptedDice(rolls),
    )
    assert result.state == FieldState(side.other, 38 if advance else 39, 1, 10)
    assert result.outcome.value == "turnover_on_downs"


@pytest.mark.parametrize("side", list(Possession))
def test_session_return_fumble_has_fresh_down_and_complete_observed_trace(side: Possession) -> None:
    original = team_chart(
        "Original",
        defense=0,
        plays={Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)},
    )
    returning = return_fumbler(3, 5)
    home, away = (original, returning) if side is Possession.HOME else (returning, original)
    session = PlaySession.for_analysis(home, away, FieldState(side, 60, 3, 8))
    source = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 4, 3),
            OffensiveRoll(2, 0, 0),
        ]
    )
    session.snap("9", "A", dice=source)
    result = session.decide("interception:return", dice=source)
    assert result.supported and not result.pending
    assert result.outcome == "defensive_recovery"
    assert result.state_after.possession == side.other.value
    assert (
        result.state_after.down,
        result.state_after.yards_to_go,
        result.state_after.yards_to_goal,
    ) == (1, 10, 52)
    assert [entry.section for entry in result.trace] == [
        "offense",
        "defense",
        "turnover_return",
        "fumble_recovery",
        "turnover_return",
    ]
    assert (
        len(session.view().log) == 1 and session.view().score.home == session.view().score.away == 0
    )


def test_changed_return_series_rules_reject_previous_replay_profile() -> None:
    import json

    from bowl_bound.save_game import SaveFormatError, dumps_game, loads_game
    from tests.test_save_game import new, seal

    data = json.loads(dumps_game(new()))
    assert data["engine_profile"] == "bowl-bound-m21-v1"
    data["engine_profile"] = "bowl-bound-m19-v1"
    with pytest.raises(SaveFormatError, match="invalid or incompatible"):
        loads_game(seal(data), lambda _: pytest.fail("old profile must fail before team lookup"))


def test_returner_own_recovery_save_resume_preserves_fresh_series_and_next_snap() -> None:
    from bowl_bound.save_game import dumps_game, loads_game
    from tests.test_save_game import new

    original = team_chart(
        "Original",
        defense=0,
        plays={Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=20)},
    )
    returning = return_fumbler(3, 5)
    game = new(
        teams=(original, returning),
        rolls=[
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 4, 3),
            OffensiveRoll(2, 0, 0),
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
        ],
    )
    game.snap("9", "A")
    game.decide("interception:return")
    state = game.view().state
    assert (state.possession, state.down, state.yards_to_go, state.yards_to_goal) == (
        "away",
        1,
        10,
        47,
    )
    restored = loads_game(
        dumps_game(game), lambda key: {"2002/home": original, "2002/away": returning}[key]
    )
    assert restored.view() == game.view()
    assert restored.snap("1", "A") == game.snap("1", "A")
    assert restored.view() == game.view()
    assert (game.view().state.down, game.view().state.yards_to_go) == (2, 6)
