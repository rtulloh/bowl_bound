"""Synthetic pending Hail Mary identity, rule context and pre-fix replay.

The four cli069 fixtures were saved by the unmodified a30f112 engine using
pending_game in a clean archive, not constructed by editing digests or commands.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.coaching_profiles import CURRENT_DIFFICULTY_VERSION
from bowl_bound.dice import OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    ResultKind,
    SpecialTeamsColumn,
    TeamChart,
)
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.session import PlayReport, PlaySession
from bowl_bound.timing import Clock
from tests.synthetic_teams import _with_legend_color, team_chart, write_team, yards
from tests.test_cli import saved_facts
from tests.test_models import provenance
from tests.test_save_game import legacy_fixture_for_current_runtime
from tests.test_special_teams import special_chart


def hail_mary_teams() -> tuple[TeamChart, TeamChart]:
    """Invented charts whose kickoff starts a legal late-half play at opponent 18."""
    charts = []
    penalty = _with_legend_color(
        NormalizedCell(
            kind=ResultKind.PENALTY,
            provenance=provenance(),
            penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, yards=10),
        )
    )
    for name in ("Home", "Away"):
        base = team_chart(name, season=2002, offense=0, defense=0)
        special = special_chart(name, kickoff=yards(45), kickoff_return=yards(62))
        charts.append(
            replace(
                base,
                special_teams=tuple(
                    replace(row, cell=penalty if row.roll == 10 else yards(15))
                    if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN
                    else row
                    for row in special.special_teams
                ),
            )
        )
    return charts[0], charts[1]


def pending_game(*, penalty: bool = False, snap: bool = True) -> SavedGame:
    game = SavedGame.new(
        *hail_mary_teams(),
        home_id="2002/home",
        away_id="2002/away",
        seed=7,
        coach_seed=31,
        coach_policy="hard-v13",
        mode="regulation",
        clock=Clock(2, 20),
        dice=ScriptedDice(
            [
                OffensiveRoll(3, 4, 5),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 1, 0),
                OffensiveRoll(3, 4, 5) if penalty else OffensiveRoll(2, 0, 1),
                OffensiveRoll(3, 0, 0),
                OffensiveRoll(1, 0, 0),
                OffensiveRoll(1, 1, 0),
                OffensiveRoll(3, 0, 0),
            ]
        ),
    )
    game.decide("toss:receive")
    game.kick("kickoff")
    assert game.view().state.yards_to_goal == 18
    if snap:
        game.action("hail_mary")
    return game


def assert_identity(report: PlayReport) -> None:
    assert report.called_play == report.resolved_play == "Hail Mary"
    assert report.defense == "Blank defense"
    assert report.trace[0].section == "hail_mary"
    # The actual table trace retains its internal Boot-leg routing, without a defense roll.
    assert report.trace[0].play == "Boot-leg"
    assert all(entry.section != "defense" for entry in report.trace)


@pytest.mark.parametrize("possession", list(Possession))
@pytest.mark.parametrize("formation", ["A", "F"])
@pytest.mark.parametrize("end_zone", [False, True])
def test_pending_hail_mary_keeps_identity_through_interception_choices(
    possession: Possession, formation: str, end_zone: bool
) -> None:
    session = PlaySession.for_analysis(
        *hail_mary_teams(), FieldState(possession, 18 if end_zone else 70, 3, 8)
    )
    dice = ScriptedDice([OffensiveRoll(2, 0, 1), OffensiveRoll(3, 0, 0), OffensiveRoll(3, 0, 0)])
    before = session.view()
    pending = session.snap("8", formation, dice=dice, hail_mary=True)
    assert_identity(pending)
    assert pending.outcome == "interception_pending" and pending.pending
    assert session.view().state == before.state and session.view().log == ()
    if end_zone:
        recovery = session.decide("interception:return")
        assert_identity(recovery)
        assert recovery.outcome == "end_zone_recovery_pending"
        assert recovery.trace == pending.trace
        assert session._pending.turnover_resolution.end_zone_recovery.depth == 9
        assert session.view().state == before.state and session.view().log == ()
        completed = session.decide("end_zone:touchback")
        assert completed.state_after.yards_to_goal == 80
    else:
        completed = session.decide("interception:decline")
    assert_identity(completed)
    assert session.view().log == (completed,)
    assert dice.offensive() == OffensiveRoll(3, 0, 0)


@pytest.mark.parametrize("possession", list(Possession))
def test_hail_mary_return_penalty_and_completion_keep_original_identity(
    possession: Possession,
) -> None:
    session = PlaySession.for_analysis(*hail_mary_teams(), FieldState(possession, 70, 3, 8))
    dice = ScriptedDice(
        [
            OffensiveRoll(2, 0, 1),
            OffensiveRoll(3, 0, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 1, 0),
            OffensiveRoll(3, 0, 0),
        ]
    )
    session.snap("8", "A", dice=dice, hail_mary=True)
    pending = session.decide("interception:return")
    assert pending.outcome == "return_penalty_pending" and session.view().log == ()
    assert_identity(pending)
    completed = session.decide("return:decline")
    assert_identity(completed)
    assert completed.state_after.possession == possession.other.value
    assert dice.offensive() == OffensiveRoll(3, 0, 0)


@pytest.mark.parametrize("choice", ["decline", "accept:0:previous"])
def test_hail_mary_pass_interference_pending_and_completed_labels(choice: str) -> None:
    session = PlaySession.for_analysis(*hail_mary_teams(), FieldState(Possession.HOME, 70, 3, 8))
    dice = ScriptedDice([OffensiveRoll(3, 4, 5), OffensiveRoll(3, 0, 0), OffensiveRoll(3, 0, 0)])
    pending = session.snap("8", "A", dice=dice, hail_mary=True)
    assert pending.outcome == "penalty_pending" and session.view().log == ()
    assert_identity(pending)
    assert_identity(session.decide(choice))
    assert dice.offensive() == OffensiveRoll(3, 0, 0)


@pytest.mark.parametrize("stage", ["interception", "end-zone", "return-penalty", "penalty"])
def test_authentic_pre_fix_hail_mary_save_replays_and_continues(stage: str) -> None:
    raw = legacy_fixture_for_current_runtime(
        Path(__file__).parent / "fixtures" / f"cli069-{stage}.json"
    )
    charts = dict(zip(("2002/home", "2002/away"), hail_mary_teams(), strict=True))
    restored = loads_game(raw, charts.__getitem__)
    frozen = json.loads(raw)
    facts = saved_facts(restored)
    # Load upgrades ordinary Hard policy, retaining all past commands and exact dice/state.
    for key in ("commands", "rolls", "random_state", "state_digest", "teams"):
        assert facts[key] == frozen[key]
    assert restored.coach_policy == f"hard-v{CURRENT_DIFFICULTY_VERSION}"
    reference = pending_game(penalty=stage == "penalty")
    if stage in {"end-zone", "return-penalty"}:
        reference.decide("interception:return")
    if stage == "return-penalty":
        reference.decide("end_zone:return")
    continuation = {
        "interception": ["interception:return", "end_zone:touchback"],
        "end-zone": ["end_zone:touchback"],
        "return-penalty": ["return:decline"],
        "penalty": ["decline"],
    }[stage]
    for choice in continuation:
        before = restored.view()
        rolls = saved_facts(restored)["rolls"]
        report = restored.decide(choice)
        assert_identity(report)
        reference.decide(choice)
        assert restored.view() == reference.view()
        if report.pending:
            assert restored.view().clock == before.clock
            assert restored.view().state == before.state
            assert restored.view().log == before.log
            assert saved_facts(restored)["rolls"] == rolls
    assert loads_game(dumps_game(restored), charts.__getitem__).view() == restored.view()
    assert [charge.seconds for charge in restored.view().timing_log] == [10, 10]


def test_api_displays_engine_hail_mary_identity_and_rule_depth(tmp_path: Path) -> None:
    for chart in hail_mary_teams():
        write_team(tmp_path, chart)
    game = pending_game(snap=False)
    with TestClient(create_app(tmp_path)) as client:
        loaded = client.post("/api/games/load", content=dumps_game(game))
        assert loaded.status_code == 200, loaded.text
        path = "/api/games/" + loaded.json()["game_id"]
        response = client.post(path + "/action", json={"action": "hail_mary"})
        assert response.status_code == 200, response.text
        pending = response.json()
        report = pending["report"]
        assert report["called_play"] == report["resolved_play"] == "Hail Mary"
        assert report["defense"] == "Blank defense"
        assert pending["view"]["pending"]["decision_context"] == (
            "Interception in Away end zone (9 yards deep). Return result pending."
        )
        before = pending["view"]
        response = client.post(path + "/decision", json={"choice": "interception:return"})
        assert response.status_code == 200, response.text
        recovered = response.json()
        assert recovered["report"]["defense"] == "Blank defense"
        assert recovered["report"]["called_play"] == "Hail Mary"
        for key in ("clock", "state", "statistics", "log", "timing_log"):
            assert recovered["view"][key] == before[key]
