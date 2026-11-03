"""RULE-041: compare completed recovery outcomes before applying a penalty."""

import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.cli import TerminalGame
from bowl_bound.decision_facts import DecisionOutcomeKind
from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import NormalizedCell, PenaltyTeam, ResultKind, TeamChart
from bowl_bound.regulation import RegulationGame
from bowl_bound.save_game import (
    SavedGame,
    SaveFormatError,
    _digest,
    _source_data,
    dumps_game,
    loads_game,
)
from bowl_bound.session import PlaySession
from bowl_bound.team_catalog import TeamCatalog
from tests.synthetic_teams import metadata, team_chart, yards
from tests.test_models import provenance
from tests.test_regulation import kickoff
from tests.test_session_penalties import chart, foul
from tests.test_special_teams import penalty, special_chart, with_roll


def teams(location: int = 3) -> tuple[TeamChart, TeamChart]:
    home = chart(
        foul(PenaltyTeam.OFFENSE),
        NormalizedCell(ResultKind.FUMBLE, provenance(), yards=location),
    )
    home = replace(home, defense=team_chart("Home", defense=0).defense)
    return home, replace(home, name="Away")


@pytest.mark.parametrize("side", list(Possession))
@pytest.mark.parametrize("recovered,down", [(True, 1), (False, 1), (True, 4)])
@pytest.mark.parametrize("decision", ["decline", "accept:0:previous"])
def test_recovery_is_known_before_penalty_and_never_repeated(
    side: Possession, recovered: bool, down: int, decision: str
) -> None:
    home, away = teams()
    session = PlaySession.for_analysis(home, away, FieldState(side, 65, down, 10))
    recovery = OffensiveRoll(1 if recovered else 3, 0, 0)
    sentinel = OffensiveRoll(2, 2, 2)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),
            recovery,
            sentinel,
        ]
    )
    before = session.view()
    report = session.snap("1", "A", dice=dice)
    pending = session.view().pending
    assert report.pending and pending is not None
    assert session.view().state == before.state
    assert session.view().statistics == before.statistics
    assert not session.view().log and not session.view().scoring
    assert [
        entry.roll["total"] for entry in report.trace if entry.section == "fumble_recovery"
    ] == [recovery.total]
    decline = next(c for c in pending.choices if c.id == "decline")
    assert "unresolved" not in decline.label and "still to be resolved" not in decline.label
    projection = next(o for o in pending.decision_outcomes if o.choice_id == "decline")
    retaining = recovered and down != 4
    expected_side = side if retaining else side.other
    assert projection.kind is DecisionOutcomeKind.FIELD
    assert projection.possession == expected_side.value
    assert projection.yards_to_goal == (62 if retaining else 38)
    assert projection.down == (2 if retaining else 1)
    for _ in range(4):
        assert session.view().pending == pending
    completed = session.decide(decision)
    assert dice.offensive() == sentinel
    assert not completed.pending and len(session.view().log) == 1
    assert [
        entry.roll["total"] for entry in completed.trace if entry.section == "fumble_recovery"
    ] == [recovery.total]
    if decision == "decline":
        assert completed.state_after.possession == expected_side.value
        assert completed.state_after.yards_to_goal == projection.yards_to_goal
        assert completed.state_after.down == projection.down
    else:
        assert completed.outcome == "penalty_accepted"
        assert completed.state_after.possession == side.value
        assert completed.state_after.yards_to_goal == 70
        assert session.view().score.home == session.view().score.away == 0


