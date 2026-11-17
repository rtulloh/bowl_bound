"""Located FG evidence is required independently of exploratory point losses."""

import sys
from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from types import FrameType

import pytest

from bowl_bound.game_state import Possession
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    ResultKind,
    SpecialTeamsColumn,
    TeamChart,
)
from tests.synthetic_teams import team_chart, yards
from tests.test_models import provenance
from tools.chartgen.readiness import qualification_status
from tools.chartgen.scope import CORE_METRICS


def test_required_located_field_goal_evidence_is_not_silently_omitted() -> None:
    ordinary = {
        "passed": True,
        "metrics": {name: {"passed": True} for name in CORE_METRICS},
        "unidentifiable_source_metrics": [],
        "historically_sparse_metrics": [],
        "historical_exposure": {
            "qualified": True,
            "metrics": {name: {"qualified": True} for name in CORE_METRICS},
        },
    }
    result = qualification_status(
        failed_games=0,
        per_team={
            "a": {
                "state": "fit",
                "offense_assessment": deepcopy(ordinary),
                "defense_assessment": deepcopy(ordinary),
            }
        },
        coverage={"complete": True},
        expected_teams=("a",),
    )

    # Unfrozen precision already prevents GO, but must not hide this independent
    # required-evidence gap or permit its omission when precision is supplied.
    assert result["state"] == "unverified" and result["passed"] is False
    assert not result["known_failures"]
    assert "precision_contract_unfrozen" in result["missing_evidence"]
    assert "a/offense:located_field_goal_qualification" in result["missing_evidence"]


def field_goal_chart(cell_at: Callable[[int], NormalizedCell]) -> TeamChart:
    chart = team_chart("Fictional Kicker", season=2007)
    return replace(
        chart,
        special_teams=tuple(
            replace(row, cell=cell_at(row.roll))
            if row.column is SpecialTeamsColumn.FIELD_GOAL
            else row
            for row in chart.special_teams
        ),
    )


@pytest.mark.parametrize("possession", (Possession.HOME, Possession.AWAY))
def test_actual_engine_distinguishes_equal_pooled_but_wrong_located_curves(
    possession: Possession,
) -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart
    from tools.chartgen.research_inputs import semantic_sha256

    correct = field_goal_chart(lambda _: yards(30))
    wrong = field_goal_chart(lambda total: yards(50 if total >= 30 else 10))
    receiving = team_chart("Fictional Receiver", season=2007)
    original = semantic_sha256((correct, wrong, receiving))
    for name in ("offense", "defense", "supplemental", "pat_outcomes"):
        assert getattr(correct, name) == getattr(wrong, name)
    assert [r for r in correct.special_teams if r.column is not SpecialTeamsColumn.FIELD_GOAL] == [
        r for r in wrong.special_teams if r.column is not SpecialTeamsColumn.FIELD_GOAL
    ]

    expected = audit_field_goal_chart(
        correct, receiving, yards_to_goal=(20, 40), possession=possession
    )
    corrupted = audit_field_goal_chart(
        wrong, receiving, yards_to_goal=(20, 40), possession=possession
    )
    expected_good = [expected["locations"][str(spot)]["good_mass"] for spot in (20, 40)]
    wrong_good = [corrupted["locations"][str(spot)]["good_mass"] for spot in (20, 40)]
    assert expected_good == [216, 0]
    assert wrong_good == [108, 108]
    assert sum(expected_good) == sum(wrong_good) == 216  # Same pooled 0.5, wrong at BOTH LOS.
    for result in (expected, corrupted):
        assert result["scope"] == "closed_numeric_ng_only"
        assert result["source_qualification"] == "unverified"
        assert result["engine"]["runtime_origins_verified"] is True
        assert result["engine"]["reviewed_engine_verified"] is True
        assert result["input_identity"]["algorithm"] == "bb-research-inputs-v1"
        assert result["context"]["possession"] == possession.value
        assert result["context"]["home_season"] == 2007
        assert result["context"]["advanced_ii"] is False
        assert result["context"]["regulation_clock"] is None
        assert result["context"]["overtime"] is False
        for location in result["locations"].values():
            assert location["initial_face_mass"] == location["accounted_mass"] == 216
            assert location["good_mass"] + location["missed_mass"] == 216
            assert location["unsupported_mass"] == location["engine_error_mass"] == 0
            assert location["unexpected_pending_mass"] == location["illegal_action_mass"] == 0
            assert location["unclassified_terminal_mass"] == 0
            assert location["numeric_conditional_denominator"] == 216
    assert semantic_sha256((correct, wrong, receiving)) == original


def test_ng_uses_actual_engine_miss_without_inventing_numeric_range() -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart

    chart = field_goal_chart(lambda _: NormalizedCell(ResultKind.NO_GOOD_FIELD_GOAL, provenance()))
    result = audit_field_goal_chart(
        chart, team_chart("Fictional Receiver", season=2007), yards_to_goal=(20,)
    )
    location = result["locations"]["20"]
    assert location["good_mass"] == 0 and location["missed_mass"] == 216
    assert location["unsupported_mass"] == 0 and location["accounted_mass"] == 216


