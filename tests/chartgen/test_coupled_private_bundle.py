"""The new compiled model uses the same strict private ancestry transport."""

from copy import deepcopy
from functools import lru_cache

import pytest

from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.team_csv import TeamFileMetadata
from tests.chartgen.test_private_bundle import decode, hashes, rebase
from tests.chartgen.test_typed_event_model import legacy_factory
from tools.chartgen.coupled_event_risks import apply_coupled_model, model_identity
from tools.chartgen.private_bundle import _model, encode_private_bundle, gameplay_metadata_sha256


@lru_cache(maxsize=1)
def subject():
    old = legacy_factory()
    metadata = TeamFileMetadata(
        5.5, (), "Fictional", old.offense[0].cell.provenance.source_sha256, ()
    )
    candidate, receipt = apply_coupled_model(
        old,
        known_depths=((-3, 1), (5, 1), (19, 1), (35, 1)),
        unknown_locations=2,
        source_identity="a" * 64,
    )
    assert receipt["status"] == "represented"
    return candidate, metadata, receipt


def test_reviewed_compiled_coupled_model_roundtrip_and_actual_save() -> None:
    candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)
    loaded, transport = decode(files, candidate, metadata, receipt)
    assert loaded == candidate
    assert gameplay_metadata_sha256(transport) == gameplay_metadata_sha256(metadata)
    game = SavedGame.new(
        loaded,
        loaded,
        home_id="2007/fictional-home",
        away_id="2007/fictional-away",
        seed=2,
        coach_seed=3,
    )
    game.snap("6", "D")
    restored = loads_game(dumps_game(game), lambda key: decode(files, candidate, metadata, receipt))
    assert restored.view() == game.view()


@pytest.mark.parametrize("field", ["origin", "contract", "sha256"])
def test_coupled_registry_is_full_compiled_identity_not_origin_or_self_hash(field: str) -> None:
    candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)

    def mutation(ledger):
        value = ledger["model_identity"]
        value[field] = "unreviewed" if field != "contract" else {"different": True}
        ledger["producer_receipt"]["model_identity"] = value

    rebase(files, mutation)
    with pytest.raises(ValueError, match="model"):
        decode(files, candidate, metadata, receipt)


def test_v3_repinned_football_mutation_still_fails_complete_semantic_check() -> None:
    candidate, metadata, receipt = subject()
    files = encode_private_bundle(candidate, metadata, receipt)
    # A valid CSV change and matching transported source text cannot replace
    # the independently pinned complete object, even with updated file hashes.
    original = files["defense.csv"]
    assert "INT -3" in original
    files["defense.csv"] = original.replace("INT -3", "INT -2", 1)
    with pytest.raises(ValueError):
        decode(files, candidate, metadata, receipt, expected_file_hashes=hashes(files))


def test_model_numeric_weight_cannot_masquerade_as_boolean() -> None:
    compiled = model_identity()
    mutated = deepcopy(compiled)
    mutated["contract"]["weights"][-1] = True
    with pytest.raises(ValueError, match="model"):
        _model(mutated, compiled["sha256"])
