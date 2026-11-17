"""Narrow policy alternative preserves printed source response allocations exactly."""

from dataclasses import fields, replace
from itertools import combinations, product

import pytest

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.models import (
    Defense,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    Priority,
    ResultKind,
    TeamChart,
)
from bowl_bound.resolution import Operation, resolve_cells, resolve_play
from tests.chartgen.tactical_fixtures import mean, outcomes
from tests.chartgen.test_generation import events as events
from tests.synthetic_teams import team_chart, yards
from tools.chartgen.evidence import Event
from tools.chartgen.generate import EvidenceModel, generate_team
from tools.chartgen.tactics import TacticalProfile, TacticDelta

APPROVED_SHA = "bbb35953b3812769bde39d5c567fc21dece00b0899cb037feaad0db7aa88280c"


def test_selected_factory_is_independent_of_rejected_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden() -> TacticalProfile:
        raise AssertionError("selected policy depends on rejected probability proposal")

    monkeypatch.setattr(TacticalProfile, "bowl_bound_v1", forbidden, raising=False)
    assert TacticalProfile.bowl_bound_yardage_v1().sha256 == APPROVED_SHA


def test_rejected_and_mutated_authored_profiles_cannot_enter_generation(
    events: list[Event],
) -> None:
    rejected = replace(TacticalProfile.neutral(), origin="authored-bb-v1")
    with pytest.raises(ValueError, match="rejected probability-changing"):
        generate_team(events, "1", "Cedar Valley", 2007, tactics=rejected)
    selected = TacticalProfile.bowl_bound_yardage_v1()
    mutated = replace(
        selected, effects=tuple(replace(e, yard_offset=0.0) for e in selected.effects)
    )
    with pytest.raises(ValueError, match="approved tactical policy hash"):
        generate_team(events, "1", "Cedar Valley", 2007, tactics=mutated)


def test_corrected_release_requires_explicit_approved_pin() -> None:
    with pytest.raises(ValueError, match="approved tactical policy hash"):
        TacticalProfile.for_corrected_release("0" * 64)
    selected = TacticalProfile.for_corrected_release(APPROVED_SHA)
    assert selected.origin == "authored-bb-yardage-v1" and selected.sha256 == APPROVED_SHA


@pytest.mark.parametrize(
    "kind",
    (
        "ordinary",
        "parentheses",
        "incomplete",
        "interception",
        "fumble",
        "B",
        "QR",
        "QT",
        "SOP",
        "BLP",
        "penalty",
    ),
)
@pytest.mark.parametrize("completion_effect", (-0.07, 0.07))
def test_selected_policy_actual_engine_priority_and_supplemental_kinds(
    events: list[Event], kind: str, completion_effect: float
) -> None:
    defense, _, _ = generate_team(
        events,
        "1",
        "Cedar Valley",
        2007,
        seed=19,
        model=_model(events, 0.4, completion_effect),
        tactics=TacticalProfile.bowl_bound_yardage_v1(),
    )
    offense = team_chart("Original Synthetic", season=2007, offense=9)
    play = (
        Play.FIVE if kind in {"SOP", "BLP"} else Play.ONE if kind in {"B", "fumble"} else Play.NINE
    )
    cell = yards(10)
    if kind == "parentheses":
        cell = replace(yards(12), priority=Priority.PARENTHESIZED)
    elif kind == "interception":
        cell = NormalizedCell(ResultKind.INTERCEPTION, cell.provenance, yards=20)
    elif kind == "fumble":
        cell = NormalizedCell(ResultKind.FUMBLE, cell.provenance, yards=4)
    elif kind == "penalty":
        cell = NormalizedCell(
            ResultKind.PENALTY,
            cell.provenance,
            penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5),
        )
    elif kind in {"incomplete", "B", "QR", "QT", "SOP", "BLP"}:
        cell = NormalizedCell(
            {
                "incomplete": ResultKind.INCOMPLETE,
                "B": ResultKind.BREAKAWAY,
                "QR": ResultKind.QUARTERBACK_RUN,
                "QT": ResultKind.QUARTERBACK_TRAPPED,
                "SOP": ResultKind.SPRINT_OUT_PASS,
                "BLP": ResultKind.BOOTLEG_PASS,
            }[kind],
            cell.provenance,
        )
    offense = replace(
        offense,
        offense=tuple(replace(r, cell=cell) if r.play is play else r for r in offense.offense),
        supplemental=tuple(
            replace(r, cell=yards({"B": 20, "QR": 7, "QT": -6}[r.column.value]))
            for r in offense.supplemental
        ),
    )
    witnesses = set()
    for formation in Defense:
        records = {
            r.roll: r.cell for r in defense.defense if r.play is play and r.defense is formation
        }
        for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
            offensive = OffensiveRoll(*faces)
            for red, green in product(RED_FACES, GREEN_FACES):
                defensive = DefensiveRoll(red, green)
                expected = resolve_cells(cell, records[defensive.total])
                result = resolve_play(
                    offense,
                    defense,
                    play,
                    formation,
                    ScriptedDice([offensive, defensive, OffensiveRoll(1, 0, 0)]),
                )
                assert result.trace[0].roll == offensive and result.trace[0].cell == cell
                assert (
                    result.trace[1].roll == defensive
                    and result.trace[1].cell == records[defensive.total]
                )
                witnesses.add(expected.kind)
                if kind in {"SOP", "BLP"}:
                    assert result.result.yards == 9
                    assert result.resolved_play is (Play.SEVEN if kind == "SOP" else Play.EIGHT)
                    assert len(result.trace) == 3
                elif kind == "parentheses":
                    assert result.result.yards == 12 and not result.result.pending
                    assert len(result.trace) == 2
                elif expected.kind in {
                    ResultKind.BREAKAWAY,
                    ResultKind.QUARTERBACK_RUN,
                    ResultKind.QUARTERBACK_TRAPPED,
                }:
                    support = {
                        ResultKind.BREAKAWAY: 20,
                        ResultKind.QUARTERBACK_RUN: 7,
                        ResultKind.QUARTERBACK_TRAPPED: -6,
                    }[expected.kind]
                    if expected.operation is Operation.ADD:
                        support += records[defensive.total].yards or 0
                    assert result.result.yards == support and not result.result.pending
                    assert len(result.trace) == 3
                else:
                    assert result.result.kind is expected.kind
                    assert result.result.yards == expected.yards
                    assert result.result.pending == expected.pending
                    assert len(result.trace) == 2
    if kind in {"B", "QR", "QT"}:
        assert {
            "B": ResultKind.BREAKAWAY,
            "QR": ResultKind.QUARTERBACK_RUN,
            "QT": ResultKind.QUARTERBACK_TRAPPED,
        }[kind] in witnesses