@pytest.mark.parametrize("side", list(Possession))
@pytest.mark.parametrize("accept", [False, True])
@pytest.mark.parametrize(
    "spot,location,recovery,kind,opponent,points",
    [
        (5, 7, 1, DecisionOutcomeKind.TOUCHDOWN, False, 6),
        (95, -7, 1, DecisionOutcomeKind.SAFETY, True, 2),
        (95, -7, 3, DecisionOutcomeKind.TOUCHDOWN, True, 6),
    ],
)
def test_scoring_fumble_is_projected_without_awarding_discarded_points(
    side: Possession,
    accept: bool,
    spot: int,
    location: int,
    recovery: int,
    kind: DecisionOutcomeKind,
    opponent: bool,
    points: int,
) -> None:
    home, away = teams(location)
    session = PlaySession.for_analysis(home, away, FieldState(side, spot, 1, min(10, spot)))
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),
            OffensiveRoll(recovery, 0, 0),
            OffensiveRoll(2, 2, 2),
        ]
    )
    session.snap("1", "A", dice=dice)
    pending = session.view().pending
    decline = next(o for o in pending.decision_outcomes if o.choice_id == "decline")
    assert decline.kind is kind
    scorer = side.other if opponent else side
    assert decline.scoring_side == scorer.value
    assert session.view().score.home == session.view().score.away == 0
    session.decide("accept:0:previous" if accept else "decline")
    assert dice.offensive() == OffensiveRoll(2, 2, 2)
    assert (session.view().score.home, session.view().score.away) == (
        (0, 0) if accept else (points, 0) if scorer is Possession.HOME else (0, points)
    )


@pytest.mark.parametrize("decision", ["decline", "accept:0:previous"])
def test_save_replay_keeps_prepared_recovery_and_future_source(decision: str) -> None:
    home, away = teams()
    saved = SavedGame.new(
        home,
        away,
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
        coach_seed=31,
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
                OffensiveRoll(2, 2, 2),
            ]
        ),
    )
    saved.snap("1", "A")
    assert len(saved._tape.rolls) == 4
    restored = loads_game(dumps_game(saved), lambda key: home if key.endswith("home") else away)
    assert restored.view() == saved.view()
    assert restored.decide(decision) == saved.decide(decision)
    assert restored.view() == saved.view()
    assert len(saved._tape.rolls) == len(restored._tape.rolls) == 4
    assert saved._tape.offensive() == restored._tape.offensive() == OffensiveRoll(2, 2, 2)


@pytest.mark.parametrize("decision", ["decline", "accept:0:previous"])
def test_end_zone_recovery_choice_and_save_precede_original_penalty(decision: str) -> None:
    home, away = teams(7)
    saved = SavedGame.new(
        home,
        away,
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
        coach_seed=31,
        start_yards_to_goal=5,
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
                OffensiveRoll(2, 2, 2),
            ]
        ),
    )
    saved.snap("1", "A")
    assert [c.id for c in saved.view().pending.choices] == ["end_zone:return", "end_zone:touchback"]

    def resolve(key: str) -> TeamChart:
        return home if key.endswith("home") else away

    restored = loads_game(dumps_game(saved), resolve)
    assert restored.decide("end_zone:touchback") == saved.decide("end_zone:touchback")
    pending = saved.view().pending
    assert pending.chooser == "Away"
    decline = next(o for o in pending.decision_outcomes if o.choice_id == "decline")
    assert (decline.kind, decline.possession, decline.yards_to_goal) == (
        DecisionOutcomeKind.FIELD,
        "away",
        80,
    )
    assert saved.view().state.possession == "home" and not saved.view().log
    restored = loads_game(dumps_game(restored), resolve)
    assert restored.decide(decision) == saved.decide(decision)
    assert restored.view() == saved.view()
    assert saved.view().state.possession == ("away" if decision == "decline" else "home")
    assert saved._tape.offensive() == restored._tape.offensive() == OffensiveRoll(2, 2, 2)


@pytest.mark.parametrize("side", list(Possession))
def test_defensive_fumble_return_touchdown_is_known_before_penalty(side: Possession) -> None:
    home, away = (
        replace(
            t, special_teams=special_chart(t.name, interception_return=yards(100)).special_teams
        )
        for t in teams()
    )
    session = PlaySession.for_analysis(home, away, FieldState(side, 65, 1, 10))
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),
            OffensiveRoll(3, 3, 4),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(2, 2, 2),
        ]
    )
    report = session.snap("1", "A", dice=dice)
    assert report.pending
    pending = session.view().pending
    decline = next(o for o in pending.decision_outcomes if o.choice_id == "decline")
    assert decline.kind is DecisionOutcomeKind.TOUCHDOWN
    assert decline.scoring_side == side.other.value
    assert session.view().score.home == session.view().score.away == 0
    session.decide("decline")
    assert (session.view().score.home, session.view().score.away) == (
        (0, 6) if side is Possession.HOME else (6, 0)
    )
    assert dice.offensive() == OffensiveRoll(2, 2, 2)


