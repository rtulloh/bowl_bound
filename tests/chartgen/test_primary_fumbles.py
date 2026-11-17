"""Synthetic primary-F source and real-engine observation boundaries."""

from dataclasses import replace
from typing import Any

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    ChartColor,
    NormalizedCell,
    Play,
    ResultKind,
    SpecialTeamsColumn,
    SupplementalColumn,
    TeamChart,
)
from bowl_bound.session import PlayReport, PlaySession
from tests.synthetic_teams import metadata, team_chart
from tests.test_models import provenance
from tools.chartgen.evidence import Event
from tools.chartgen.refine import source_targets
from tools.chartgen.research_runner import _json_value


def source_sample(*, return_fumble: bool = False) -> list[Event]:
    return [
        Event(2007, "g", "rush", "a", "b", "A", "B", "rush", 4, fumble=False),
        Event(2007, "g", "pass", "a", "b", "A", "B", "complete", 8, fumble=False),
        Event(
            2007,
            "g",
            "pick",
            "a",
            "b",
            "A",
            "B",
            "interception",
            12,
            fumble=return_fumble,
            fumble_team="b" if return_fumble else None,
        ),
    ]


def test_return_fumble_does_not_raise_primary_offensive_fumble_target() -> None:
    assert source_targets(source_sample(return_fumble=True), ["a"])["fumble"] == 0


def test_primary_fumble_remains_counted_separately_from_return_fumble() -> None:
    sample = source_sample(return_fumble=True)
    sample[0] = replace(sample[0], fumble=True, fumble_team="a")
    assert source_targets(sample, ["a"])["fumble"] == pytest.approx(1 / 3)


def test_defensive_target_uses_actual_originating_owner_without_relabeling_source() -> None:
    sample = source_sample(return_fumble=True)
    sample[0] = replace(sample[0], fumble=True, fumble_team="a")
    originals = [event.to_dict() for event in sample]
    allowed = source_targets(sample, ["b"], role="defense")
    assert allowed["fumble"] == pytest.approx(1 / 3)
    assert [event.to_dict() for event in sample] == originals


def test_unsupported_primary_fumble_owner_is_unknown_not_a_zero_observation() -> None:
    sample = [replace(event, fumble=None) for event in source_sample()]
    sample[0] = replace(sample[0], fumble=True, fumble_team="b")
    assert "fumble" not in source_targets(sample, ["a"])


def result_for(
    report: PlayReport, home: TeamChart, away: TeamChart, *, hurried: bool = False
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = {
        "status": "passed",
        "teams": {"home": "A", "away": "B"},
        "configuration": {"advanced_ii": False},
        "engine_log": [_json_value(report)],
        "coaching_calls": [
            {
                "choice": "1",
                "role": "offense",
                "observation": {"play_number": report.number - 1, "hurried": hurried},
            }
        ],
    }
    return result, {"A": (home, metadata()), "B": (away, metadata())}


def observe(result: dict[str, Any], teams: dict[str, Any]) -> list[dict[str, Any]]:
    from tools.chartgen.primary_fumbles import observe_primary_results

    return observe_primary_results(result, teams)


def test_primary_dead_loose_ball_is_observed_without_a_recovery_roll() -> None:
    home = team_chart(
        "A", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=-50)}
    )
    away = team_chart("B", defense=0)
    report = PlaySession.new(home, away, seed=1).snap(
        "1", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    )
    assert report.outcome == "safety"
    assert not any(entry.section == "fumble_recovery" for entry in report.trace)
    result, teams = result_for(report, home, away)
    observed = observe(result, teams)
    assert len(observed) == 1 and observed[0]["primary_fumble"] is True
    assert observed[0]["offense_id"] == "A"
    assert observed[0]["first_recovery_retained"] is None