def test_actual_threshold_equality_and_both_neighbors_remain_distinct() -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart

    result = audit_field_goal_chart(
        field_goal_chart(lambda _: yards(30)),
        team_chart("Fictional Receiver", season=2007),
        yards_to_goal=(29, 30, 31),
    )
    assert [result["locations"][str(spot)]["good_mass"] for spot in (29, 30, 31)] == [
        216,
        216,
        0,
    ]


def test_mixed_numeric_and_unsupported_mass_is_not_renormalized_into_all_faces() -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart

    chart = field_goal_chart(
        lambda total: (
            NormalizedCell(ResultKind.FUMBLE, provenance(), yards=2) if total >= 30 else yards(30)
        )
    )
    result = audit_field_goal_chart(
        chart, team_chart("Fictional Receiver", season=2007), yards_to_goal=(20, 40)
    )
    short, long = (result["locations"][str(spot)] for spot in (20, 40))
    assert short["good_mass"] == long["missed_mass"] == 108
    assert short["missed_mass"] == long["good_mass"] == 0
    for location in (short, long):
        assert location["unsupported_mass"] == 108
        assert location["accounted_mass"] == location["initial_face_mass"] == 216
        assert location["numeric_conditional_denominator"] == 108
    assert short["numeric_conditional_numerator"] == 108
    assert short["numeric_conditional_success"] == 1.0  # Conditional only, good mass108/216.
    assert long["numeric_conditional_numerator"] == 0
    assert long["numeric_conditional_success"] == 0.0
    assert result["source_qualification"] == "unverified"


@pytest.mark.parametrize(
    ("possession", "home_season", "home_identity"),
    ((Possession.HOME, 2007, "kicking"), (Possession.AWAY, 2008, "receiving")),
)
def test_context_identity_records_the_actual_home_season_and_both_seats(
    possession: Possession, home_season: int, home_identity: str
) -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart

    result = audit_field_goal_chart(
        field_goal_chart(lambda _: yards(30)),
        team_chart("Fictional Receiver", season=2008),
        yards_to_goal=(20,),
        possession=possession,
    )
    assert result["context"]["home_season"] == home_season
    assert result["context"]["seats"]["home"] == home_identity
    assert set(result["context"]["seats"].values()) == {"kicking", "receiving"}


@pytest.mark.parametrize(
    "cell",
    (
        NormalizedCell(ResultKind.FUMBLE, provenance(), yards=2),
        NormalizedCell(ResultKind.BLOCKED_KICK, provenance(), yards=2),
        NormalizedCell(
            ResultKind.PENALTY,
            provenance(),
            penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
        ),
    ),
)
def test_initial_nonclosed_procedure_retains_all_mass_as_unsupported(cell: NormalizedCell) -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart

    result = audit_field_goal_chart(
        field_goal_chart(lambda _: cell),
        team_chart("Fictional Receiver", season=2007),
        yards_to_goal=(20,),
    )
    location = result["locations"]["20"]
    assert location["unsupported_mass"] == location["accounted_mass"] == 216
    assert location["good_mass"] == location["missed_mass"] == 0
    assert location["unsupported_kinds"] == {cell.kind.value: 216}
    assert location["numeric_conditional_success"] is None
    assert location["numeric_conditional_numerator"] == 0
    assert location["numeric_conditional_denominator"] == 0


def test_actual_legal_action_view_refuses_a_field_goal_from_own_end_line() -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart

    result = audit_field_goal_chart(
        field_goal_chart(lambda _: yards(99)),
        team_chart("Fictional Receiver", season=2007),
        yards_to_goal=(99,),
    )
    location = result["locations"]["99"]
    assert location["illegal_action_mass"] == location["accounted_mass"] == 216
    assert location["good_mass"] == location["missed_mass"] == 0


@pytest.mark.parametrize("spots", ((), (20, 20), (True,), (0,), (100,), (20.0,), ("20",)))
def test_context_inventory_rejects_invalid_or_duplicated_locations(spots: tuple) -> None:
    from tools.chartgen.field_goals import audit_field_goal_chart

    with pytest.raises((TypeError, ValueError)):
        audit_field_goal_chart(
            field_goal_chart(lambda _: yards(30)),
            team_chart("Fictional Receiver", season=2007),
            yards_to_goal=spots,
        )


def test_changed_caller_context_is_refused_before_returning_reusable_diagnostic() -> None:
    from bowl_bound.session import PlaySession
    from tools.chartgen.field_goals import audit_field_goal_chart
    from tools.chartgen.research_inputs import InputConsistencyError

    spots = [20]
    changed = False

    def mutate_context(frame: FrameType, event: str, arg: object) -> None:
        nonlocal changed
        if event == "call" and frame.f_code is PlaySession.kick.__code__ and not changed:
            spots.append(40)
            changed = True

    prior = sys.getprofile()
    sys.setprofile(mutate_context)
    try:
        with pytest.raises(InputConsistencyError):
            audit_field_goal_chart(
                field_goal_chart(lambda _: yards(30)),
                team_chart("Fictional Receiver", season=2007),
                yards_to_goal=spots,
            )
    finally:
        sys.setprofile(prior)
    assert changed