@pytest.mark.parametrize("side", list(Possession))
@pytest.mark.parametrize("decision", ["decline", "accept:0:previous"])
def test_flagged_fumble_timing_and_statistics_commit_once(side: Possession, decision: str) -> None:
    home, away = (
        replace(
            t, season=2002, special_teams=special_chart(t.name, kickoff=yards(70)).special_teams
        )
        for t in teams()
    )
    regulation = RegulationGame.new(
        home,
        away,
        seed=1,
        dice=ScriptedDice([OffensiveRoll(3, 4, 5), OffensiveRoll(1, 0, 0)]),
    )
    kickoff(regulation, "toss:receive" if side is Possession.HOME else "toss:kick")
    before = regulation.view()
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),
            OffensiveRoll(3, 0, 0),
            OffensiveRoll(2, 2, 2),
        ]
    )
    regulation.snap("1", "A", dice=dice)
    assert regulation.view().clock == before.clock
    assert regulation.view().statistics == before.statistics
    report = regulation.decide(decision)
    after = regulation.view()
    assert report.timing.penalty
    assert after.clock.remaining == before.clock.remaining - 10
    assert len(after.timing_log) == len(before.timing_log) + 1
    stats = after.statistics.home if side is Possession.HOME else after.statistics.away
    assert stats.rushing_attempts == (1 if decision == "decline" else 0)
    assert stats.rushing_yards == (3 if decision == "decline" else 0)
    assert len(after.log) == len(before.log) + 1
    assert dice.offensive() == OffensiveRoll(2, 2, 2)


def legacy_save(
    monkeypatch: pytest.MonkeyPatch, decision: str | None
) -> tuple[str, tuple[TeamChart, TeamChart]]:
    """Create the old public-safe journal ordering, without an obsolete engine copy."""
    home, away = teams()
    saved = SavedGame.new(
        home,
        away,
        home_id="2026/home",
        away_id="2026/away",
        seed=7,
        coach_seed=31,
        dice=ScriptedDice(
            [
                OffensiveRoll(1, 0, 0),
                DefensiveRoll(1, 0),
                OffensiveRoll(2, 0, 0),
                OffensiveRoll(3, 0, 0),
                OffensiveRoll(2, 2, 2),
            ]
        ),
    )
    current = PlaySession._apply_live_result

    def old_order(
        session: Any,
        prepared: Any,
        called: Any,
        defensive: Any,
        field: Any,
        before: Any,
        trace: Any,
        prefix: str,
        source: Any,
        **kwargs: Any,
    ) -> Any:
        if kwargs.get("deferred_penalty") is not None:
            return session._offer_penalty_decision(
                prepared,
                called,
                defensive,
                field,
                before,
                trace,
                prefix,
                source,
            )
        return current(
            session, prepared, called, defensive, field, before, trace, prefix, source, **kwargs
        )

    with monkeypatch.context() as legacy:
        legacy.setattr(PlaySession, "_apply_live_result", old_order)
        saved.snap("1", "A")
        if decision is not None:
            saved.decide(decision)
            saved._tape.future = ScriptedDice(
                [
                    OffensiveRoll(1, 0, 0),
                    DefensiveRoll(1, 0),
                    OffensiveRoll(2, 0, 0),
                    OffensiveRoll(3, 0, 0),
                    OffensiveRoll(2, 2, 2),
                ]
            )
        data = json.loads(dumps_game(saved))
    data["engine_profile"] = "bowl-bound-m22-v1"
    data["integrity"] = _digest({k: v for k, v in data.items() if k != "integrity"})
    return json.dumps(data), (home, away)


