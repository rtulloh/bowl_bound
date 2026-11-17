"""Complete supplied facts retain their types and detached snapshot identity."""

import copy
import pickle
import sys
from dataclasses import fields, is_dataclass, replace
from types import FrameType
from typing import Any

import pytest

from bowl_bound.models import Play
from bowl_bound.team_csv import team_to_files
from tests.synthetic_teams import metadata, team_chart
from tools.chartgen.research_inputs import (
    FrozenResearchInputs,
    require_team_inputs,
    semantic_sha256,
)


def inputs() -> dict:
    return {
        "teams": {"2007/a": (team_chart("A"), metadata())},
        "manifest": {"teams": {"a": {"source_known": None}}, "games": []},
        "catalog": {"a": "2007/a"},
        "targets": {"a": {"offense": {"completion": 0.5}}},
    }


@pytest.mark.parametrize("value", (None, False, 0, 0.0, -0.0, "0", Play.ONE, 1, True, 1.0))
def test_semantic_identity_distinguishes_source_types(value: object) -> None:
    values = (None, False, 0, 0.0, -0.0, "0", Play.ONE, 1, True, 1.0)
    assert len({semantic_sha256(item) for item in values}) == len(values)
    assert semantic_sha256(value) == semantic_sha256(value)


def test_semantic_identity_retains_order_but_not_dict_insertion_order() -> None:
    assert semantic_sha256({"a": [1, 2], "b": None}) == semantic_sha256({"b": None, "a": [1, 2]})
    assert semantic_sha256([1, 2]) != semantic_sha256([2, 1])
    assert semantic_sha256([1, 2]) != semantic_sha256((1, 2))
    assert semantic_sha256(range(1, 4)) != semantic_sha256((1, 2, 3))


@pytest.mark.parametrize("change", ("provenance", "metadata_evidence"))
def test_complete_chart_identity_covers_facts_lost_by_csv_hash(change: str) -> None:
    chart, meta = team_chart("A"), metadata()
    changed_chart, changed_meta = chart, meta
    if change == "provenance":
        record = chart.offense[0]
        provenance = replace(record.cell.provenance, original_text="different original evidence")
        changed_chart = replace(
            chart,
            offense=(
                replace(record, cell=replace(record.cell, provenance=provenance)),
                *chart.offense[1:],
            ),
        )
    elif change == "metadata_evidence":
        changed_meta = replace(meta, evidence=(("new evidence", chart.offense[0].cell.provenance),))
    assert team_to_files(chart, meta) == team_to_files(changed_chart, changed_meta)
    assert semantic_sha256((chart, meta)) != semantic_sha256((changed_chart, changed_meta))


def test_snapshot_detaches_all_nested_objects_and_preserves_internal_aliases() -> None:
    original = inputs()
    original["manifest"]["shared"] = original["targets"]["a"]
    frozen = FrozenResearchInputs.capture(**original)
    detached = frozen.values
    assert detached["manifest"]["shared"] is detached["targets"]["a"]
    assert detached["targets"]["a"] is not original["targets"]["a"]
    assert detached["teams"]["2007/a"][0] is not original["teams"]["2007/a"][0]
    assert detached["teams"]["2007/a"][0].offense[0].cell.provenance is not (
        original["teams"]["2007/a"][0].offense[0].cell.provenance
    )
    frozen.check("unchanged")
    original["targets"]["a"]["offense"]["completion"] = None
    assert detached["targets"]["a"]["offense"]["completion"] == 0.5
    with pytest.raises(ValueError, match="frozen simulation inputs.*original.*targets"):
        frozen.check("caller changed")


def test_exported_descriptor_cannot_repin_expected_snapshot() -> None:
    frozen = FrozenResearchInputs.capture(**inputs())
    identity = frozen.identity
    identity["components"]["targets"] = "0" * 64
    assert frozen.identity != identity
    frozen.values["targets"]["a"]["offense"]["completion"] = 0.7
    with pytest.raises(ValueError, match="frozen simulation inputs.*snapshot.*targets"):
        frozen.check("snapshot changed")


@pytest.mark.parametrize("value", (float("nan"), float("inf"), object(), {1: "bad key"}, {"set"}))
def test_unsupported_or_nonfinite_facts_fail_closed(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="research input"):
        semantic_sha256(value)


def test_cycles_are_rejected_but_repeated_aliases_are_supported() -> None:
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match="research input.*cycle"):
        semantic_sha256(cyclic)
    child = [1, None]
    assert semantic_sha256([child, child]) == semantic_sha256([[1, None], [1, None]])


def test_caller_restored_between_guards_cannot_change_detached_computation() -> None:
    original = inputs()
    frozen = FrozenResearchInputs.capture(**original)
    original["targets"]["a"]["offense"]["completion"] = 0.8
    assert frozen.values["targets"]["a"]["offense"]["completion"] == 0.5
    original["targets"]["a"]["offense"]["completion"] = 0.5
    frozen.check("restored caller, unchanged detached computation")


