"""CLI-046: natural calls use structured facts and never drive football decisions."""

from dataclasses import asdict, replace
from random import getstate

import pytest

from bowl_bound.commentary import narrate_report
from bowl_bound.session import PlayReport, PlaySession, TraceEntry
from bowl_bound.statistics import PlayStatistics, StatKind
from tests.synthetic_teams import team_chart
from tests.test_commentary import report, roster


def play(kind: StatKind, yards: int = 4, outcome: str = "advance") -> PlayReport:
    original = report(kind)
    return replace(
        original,
        outcome=outcome,
        yards=yards,
        statistics=replace(original.statistics, yards=yards, touchdown=outcome == "touchdown"),
    )


@pytest.mark.parametrize("named", [False, True])
@pytest.mark.parametrize(
    "kind,yards,words",
    [
        (StatKind.RUSH, 0, "no gain"),
        (StatKind.RUSH, -3, "loss of 3 yards"),
        (StatKind.RUSH, 1, "1 yard"),
        (StatKind.RUSH, 4, "4 yards"),
        (StatKind.RUSH, 25, "25 yards"),
        (StatKind.COMPLETE, 4, "4 yards"),
        (StatKind.COMPLETE, 0, "no gain"),
        (StatKind.COMPLETE, -2, "loss of 2 yards"),
        (StatKind.INCOMPLETE, 0, "incomplete"),
        (StatKind.SACK, -7, "loss of 7 yards"),
    ],
)
def test_calls_integrate_names_or_generic_roles(
    kind: StatKind, yards: int, words: str, named: bool
) -> None:
    value = play(kind, yards)
    text = narrate_report(value, roster("H") if named else None)
    assert words in text.lower()
    assert "Illustrative players" not in text
    assert "runner:" not in text and "passer:" not in text and "receiver:" not in text
    assert value.description not in text
    if named:
        assert ("H Bolt" if kind is StatKind.RUSH else "H Quill") in text
        if kind is StatKind.COMPLETE:
            assert "H Finch" in text
    else:
        assert "the running back" in text.lower() or "the quarterback" in text.lower()
    assert "1 yards" not in text


@pytest.mark.parametrize("kind", [StatKind.RUSH, StatKind.COMPLETE])
def test_touchdown_uses_credited_not_raw_chart_yards(kind: StatKind) -> None:
    value = replace(play(kind, 65, "touchdown"), yards=99, state_after=None)
    text = narrate_report(value, roster("H"))
    assert "TOUCHDOWN" in text and "65 yards" in text and "99" not in text
    assert "H Bolt" in text if kind is StatKind.RUSH else "H Finch" in text


@pytest.mark.parametrize(
    "outcome,expected", [("first_down", "First down!"), ("turnover_on_downs", "Turnover on downs!")]
)
def test_only_committed_outcome_adds_first_down_or_turnover(outcome: str, expected: str) -> None:
    assert expected in narrate_report(play(StatKind.RUSH, 4, outcome), roster("H"))
    ordinary = narrate_report(play(StatKind.RUSH, 40), roster("H"))
    assert "First down" not in ordinary and "Turnover" not in ordinary


def test_variants_are_stable_read_only_and_do_not_consume_randomness() -> None:
    value, names = play(StatKind.RUSH, 0), roster("H")
    before, rng, before_names = asdict(value), getstate(), asdict(names)
    calls = [narrate_report(replace(value, number=n), names) for n in range(1, 10)]
    assert len(set(calls)) >= 3
    assert all("no gain" in text.lower() and "H Bolt" in text for text in calls)
    assert len({narrate_report(value, names) for _ in range(10)}) == 1
    assert asdict(value) == before and asdict(names) == before_names and getstate() == rng


@pytest.mark.parametrize(
    "outcome", ["defensive_recovery", "defensive_touchdown", "touchback", "safety"]
)
def test_interceptions_keep_final_result_without_inventing_defender(outcome: str) -> None:
    value = play(StatKind.INTERCEPTION, 0, outcome)
    text = narrate_report(value, roster("H"))
    assert "INTERCEPTED" in text and "H Quill" in text
    if outcome == "defensive_touchdown":
        assert "TOUCHDOWN" in text
    if outcome == "touchback":
        assert "Touchback" in text
    if outcome == "safety":
        assert "SAFETY" in text
    assert "defender:" not in text and "jumps the route" not in text
    assert value.state_after.possession_name in text and value.state_after.spot in text


@pytest.mark.parametrize(
    "change",
    [
        {"pending": True},
        {"supported": False},
        {"outcome": "future_rule"},
        {"trace": (TraceEntry("fumble_recovery", "Home", "", None, {}, ""),)},
        {"trace": (TraceEntry("blocked_kick_recovery", "Home", "", None, {}, ""),)},
        {"statistics": PlayStatistics()},
    ],
)
def test_unestablished_results_retain_complete_factual_fallback(change: dict[str, object]) -> None:
    value = replace(play(StatKind.RUSH), **change)
    assert narrate_report(value, roster("H")) == value.commentary


def test_penalty_narrative_is_not_discarded_for_an_offensive_credit() -> None:
    value = play(StatKind.RUSH)
    value = replace(value, timing=replace(value.timing, penalty=True))
    assert narrate_report(value, roster("H")) == value.commentary