def test_interception_return_fumble_is_not_a_primary_offensive_fumble() -> None:
    home = team_chart(
        "A", plays={Play.NINE: NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=10)}
    )
    away = team_chart("B", defense=0)
    away = replace(
        away,
        special_teams=tuple(
            replace(row, cell=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=0))
            if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN
            else row
            for row in away.special_teams
        ),
    )
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(1, 2, 2),
        ]
    )
    session = PlaySession.new(home, away, seed=1)
    session.snap("9", "A", dice=dice)
    report = session.decide("interception:return", dice=dice)
    assert any(entry.section == "fumble_recovery" for entry in report.trace)
    result, teams = result_for(report, home, away)
    assert observe(result, teams)[0]["primary_fumble"] is False


def test_consulted_f_cell_does_not_override_engine_interception_priority() -> None:
    home = team_chart(
        "A", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3)}
    )
    away = team_chart("B", defense=0)
    away = replace(
        away,
        defense=tuple(
            replace(row, cell=NormalizedCell(ResultKind.INTERCEPTION, provenance(), yards=10))
            if row.play is Play.ONE
            else row
            for row in away.defense
        ),
    )
    session = PlaySession.new(home, away, seed=1)
    session.snap("1", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)]))
    report = session.decide("interception:decline")
    result, teams = result_for(report, home, away)
    assert observe(result, teams)[0]["primary_fumble"] is False


@pytest.mark.parametrize("color,expected", [(ChartColor.GREEN, False), (ChartColor.RED, True)])
def test_qb_sneak_uses_engine_color_rule_instead_of_chart_token(
    color: ChartColor, expected: bool
) -> None:
    token = NormalizedCell(
        ResultKind.FUMBLE if not expected else ResultKind.YARDS, provenance(), yards=8
    )
    home = team_chart("A", plays={Play.ONE: token})
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=replace(row.cell, chart_color=color)) if row.play is Play.ONE else row
            for row in home.offense
        ),
    )
    away = team_chart("B", defense=0)
    rolls = [OffensiveRoll(1, 0, 0)] + ([OffensiveRoll(1, 2, 2)] if expected else [])
    report = PlaySession.new(home, away, seed=1).snap("Q", "A", dice=ScriptedDice(rolls))
    result, teams = result_for(report, home, away)
    assert observe(result, teams)[0]["primary_fumble"] is expected


def test_option_reroll_preserves_resolved_primary_fumble() -> None:
    home = team_chart(
        "A",
        plays={
            Play.FIVE: NormalizedCell(ResultKind.SPRINT_OUT_PASS, provenance()),
            Play.SEVEN: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3),
        },
    )
    away = team_chart("B", defense=0)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 1, 0),
            OffensiveRoll(1, 2, 2),
        ]
    )
    report = PlaySession.new(home, away, seed=1).snap("5", "A", dice=dice)
    assert any(entry.section == "option" for entry in report.trace)
    result, teams = result_for(report, home, away)
    assert observe(result, teams)[0]["primary_fumble"] is True


def test_supplemental_trapped_fumble_stays_primary() -> None:
    home = team_chart(
        "A", plays={Play.NINE: NormalizedCell(ResultKind.QUARTERBACK_TRAPPED, provenance())}
    )
    home = replace(
        home,
        supplemental=tuple(
            replace(row, cell=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=-5))
            if row.column is SupplementalColumn.QUARTERBACK_TRAPPED
            else row
            for row in home.supplemental
        ),
    )
    away = team_chart("B", defense=0)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 1, 0),
            OffensiveRoll(1, 2, 2),
        ]
    )
    report = PlaySession.new(home, away, seed=1).snap("9", "A", dice=dice)
    result, teams = result_for(report, home, away)
    assert observe(result, teams)[0]["primary_fumble"] is True


def test_razzle_dazzle_comparison_echo_is_not_an_extra_physical_roll() -> None:
    home = team_chart(
        "A", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3)}
    )
    away = team_chart("B", defense=0)
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 2, 3),
            OffensiveRoll(1, 3, 5),
            DefensiveRoll(1, 0),
            OffensiveRoll(1, 2, 2),
        ]
    )
    session = PlaySession.new(home, away, seed=1)
    session.snap("RZDZ", "A", dice=dice)
    report = session.decide("razzle:1:15", dice=dice)
    result, teams = result_for(report, home, away)
    assert observe(result, teams)[0]["primary_fumble"] is True