@pytest.mark.parametrize("decision", [None, "decline", "accept:0:previous"])
def test_legacy_fumble_journals_keep_recorded_rolls_and_upgrade_without_drawing(
    monkeypatch: pytest.MonkeyPatch, decision: str | None
) -> None:
    document, (home, away) = legacy_save(monkeypatch, decision)
    data = json.loads(document)

    def resolve(key: str) -> TeamChart:
        return home if key.endswith("home") else away

    restored = loads_game(document, resolve)
    assert len(restored._tape.rolls) == len(data["rolls"])
    assert _source_data(restored._tape.future) == data["random_state"]
    current_document = json.loads(dumps_game(restored))
    assert current_document["engine_profile"] == "bowl-bound-m33-v1"
    assert current_document["config"]["legacy_fumble_commands"] == len(data["commands"])
    again = loads_game(dumps_game(restored), resolve)
    assert again.view() == restored.view()
    if decision is None:
        assert [c.id for c in restored.view().pending.choices] == ["fumble:resolve"]
        assert again.decide("fumble:resolve") == restored.decide("fumble:resolve")
        decline = next(
            o for o in restored.view().pending.decision_outcomes if o.choice_id == "decline"
        )
        assert decline.kind is DecisionOutcomeKind.FIELD and decline.possession == "away"
        again = loads_game(dumps_game(again), resolve)
        assert again.decide("decline") == restored.decide("decline")
        assert len(again._tape.rolls) == len(restored._tape.rolls) == 4
        assert again._tape.offensive() == restored._tape.offensive() == OffensiveRoll(2, 2, 2)
    else:
        previous_rolls = len(restored._tape.rolls)
        restored.snap("1", "A")
        assert len(restored._tape.rolls) == previous_rolls + 4
        assert (
            next(
                o for o in restored.view().pending.decision_outcomes if o.choice_id == "decline"
            ).kind
            is DecisionOutcomeKind.FIELD
        )
        assert loads_game(dumps_game(restored), resolve).view() == restored.view()


@pytest.mark.parametrize("prefix", [True, -1, 1, "1"])
def test_replay_order_prefix_is_strictly_validated(prefix: object) -> None:
    home, away = teams()
    saved = SavedGame.new(
        home, away, home_id="2026/home", away_id="2026/away", seed=7, coach_seed=31
    )
    data = json.loads(dumps_game(saved))
    data["config"]["legacy_fumble_commands"] = prefix
    data["integrity"] = _digest({k: v for k, v in data.items() if k != "integrity"})
    with pytest.raises(SaveFormatError):
        loads_game(json.dumps(data), lambda key: home if key.endswith("home") else away)


def test_new_profile_cannot_use_old_pending_digest_after_more_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document, (home, away) = legacy_save(monkeypatch, None)
    old = json.loads(document)

    def resolve(key: str) -> TeamChart:
        return home if key.endswith("home") else away

    saved = loads_game(document, resolve)
    saved.decide("fumble:resolve")
    saved.decide("decline")
    forged = json.loads(dumps_game(saved))
    forged["state_digest"] = old["state_digest"]
    forged["integrity"] = _digest({k: v for k, v in forged.items() if k != "integrity"})
    with pytest.raises(SaveFormatError):
        loads_game(json.dumps(forged), resolve)


def test_return_penalty_consequence_finishes_before_original_penalty() -> None:
    home, away = (
        replace(
            t,
            special_teams=with_roll(
                special_chart(t.name, interception_return=yards(8)),
                "interception_return",
                10,
                penalty(PenaltyTeam.OFFENSE),
            ).special_teams,
        )
        for t in teams()
    )
    session = PlaySession.new(home, away, seed=7)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),
            OffensiveRoll(3, 3, 4),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 1),
            OffensiveRoll(2, 2, 2),
        ]
    )
    session.snap("1", "A", dice=dice)
    assert "return:decline" in [c.id for c in session.view().pending.choices]
    session.decide("return:decline")
    pending = session.view().pending
    decline = next(o for o in pending.decision_outcomes if o.choice_id == "decline")
    assert (decline.kind, decline.possession, decline.yards_to_goal) == (
        DecisionOutcomeKind.FIELD,
        "away",
        30,
    )
    assert session.view().state.possession == "home" and not session.view().log
    completed = session.decide("decline")
    assert completed.state_after.possession == "away" and completed.state_after.yards_to_goal == 30
    assert len([e for e in completed.trace if e.section == "fumble_recovery"]) == 1
    assert dice.offensive() == OffensiveRoll(2, 2, 2)


