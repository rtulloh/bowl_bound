"""Private transport must preserve complete chart and gameplay-metadata facts."""

import hashlib
import json
from dataclasses import replace

import pytest

from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.team_csv import TeamFileMetadata, TeamFormatError, team_to_files
from tests.chartgen.test_typed_event_model import legacy_factory
from tools.chartgen.private_bundle import (
    decode_private_bundle,
    encode_private_bundle,
    gameplay_metadata_sha256,
)
from tools.chartgen.research_inputs import semantic_sha256
from tools.chartgen.typed_event_risks import apply_typed_event_model


def subject():
    baseline = legacy_factory()
    first = baseline.offense[0].cell.provenance
    metadata = TeamFileMetadata(5.5, (), "Fictional", first.source_sha256, ())
    candidate, receipt = apply_typed_event_model(baseline)
    return baseline, candidate, metadata, receipt


def hashes(files):
    return {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}


def decode(files, candidate, metadata, receipt, **overrides):
    expected = {
        "expected_file_hashes": hashes(files),
        "expected_output_sha256": semantic_sha256(candidate),
        "expected_model_sha256": receipt["model_identity"]["sha256"],
        "expected_gameplay_metadata_sha256": gameplay_metadata_sha256(metadata),
    }
    return decode_private_bundle(files, **(expected | overrides))


def test_canonical_csv_guard_still_refuses_mixed_source_as_one_old_source():
    baseline, candidate, metadata, _ = subject()
    assert team_to_files(baseline, metadata)
    with pytest.raises(TeamFormatError, match="hash mismatch"):
        team_to_files(candidate, metadata)


def test_complete_private_roundtrip_restores_all_facts_ancestry_and_tuple_order():
    _, candidate, metadata, receipt = subject()
    candidate = replace(
        candidate,
        offense=tuple(reversed(candidate.offense)),
        defense=tuple(reversed(candidate.defense)),
    )
    receipt = {**receipt, "output_sha256": semantic_sha256(candidate)}
    files = encode_private_bundle(candidate, metadata, receipt)
    assert set(files) == {
        "team.yaml",
        "offense.csv",
        "defense.csv",
        "special.csv",
        "provenance.csv",
        "ancestry.json",
    }
    loaded, transport_meta = decode(files, candidate, metadata, receipt)
    assert loaded == candidate
    assert semantic_sha256(loaded) == receipt["output_sha256"]
    assert gameplay_metadata_sha256(transport_meta) == gameplay_metadata_sha256(metadata)
    assert transport_meta.source_sha256 == hashes(files)["ancestry.json"]
    assert all(
        row.cell.provenance.source_sha256 != transport_meta.source_sha256 for row in loaded.offense
    )


@pytest.mark.parametrize(
    "name",
    ["team.yaml", "offense.csv", "defense.csv", "special.csv", "provenance.csv", "ancestry.json"],
)
def test_every_transport_input_requires_the_frozen_external_hash(name):
    _, candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)
    expected = hashes(files)
    files[name] += "\n"
    with pytest.raises(ValueError, match="hash"):
        decode(files, candidate, metadata, receipt, expected_file_hashes=expected)


@pytest.mark.parametrize(
    "key,label",
    [
        ("expected_output_sha256", "output"),
        ("expected_model_sha256", "model"),
        ("expected_gameplay_metadata_sha256", "metadata"),
    ],
)
def test_candidate_cannot_self_authorize_different_reviewed_facts(key, label):
    _, candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)
    with pytest.raises(ValueError, match=label):
        decode(files, candidate, metadata, receipt, **{key: "0" * 64})


def test_missing_ancestry_cannot_be_loaded_as_an_ordinary_derived_csv():
    _, candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)
    del files["ancestry.json"]
    with pytest.raises(ValueError, match="inventory"):
        decode(files, candidate, metadata, receipt)