@pytest.mark.parametrize("damage", ["context", "faces", "prefix", "advanced"])
def test_missing_or_tampered_observation_evidence_fails_instead_of_zero_filling(
    damage: str,
) -> None:
    home, away = team_chart("A"), team_chart("B", defense=0)
    report = PlaySession.new(home, away, seed=1).snap(
        "1", "A", dice=ScriptedDice([OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)])
    )
    result, teams = result_for(report, home, away)
    if damage == "context":
        result["coaching_calls"] = []
    elif damage == "faces":
        result["engine_log"][0]["trace"][0]["roll"]["faces"][0] = 99
    elif damage == "prefix":
        result["engine_log"][0]["trace"][0]["cell"] = "untrusted display"
    else:
        result["configuration"]["advanced_ii"] = True
    with pytest.raises(ValueError):
        observe(result, teams)


def test_first_physical_recovery_comes_from_engine_roll_not_final_possession() -> None:
    home = team_chart(
        "A", plays={Play.ONE: NormalizedCell(ResultKind.FUMBLE, provenance(), yards=3)}
    )
    home = replace(home, recovery_range=range(10, 20))
    away = team_chart("B", defense=0)
    away = replace(
        away,
        recovery_range=range(10, 20),
        special_teams=tuple(
            replace(row, cell=NormalizedCell(ResultKind.FUMBLE, provenance(), yards=0))
            if row.column is SpecialTeamsColumn.INTERCEPTION_RETURN
            else row
            for row in away.special_teams
        ),
    )
    dice = ScriptedDice(
        [
            OffensiveRoll(1, 0, 0),
            DefensiveRoll(1, 0),
            OffensiveRoll(3, 4, 3),
            OffensiveRoll(1, 0, 0),
            OffensiveRoll(3, 0, 0),
        ]
    )
    report = PlaySession.new(home, away, seed=1).snap("1", "A", dice=dice)
    assert report.state_after is not None and report.state_after.possession == "home"
    assert sum(entry.section == "fumble_recovery" for entry in report.trace) == 2
    result, teams = result_for(report, home, away)
    observed = observe(result, teams)[0]
    assert observed["primary_fumble"] is True
    assert observed["first_recovery_retained"] is False


def metric_game(*, primary: bool | None, recovery_trace: bool) -> dict[str, Any]:
    """Original fictional facts for aggregation, independently of display strings."""
    stat = {
        "passing_attempts": 1,
        "completions": 1,
        "interceptions": 0,
        "sacks_taken": 0,
        "rushing_attempts": 1,
        "rushing_yards": 4,
        "passing_yards": 8,
    }
    result = {
        "status": "passed",
        "error": None,
        "teams": {"home": "A", "away": "B"},
        "final": {
            "home_score": 0,
            "away_score": 0,
            "statistics": {"home": stat, "away": {key: 0 for key in stat}},
        },
        "engine_log": [
            {
                "number": 1,
                "state_before": {"possession": "home"},
                "statistics": {"kind": "rush"},
                "outcome": "advance",
                "trace": [{"section": "fumble_recovery"}] if recovery_trace else [],
            },
            {
                "number": 2,
                "state_before": {"possession": "home"},
                "statistics": {"kind": "pass"},
                "outcome": "advance",
                "trace": [],
            },
        ],
        "coaching_calls": [],
    }
    if primary is not None:
        result["normalized_primary_results"] = [
            {
                "report_number": 1,
                "offense_side": "home",
                "offense_id": "A",
                "primary_fumble": primary,
                "first_recovery_retained": None,
                "bad_snap": False,
                "kind": "fumble" if primary else "interception",
            },
            {
                "report_number": 2,
                "offense_side": "home",
                "offense_id": "A",
                "primary_fumble": False,
                "first_recovery_retained": None,
                "bad_snap": False,
                "kind": "yards",
            },
        ]
    return result