def test_yardage_policy_has_no_authored_event_rates() -> None:
    policy = TacticalProfile.bowl_bound_yardage_v1()
    assert policy.origin == "authored-bb-yardage-v1"
    assert policy.source_hashes == ()
    assert TacticalProfile.from_dict(policy.to_dict()) == policy
    for effect in policy.effects:
        assert all(getattr(effect, field.name) == 0 for field in fields(TacticDelta)[3:])
    for play in Play:
        assert sum(policy.lookup(f, play).yard_offset for f in Defense) == 0


def _model(events: list[Event], strength: float, completion: float) -> EvidenceModel:
    return replace(
        EvidenceModel.from_events(events),
        run_effects={"1": strength},
        pass_effects={"1": strength},
        rate_effects={
            "complete": {"1": completion},
            "interception": {"1": 0.035},
            "sack": {"1": 0.04},
        },
    )


@pytest.mark.parametrize("seed", (3, 19, 41))
@pytest.mark.parametrize("completion", (-0.07, 0.0, 0.07))
def test_numeric_roles_response_invariance_and_strength(
    events: list[Event], seed: int, completion: float
) -> None:
    charts: dict[float, TeamChart] = {}
    for strength in (-1.4, 0.0, 1.4):
        model = _model(events, strength, completion)
        neutral, old_metadata, old = generate_team(
            events, "1", "Cedar Valley", 2007, seed=seed, model=model
        )
        authored, metadata, new = generate_team(
            events,
            "1",
            "Cedar Valley",
            2007,
            seed=seed,
            model=model,
            tactics=TacticalProfile.bowl_bound_yardage_v1(),
        )
        charts[strength] = authored
        assert metadata == old_metadata
        for section in (
            "offense",
            "supplemental",
            "special_teams",
            "pat_outcomes",
            "recovery_range",
        ):
            assert getattr(neutral, section) == getattr(authored, section)
        for key in ("family_evidence", "supplemental_evidence", "source_summary", "opponent_model"):
            assert old[key] == new[key]
        for address, old_q in old["defensive_quantization"].items():
            if int(address.split("/")[1]) >= 6:
                assert (
                    old_q["semantic_allocations"]
                    == new["defensive_quantization"][address]["semantic_allocations"]
                )
        for old_record, new_record in zip(neutral.defense, authored.defense, strict=True):
            assert (old_record.defense, old_record.play, old_record.roll) == (
                new_record.defense,
                new_record.play,
                new_record.roll,
            )
            if old_record.cell.kind not in {ResultKind.YARDS, ResultKind.NO_CHANGE}:
                assert old_record.cell == new_record.cell
            else:
                assert new_record.cell.kind in {ResultKind.YARDS, ResultKind.NO_CHANGE}
                assert old_record.cell.priority is new_record.cell.priority
        for gain in (4, 10, 18):
            m = {(p, f): mean(outcomes(authored, p, f, gain)) for p in Play for f in Defense}
            assert m[Play.ONE, Defense.B] < m[Play.ONE, Defense.A] < m[Play.ONE, Defense.E]
            assert m[Play.THREE, Defense.C] < m[Play.THREE, Defense.A] < m[Play.THREE, Defense.B]
            assert m[Play.FOUR, Defense.A] < m[Play.FOUR, Defense.F]
            assert m[Play.SIX, Defense.D] < m[Play.SIX, Defense.A] < m[Play.SIX, Defense.F]
            assert m[Play.SEVEN, Defense.D] < m[Play.SEVEN, Defense.F] < m[Play.SEVEN, Defense.E]
            assert m[Play.NINE, Defense.E] < m[Play.NINE, Defense.F] < m[Play.NINE, Defense.B]
            assert m[Play.EIGHT, Defense.A] < m[Play.EIGHT, Defense.F]
            for first, second in combinations(Defense, 2):
                assert any(m[p, first] < m[p, second] for p in Play)
                assert any(m[p, first] > m[p, second] for p in Play)
    for play in Play:
        for formation in Defense:
            strong, balanced, weak = (
                mean(outcomes(charts[s], play, formation, 10)) for s in (-1.4, 0.0, 1.4)
            )
            assert strong < balanced < weak