def rebase(files, mutate):
    """Fault injection repins transport bytes but preserves reviewed object IDs."""
    original = hashes(files)["ancestry.json"]
    ledger = json.loads(files["ancestry.json"])
    mutate(ledger)
    files["ancestry.json"] = json.dumps(ledger, sort_keys=True, separators=(",", ":")) + "\n"
    files["team.yaml"] = files["team.yaml"].replace(original, hashes(files)["ancestry.json"])


@pytest.mark.parametrize(
    "fault",
    ["duplicate", "missing", "bool-coordinate", "wrong-provenance", "wrong-producer-output"],
)
def test_repinned_container_cannot_hide_bad_ancestry_or_inconsistent_receipts(fault):
    _, candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)

    def mutate(ledger):
        if fault == "duplicate":
            ledger["records"][-1] = ledger["records"][0]
        elif fault == "missing":
            ledger["records"].pop()
        elif fault == "bool-coordinate":
            ledger["records"][0]["coordinate"][0] = True
        elif fault == "wrong-provenance":
            ledger["records"][0]["provenance"]["source_sha256"] = "b" * 64
        else:
            ledger["producer_receipt"]["output_sha256"] = "b" * 64

    rebase(files, mutate)
    with pytest.raises(ValueError):
        decode(files, candidate, metadata, receipt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("page", True),
        ("page", 0),
        ("rgb_color", [True, 0, 0]),
        ("bounding_box", {"left": 0, "bottom": 0, "right": 0, "top": 1}),
    ],
)
def test_sidecar_source_fields_remain_strictly_typed_and_finite(field, value):
    _, candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)
    rebase(files, lambda ledger: ledger["records"][0]["provenance"].update({field: value}))
    with pytest.raises(ValueError):
        decode(files, candidate, metadata, receipt)


def test_actual_save_load_uses_the_exact_restored_chart_fingerprint_and_markers():
    _, candidate, metadata, receipt = subject()
    metadata = replace(
        metadata,
        power_rating=200.0,
        defense_chart_markers=("XWC", "W"),
        power_rating_is_placeholder=True,
    )
    files = encode_private_bundle(candidate, metadata, receipt)
    chart, transport_meta = decode(files, candidate, metadata, receipt)
    assert transport_meta.defense_chart_markers == ("XWC", "W")
    assert transport_meta.power_rating_is_placeholder
    game = SavedGame.new(
        chart,
        chart,
        home_id="2007/fictional-home",
        away_id="2007/fictional-away",
        seed=2,
        coach_seed=3,
        home_privileges=transport_meta.defense_chart_markers,
        away_privileges=transport_meta.defense_chart_markers,
    )
    game.snap("6", "D")
    restored = loads_game(dumps_game(game), lambda key: decode(files, candidate, metadata, receipt))
    assert restored.view() == game.view()

    # Re-saving changes only the save timestamp and its covering integrity hash.
    # The actual retained engine journal/config/chart fingerprints/future RNG match.
    def retained_facts(value):
        record = json.loads(dumps_game(value))
        del record["saved_at"], record["integrity"]
        return record

    assert retained_facts(restored) == retained_facts(game)


@pytest.mark.parametrize("field", ["rating", "marker-order", "label", "placeholder"])
def test_each_gameplay_metadata_component_has_independent_required_identity(field):
    _, candidate, metadata, receipt = subject()
    metadata = replace(metadata, power_rating=200.0, defense_chart_markers=("W", "XWC"))
    changes = {
        "rating": {"power_rating": 201.0},
        "marker-order": {"defense_chart_markers": ("XWC", "W")},
        "label": {"defense_label": "Different fictional label"},
        "placeholder": {"power_rating_is_placeholder": True},
    }
    different = replace(metadata, **changes[field])
    assert gameplay_metadata_sha256(different) != gameplay_metadata_sha256(metadata)
    files = encode_private_bundle(candidate, metadata, receipt)
    with pytest.raises(ValueError, match="metadata"):
        decode(
            files,
            candidate,
            metadata,
            receipt,
            expected_gameplay_metadata_sha256=gameplay_metadata_sha256(different),
        )
