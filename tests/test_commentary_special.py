"""Synthetic special-team and turnover narration without guessed participants."""

import json
from dataclasses import asdict, replace

import pytest

from bowl_bound.commentary import narrate_report
from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import Possession, start_drive
from bowl_bound.roster import Roster, parse_roster
from bowl_bound.session import PlaySession, TraceEntry
from bowl_bound.statistics import PlayStatistics, StatKind
from tests.test_commentary import report
from tests.test_special_teams import special_chart, yards


def names(prefix: str) -> Roster:
    return parse_roster(
        json.dumps(
            {
                "k": [prefix + " Boot"],
                "p": [prefix + " Punt"],
                "kr": [prefix + " Return"],
                "qb": [prefix + " Quill"],
                "rb": [prefix + " Runner"],
            }
        )
    )


@pytest.mark.parametrize("side", ["home", "away"])
@pytest.mark.parametrize(
    "action,outcome,role",
    [
        ("punt", "punt_fair_catch", "H Punt"),
        ("field_goal", "field_goal_good", "H Boot"),
        ("kickoff", "touchback", "H Boot"),
        ("pat", "pat_good", "H Boot"),
    ],
)
def test_kicking_side_is_not_the_final_possessor(
    side: str, action: str, outcome: str, role: str
) -> None:
    original = report()
    value = replace(
        original,
        statistics=PlayStatistics(),
        outcome=outcome,
        state_before=replace(original.state_before, possession=side),
        state_after=replace(original.state_after, possession="away" if side == "home" else "home"),
        trace=(TraceEntry(action, "ignored display name", "", None, {}, ""),),
    )
    home, away = (names("H"), names("A")) if side == "home" else (names("A"), names("H"))
    text = narrate_report(value, home, away)
    assert role in text and "returner:" not in text
    assert "Illustrative players" not in text
    assert text.endswith(value.commentary)


@pytest.mark.parametrize("action", ["punt", "kickoff"])
@pytest.mark.parametrize("side", ["home", "away"])
def test_actual_return_stage_labels_opposite_team(action: str, side: str) -> None:
    original = report()
    value = replace(
        original,
        statistics=PlayStatistics(),
        outcome=action + "_return",
        state_before=replace(original.state_before, possession=side),
        state_after=replace(original.state_after, possession="away" if side == "home" else "home"),
        trace=tuple(
            TraceEntry(s, "ignored", "", None, {}, "") for s in (action, action + "_return")
        ),
    )
    home, away = (names("H"), names("A")) if side == "home" else (names("A"), names("H"))
    text = narrate_report(value, home, away)
    assert "H Boot" in text or "H Punt" in text
    assert "A Return" in text and "H Return" not in text
    touchdown = replace(value, outcome="return_touchdown", state_after=None)
    assert "A Return" in narrate_report(touchdown, home, away)


@pytest.mark.parametrize("outcome", ["kick_replay", "kick_penalty_accepted", "conversion_ready"])
def test_consulted_kick_chart_is_not_proof_of_a_committed_kick(outcome: str) -> None:
    value = replace(
        report(),
        statistics=PlayStatistics(),
        outcome=outcome,
        trace=(TraceEntry("punt", "Home", "", None, {}, ""),),
    )
    assert narrate_report(value, names("H"), names("A")) == value.commentary


@pytest.mark.parametrize("recovery", ["fumble_recovery", "blocked_kick_recovery"])
def test_chained_or_ambiguous_recovery_never_invents_a_player(recovery: str) -> None:
    value = replace(
        report(StatKind.INTERCEPTION),
        trace=tuple(
            TraceEntry(s, "Home", "", None, {}, "")
            for s in ("turnover_return", recovery, "turnover_return")
        ),
    )
    assert narrate_report(value, names("H"), names("A")) == value.commentary


@pytest.mark.parametrize("side", ["home", "away"])
def test_completed_interception_return_uses_original_defending_team(side: str) -> None:
    value = replace(
        report(StatKind.INTERCEPTION, side),
        outcome="defensive_recovery",
        trace=(TraceEntry("turnover_return", "ignored", "", None, {}, ""),),
    )
    home, away = (names("H"), names("A")) if side == "home" else (names("A"), names("H"))
    text = narrate_report(value, home, away)
    assert "H Quill" in text and "A Return" in text and "returns the interception" in text
    assert "defender:" not in narrate_report(value, home, away)