def test_aggregation_separates_primary_from_return_only_recovery_trace() -> None:
    from tools.chartgen.refine import aggregate_games

    summary = aggregate_games([metric_game(primary=False, recovery_trace=True)], team_filter="A")
    assert summary["metrics"]["fumble"]["value"] == 0
    assert summary["metrics"]["chain_fumble_recovery"]["numerator"] == 1


def test_aggregation_counts_dead_ball_primary_without_recovery_roll() -> None:
    from tools.chartgen.refine import aggregate_games

    summary = aggregate_games([metric_game(primary=True, recovery_trace=False)], team_filter="A")
    assert summary["metrics"]["fumble"]["numerator"] == 1
    assert summary["metrics"]["chain_fumble_recovery"]["numerator"] == 0


def test_legacy_result_without_primary_observation_is_not_a_zero_fumble_sample() -> None:
    from tools.chartgen.refine import aggregate_games

    summary = aggregate_games([metric_game(primary=None, recovery_trace=False)], team_filter="A")
    assert "fumble" not in summary["metrics"]
    assert summary["primary_observation_coverage"]["unqualified_team_games"] == 1


def test_compaction_preserves_primary_observation_facts() -> None:
    from tools.chartgen.cohort_simulation import compact_metric_result

    result = metric_game(primary=True, recovery_trace=False)
    compact = compact_metric_result(result)
    assert compact["normalized_primary_results"] == result["normalized_primary_results"]


def test_source_primary_coverage_discloses_unknowns_and_holder_inference() -> None:
    from tools.chartgen.primary_fumbles import primary_source_coverage

    sample = source_sample(return_fumble=True)
    sample[0] = replace(sample[0], fumble=True, fumble_team=None)
    sample[1] = replace(sample[1], fumble=None)
    coverage = primary_source_coverage(sample)
    assert coverage["eligible_snaps"] == 3
    assert coverage["known_primary_fumble"] == 1
    assert coverage["known_no_primary_fumble"] == 1
    assert coverage["unknown_primary_fumble"] == 1
    assert coverage["inferred_primary_holder"] == 1
    assert coverage["known_return_holder_excluded_from_primary"] == 1


def test_defensive_target_matches_opponents_offense_without_mutating_holders() -> None:
    sample = source_sample(return_fumble=True)
    own = source_targets(sample, ["a"])
    allowed = source_targets(sample, ["b"], role="defense")
    for metric in [
        "completion",
        "interception",
        "sack",
        "pure_rush_yards_per_attempt",
        "pass_yards_per_attempt",
        "fumble",
    ]:
        assert allowed[metric] == own[metric]


def test_mixed_legacy_batch_does_not_fit_only_its_identified_subset() -> None:
    from tools.chartgen.refine import aggregate_games

    summary = aggregate_games(
        [
            metric_game(primary=True, recovery_trace=False),
            metric_game(primary=None, recovery_trace=True),
        ],
        team_filter="A",
    )
    assert "fumble" not in summary["metrics"]
    assert summary["primary_observation_coverage"]["qualified_primary_snaps"] == 2
    assert summary["primary_observation_coverage"]["unqualified_team_games"] == 1
    assert summary["metrics"]["chain_fumble_recovery"]["numerator"] == 1


@pytest.mark.parametrize("damage", ["missing", "duplicate", "owner"])
def test_metric_aggregation_rejects_mismatched_primary_observations(damage: str) -> None:
    from tools.chartgen.refine import aggregate_games

    result = metric_game(primary=True, recovery_trace=False)
    if damage == "missing":
        result["normalized_primary_results"].pop()
    elif damage == "duplicate":
        result["normalized_primary_results"].append(result["normalized_primary_results"][0])
    else:
        result["normalized_primary_results"][0]["offense_id"] = "B"
    with pytest.raises(ValueError, match="primary observation"):
        aggregate_games([result], team_filter="A")


def test_nonempty_statistics_cannot_have_empty_primary_observation_coverage() -> None:
    from tools.chartgen.refine import aggregate_games

    result = metric_game(primary=True, recovery_trace=False)
    result["engine_log"] = []
    result["normalized_primary_results"] = []
    with pytest.raises(ValueError, match="primary observation"):
        aggregate_games([result], team_filter="A")