def test_api_transports_legacy_recovery_step_and_known_penalty_facts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    document, (home, away) = legacy_save(monkeypatch, None)
    monkeypatch.setattr(
        TeamCatalog,
        "load_with_metadata",
        lambda self, key: (home if key.endswith("home") else away, metadata()),
    )
    client = TestClient(create_app(tmp_path))
    loaded = client.post("/api/games/load", json=json.loads(document))
    assert loaded.status_code == 200
    body = loaded.json()
    assert [c["id"] for c in body["view"]["pending"]["choices"]] == ["fumble:resolve"]
    assert body["view"]["log"] == []
    response = client.post(
        f"/api/games/{body['game_id']}/decision", json={"choice": "fumble:resolve"}
    )
    assert response.status_code == 200
    pending = response.json()["view"]["pending"]
    decline = next(o for o in pending["decision_outcomes"] if o["choice_id"] == "decline")
    assert (decline["kind"], decline["possession"], decline["yards_to_goal"]) == (
        "field",
        "away",
        38,
    )
    assert "still to be resolved" not in next(
        c["label"] for c in pending["choices"] if c["id"] == "decline"
    )


def test_cli_applies_same_legacy_recovery_control(monkeypatch: pytest.MonkeyPatch) -> None:
    document, (home, away) = legacy_save(monkeypatch, None)

    def resolve(key: str) -> TeamChart:
        return home if key.endswith("home") else away

    saved = loads_game(document, resolve)
    terminal = TerminalGame(saved, resolve, human_side="away", output=io.StringIO())
    terminal.display()
    assert "Resolve fumble recovery" in terminal.output.getvalue()
    assert terminal.command("choose fumble:resolve")
    pending = saved.view().pending
    assert (
        next(o for o in pending.decision_outcomes if o.choice_id == "decline").possession == "away"
    )
    assert len(saved._tape.rolls) == 4 and not saved.view().log


@pytest.mark.parametrize("decision", ["decline", "accept:0:previous"])
def test_prepared_own_return_penalty_retains_stat_credit_until_original_choice(
    decision: str,
) -> None:
    home, away = (
        replace(
            t,
            special_teams=with_roll(
                special_chart(t.name, interception_return=yards(40)),
                "interception_return",
                10,
                penalty(PenaltyTeam.OFFENSE, 5),
            ).special_teams,
        )
        for t in teams()
    )
    session = PlaySession.new(home, away, seed=7)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(2, 0, 0),
            OffensiveRoll(1, 3, 4),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 0, 1),
            OffensiveRoll(2, 2, 2),
        ]
    )
    session.snap("1", "A", dice=dice)
    session.decide("return:accept")
    assert session.view().pending is not None and not session.view().log
    assert session.view().statistics.home.rushing_attempts == 0
    completed = session.decide(decision)
    assert completed.state_after.possession == "home"
    if decision == "decline":
        # Origin 62: the 40-yard return passes its midpoint (31); five yards
        # are enforced there. Credit original gain 3 + legal return 31, not the foul.
        assert completed.state_after.yards_to_goal == 36
        assert session.view().statistics.home.rushing_attempts == 1
        assert session.view().statistics.home.rushing_yards == 34
    else:
        assert completed.state_after.yards_to_goal == 70
        assert session.view().statistics.home.rushing_attempts == 0
    assert dice.offensive() == OffensiveRoll(2, 2, 2)