def test_real_engine_kicks_and_pending_results_preserve_facts() -> None:
    home = replace(
        special_chart("Home", punt=yards(40), field_goal=yards(65), kickoff=yards(80)), season=2007
    )
    away = replace(special_chart("Away"), season=2007)
    game = PlaySession(home, away, 7, 65)
    pending = game.kick("punt", dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
    assert narrate_report(pending, names("H"), names("A")) == pending.commentary
    fair = game.decide("kick:fair_catch")
    before = asdict(fair)
    assert "H Punt" in narrate_report(fair, names("H"), names("A"))
    assert "returner:" not in narrate_report(fair, names("H"), names("A"))
    assert asdict(fair) == before
    for action in ("field_goal", "kickoff"):
        game = PlaySession(home, away, 7, 65)
        game._field = start_drive(Possession.AWAY, 65)
        # Use the same synthetic special chart on the actual kicking side.
        game._charts[Possession.AWAY] = home
        value = game.kick(action, dice=ScriptedDice([OffensiveRoll(1, 0, 0)]))
        assert not value.pending
        assert value.outcome == ("touchback" if action == "kickoff" else "field_goal_good")
        assert "A Boot" in narrate_report(value, names("H"), names("A"))
        assert "returner:" not in narrate_report(value, names("H"), names("A"))


@pytest.mark.parametrize("section", ["turnover_return", "end_zone_recovery_return"])
@pytest.mark.parametrize("outcome", ["defensive_recovery", "defensive_touchdown"])
def test_supported_interception_return_stages(section: str, outcome: str) -> None:
    value = replace(
        report(StatKind.INTERCEPTION),
        outcome=outcome,
        trace=(TraceEntry(section, "Away", "", None, {}, ""),),
    )
    if outcome == "defensive_touchdown":
        value = replace(value, state_after=None)
    assert "A Return" in narrate_report(value, names("H"), names("A"))
    assert (
        narrate_report(replace(value, pending=True), names("H"))
        == replace(value, pending=True).commentary
    )
    touchback = replace(value, outcome="touchback", trace=())
    assert "returner:" not in narrate_report(touchback, names("H"), names("A"))


@pytest.mark.parametrize("bad_snap", [False, True])
def test_real_aborted_punt_safety_without_recovery_roll_is_generic(bad_snap: bool) -> None:
    from bowl_bound.models import NormalizedCell, PenaltyCode, PenaltyTeam, ResultKind
    from tests.test_hurry import foul
    from tests.test_models import provenance

    cell = (
        foul(PenaltyTeam.OFFENSE, PenaltyCode.S, None)
        if bad_snap
        else NormalizedCell(ResultKind.BLOCKED_KICK, provenance(), yards=-20)
    )
    home = replace(special_chart("Home", punt=cell), season=2007)
    away = replace(special_chart("Away"), season=2007)
    game = PlaySession(home, away, 7, 99)
    value = game.kick(
        "punt",
        hurried=bad_snap,
        dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)]),
    )
    assert value.outcome == "safety" and not value.pending
    assert not {"fumble_recovery", "blocked_kick_recovery"} & {e.section for e in value.trace}
    assert narrate_report(value, names("H"), names("A")) == value.commentary


@pytest.mark.parametrize("action", ["punt", "kickoff"])
def test_real_no_foul_return_reroll_retains_complete_penalty_narrative(action: str) -> None:
    from bowl_bound.models import PenaltyCode, PenaltyTeam, SpecialTeamsColumn
    from tests.test_hurry import foul

    home = replace(special_chart("Home", **{action: yards(30)}), season=2007)
    away = replace(
        special_chart(
            "Away", **{action + "_return": foul(PenaltyTeam.DEFENSE, PenaltyCode.R, None)}
        ),
        season=2007,
    )
    away = replace(
        away,
        special_teams=tuple(
            replace(r, cell=yards(12))
            if r.column is SpecialTeamsColumn(action + "_return") and r.roll == 20
            else r
            for r in away.special_teams
        ),
    )
    game = PlaySession(home, away, 7, 65)
    value = game.kick(
        action,
        hurried=True,
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(2, 0, 0),
            ]
        ),
    )
    if value.pending:
        value = game.decide("kick:return")
    assert not value.pending and value.outcome == action + "_return"
    assert [e.section for e in value.trace].count(action + "_return") == 2
    original = asdict(value)
    # Even a no-foul reroll retains its complete enforcement narrative.
    assert value.timing.penalty
    assert narrate_report(value, names("H"), names("A")) == value.commentary
    assert asdict(value) == original


@pytest.mark.parametrize("action", ["punt", "kickoff"])
def test_real_return_touchdown_preserves_scoring_and_rng(action: str) -> None:
    from random import getstate

    from bowl_bound.models import NormalizedCell, ResultKind
    from tests.test_models import provenance

    home = replace(special_chart("Home", **{action: yards(30)}), season=2007)
    away = replace(
        special_chart(
            "Away", **{action + "_return": NormalizedCell(ResultKind.TOUCHDOWN, provenance())}
        ),
        season=2007,
    )
    game = PlaySession(home, away, 7, 65)
    value = game.kick(action, dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)]))
    if value.pending:
        value = game.decide("kick:return")
    assert value.outcome == "return_touchdown" and game.view().score.away == 6
    before, rng = asdict(game.view()), getstate()
    text = narrate_report(value, names("H"), names("A"))
    assert "A Return" in text and "TOUCHDOWN" in text
    assert asdict(game.view()) == before and getstate() == rng


@pytest.mark.parametrize("total", [10, 34])
def test_real_fumble_recoveries_never_guess_the_fumbler_or_recoverer(total: int) -> None:
    from bowl_bound.dice import DefensiveRoll
    from bowl_bound.models import NormalizedCell, Play, ResultKind
    from tests.synthetic_teams import team_chart
    from tests.test_models import provenance

    home = replace(
        team_chart(
            "Home", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=5)}
        ),
        recovery_range=range(10, 20),
    )
    away = special_chart("Away", interception_return=yards(0))
    last = OffensiveRoll(1, 0, 0) if total == 10 else OffensiveRoll(3, 2, 2)
    game = PlaySession(home, away, 7, 65)
    value = game.snap(
        "1",
        "A",
        dice=ScriptedDice(
            [OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), last, OffensiveRoll(1, 0, 0)]
        ),
    )
    assert not value.pending and "fumble_recovery" in [e.section for e in value.trace]
    assert value.outcome == ("offensive_recovery" if total == 10 else "defensive_recovery")
    assert value.state_after.possession == ("home" if total == 10 else "away")
    assert narrate_report(value, names("H"), names("A")) == value.commentary