@pytest.mark.parametrize("change", ("missing", "extra", "metadata", "chart"))
def test_worker_rejects_wrong_consumed_chart_or_inventory(change: str) -> None:
    original = inputs()
    frozen = FrozenResearchInputs.capture(**original)
    teams = frozen.values["teams"]
    if change == "missing":
        teams.clear()
    elif change == "extra":
        teams["unexpected"] = teams["2007/a"]
    elif change == "metadata":
        chart, meta = teams["2007/a"]
        teams["2007/a"] = (chart, replace(meta, power_rating=201))
    else:
        teams["2007/a"] = (team_chart("A", offense=17), metadata())
    with pytest.raises(ValueError, match="frozen simulation inputs.*worker charts"):
        require_team_inputs(teams, frozen.identity, ("2007/a",))


def test_worker_receipt_records_exact_complete_consumed_pairs() -> None:
    frozen = FrozenResearchInputs.capture(**inputs())
    assert (
        require_team_inputs(frozen.values["teams"], frozen.identity, ("2007/a",))
        == (frozen.identity["team_sha256"])
    )


@pytest.mark.parametrize("change", ("cycle", "nonfinite", "unknown_type", "unknown_support"))
def test_late_invalid_and_unknown_changes_retain_refusal_evidence(change: str) -> None:
    original = inputs()
    frozen = FrozenResearchInputs.capture(**original)
    if change == "cycle":
        original["manifest"]["cycle"] = original["manifest"]
    elif change == "nonfinite":
        original["targets"]["bad"] = float("nan")
    elif change == "unknown_type":
        original["targets"]["bad"] = object()
    else:
        original["manifest"]["teams"]["a"]["source_known"] = False
    with pytest.raises(ValueError, match="frozen simulation inputs.*original") as raised:
        frozen.check("invalid caller")
    assert raised.value.evidence["stage"] == "invalid caller"
    assert raised.value.evidence["expected"] == frozen.identity
    assert raised.value.evidence["changed_components"]


def test_worker_refusal_preserves_hash_evidence_when_pickled() -> None:
    frozen = FrozenResearchInputs.capture(**inputs())
    frozen.values["teams"].clear()
    with pytest.raises(ValueError) as raised:
        require_team_inputs(frozen.values["teams"], frozen.identity)
    recovered = pickle.loads(pickle.dumps(raised.value))
    assert type(recovered) is type(raised.value)
    assert str(recovered) == str(raised.value)
    assert recovered.evidence == raised.value.evidence


def test_complete_snapshot_shares_no_mutable_container_or_chart_dataclass() -> None:
    original = inputs()
    frozen = FrozenResearchInputs.capture(**original)

    def captured_objects(value: object) -> set[int]:
        if is_dataclass(value):
            children = [getattr(value, field.name) for field in fields(value)]
        elif isinstance(value, dict):
            children = list(value.values())
        elif isinstance(value, (list, tuple)):
            children = list(value)
        else:
            return set()
        own = {id(value)} if is_dataclass(value) or isinstance(value, (dict, list)) else set()
        return own.union(*(captured_objects(child) for child in children))

    assert captured_objects(original).isdisjoint(captured_objects(frozen.values))


def test_mutation_during_capture_cannot_become_its_new_expectation() -> None:
    original = inputs()
    changed = []

    def observe(frame: FrameType, event: str, argument: Any) -> None:
        if not changed and event == "call" and frame.f_code is copy.deepcopy.__code__:
            original["targets"]["a"]["offense"]["completion"] = 0.8
            changed.append(True)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        with pytest.raises(
            ValueError, match="frozen simulation inputs.*capture.*original.*targets"
        ):
            FrozenResearchInputs.capture(**original)
    finally:
        sys.setprofile(previous)
    assert changed == [True]


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("entry", ("capture", "worker"))
def test_duplicate_exact_names_refused_before_snapshot_or_worker_execution(
    reverse: bool,
    entry: str,
) -> None:
    from tools.chartgen.cohort_simulation import _initialize_worker

    original = inputs()
    original["teams"]["unused/duplicate"] = original["teams"]["2007/a"]
    if reverse:
        original["teams"] = dict(reversed(list(original["teams"].items())))
    with pytest.raises(ValueError, match="duplicate chart names"):
        if entry == "capture":
            FrozenResearchInputs.capture(**original)
        else:
            _initialize_worker(original["teams"])


@pytest.mark.parametrize("other_name", ("a", "A ", "Different"))
def test_admission_keeps_distinct_exact_names_without_case_or_whitespace_folding(
    other_name: str,
) -> None:
    original = inputs()
    chart, meta = original["teams"]["2007/a"]
    original["teams"]["unused/distinct"] = (replace(chart, name=other_name), meta)
    frozen = FrozenResearchInputs.capture(**original)
    frozen.check("distinct exact names")


@pytest.mark.parametrize("name", (None, True, 1, "", ["A"]))
def test_admission_refuses_nonstring_or_empty_name_before_lookup_rules(name: object) -> None:
    original = inputs()
    chart, _ = original["teams"]["2007/a"]
    # Fault-inject source data only; no engine/model code is patched.
    object.__setattr__(chart, "name", name)
    with pytest.raises(ValueError, match="nonempty string chart names"):
        FrozenResearchInputs.capture(**original)