def test_real_no_gain_is_an_announcer_call_with_or_without_rosters() -> None:
    game = PlaySession(team_chart("Home", offense=0), team_chart("Away", defense=0), 7, 65)
    value = game.snap("1", "A")
    for names in (None, roster("H")):
        text = narrate_report(value, names)
        assert "no gain" in text.lower()
        assert " vs " not in text and "Illustrative" not in text


@pytest.mark.parametrize(
    "action,outcome,phrase",
    [
        ("punt", "punt_fair_catch", "fair catch"),
        ("punt", "punt_dead", "downed"),
        ("punt", "punt_return", "returns"),
        ("kickoff", "kickoff_return", "returns"),
        ("kickoff", "touchback", "touchback"),
        ("kickoff", "return_touchdown", "touchdown"),
        ("field_goal", "field_goal_good", "good"),
        ("field_goal", "field_goal_missed", "no good"),
        ("pat", "pat_good", "good"),
        ("pat", "pat_missed", "no good"),
    ],
)
def test_special_calls_name_only_established_roles_and_preserve_final_spot(
    action: str, outcome: str, phrase: str
) -> None:
    from tests.test_commentary_special import names

    original = report()
    sections = [action]
    if outcome in {"punt_return", "kickoff_return", "return_touchdown"}:
        sections.append(action + "_return")
    value = replace(
        original,
        statistics=PlayStatistics(),
        outcome=outcome,
        description=(
            f"Engine kick facts. {original.state_after.possession_name} "
            f"ball at {original.state_after.spot}."
        ),
        trace=tuple(TraceEntry(s, "ignored", "", None, {}, "") for s in sections),
    )
    text = narrate_report(value, names("H"), names("A"))
    assert phrase in text.lower() and "Illustrative" not in text
    assert ("H Punt" if action == "punt" else "H Boot") in text
    assert ("A Return" in text) == (len(sections) == 2)
    assert value.state_after.possession_name in text and value.state_after.spot in text
    assert text.endswith(value.commentary)
    assert ". the " not in text


@pytest.mark.parametrize(
    "kind,yards,outcome",
    [
        (StatKind.RUSH, 0, "advance"),
        (StatKind.RUSH, -1, "advance"),
        (StatKind.RUSH, 1, "advance"),
        (StatKind.RUSH, 20, "first_down"),
        (StatKind.RUSH, 65, "touchdown"),
        (StatKind.COMPLETE, 0, "advance"),
        (StatKind.COMPLETE, -1, "advance"),
        (StatKind.COMPLETE, 1, "advance"),
        (StatKind.COMPLETE, 25, "first_down"),
        (StatKind.COMPLETE, 65, "touchdown"),
        (StatKind.INCOMPLETE, 0, "advance"),
        (StatKind.SACK, -1, "advance"),
        (StatKind.INTERCEPTION, 0, "defensive_recovery"),
    ],
)
def test_every_phrase_variant_keeps_roles_and_established_facts(
    kind: StatKind, yards: int, outcome: str
) -> None:
    original = play(kind, yards, outcome)
    calls = []
    for number in range(1, 7):
        value = replace(original, number=number)
        text = narrate_report(value, roster("H"))
        calls.append(text)
        assert (
            "H Bolt" in text
            if kind is StatKind.RUSH
            else any(name in text for name in ("H Quill", "H Reed"))
        )
        assert "Illustrative" not in text and "Recorded engine facts" not in text
        assert ("TOUCHDOWN" in text) == (outcome == "touchdown")
        assert ("First down!" in text) == (outcome == "first_down")
        assert "1 yards" not in text
        assert not any(
            word in text
            for word in ("wide open", "broken tackle", "unblocked", "dropped", "batted")
        )
    assert len(set(calls)) >= 3


@pytest.mark.parametrize("call", ["1", "6"])
def test_real_scoring_report_uses_goal_line_clipped_credit(call: str) -> None:
    game = PlaySession(team_chart("Home", offense=100), team_chart("Away", defense=0), 7, 65)
    value = game.snap(call, "A")
    assert value.statistics.touchdown and value.statistics.yards == 65
    text = narrate_report(value, roster("H"))
    assert "TOUCHDOWN" in text and "65 yards" in text and "100" not in text
    assert game.view().score.home == 6


@pytest.mark.parametrize("action", ["kneel", "spike"])
def test_real_clock_plays_keep_their_intent_instead_of_defensive_color(action: str) -> None:
    game = PlaySession(team_chart("Home"), team_chart("Away"), 7, 65)
    value = game.automatic(action)
    assert narrate_report(value, roster("H")) == value.commentary
    assert action.title() in value.commentary


def test_kick_narration_retains_all_engine_distance_and_result_details() -> None:
    from bowl_bound.dice import OffensiveRoll, ScriptedDice
    from tests.test_commentary_special import names
    from tests.test_special_teams import special_chart, yards

    home = replace(special_chart("Home", kickoff=yards(40)), season=2007)
    away = replace(special_chart("Away", kickoff_return=yards(10)), season=2007)
    game = PlaySession(home, away, 7, 65)
    value = game.kick(
        "kickoff", dice=ScriptedDice([OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0)])
    )
    assert not value.pending
    text = narrate_report(value, names("H"), names("A"))
    assert "40 yards" in text and "returns 10 yards" in text
    assert text.endswith(value.commentary)
    assert "H Boot" in text and "A Return" in text
