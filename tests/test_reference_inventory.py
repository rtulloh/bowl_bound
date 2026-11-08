"""Synthetic reference inventory checks; no private charts are test inputs."""

from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from bowl_bound.team_csv import provenance_to_csv, team_to_files
from tests.test_team_csv import chart, metadata
from tools.reference_inventory import ReferenceInput, inventory_reference, physical_weights


def reference(tmp_path: Path) -> ReferenceInput:
    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(b"%PDF-1.4\nsynthetic evidence for inventory, not a parsed PDF\n")
    digest = sha256(pdf.read_bytes()).hexdigest()
    original = chart("Cedar Valley")
    changes = {}
    for section in ("offense", "supplemental", "defense", "special_teams"):
        changes[section] = tuple(
            replace(
                row,
                cell=replace(
                    row.cell, provenance=replace(row.cell.provenance, source_sha256=digest)
                ),
            )
            for row in getattr(original, section)
        )
    changes["pat_outcomes"] = tuple(
        replace(row, provenance=replace(row.provenance, source_sha256=digest))
        for row in original.pat_outcomes
    )
    team = replace(original, **changes)
    meta = replace(
        metadata(),
        source_sha256=digest,
        evidence=tuple(
            (key, replace(value, source_sha256=digest)) for key, value in metadata().evidence
        ),
    )
    folder = tmp_path / "2026" / "cedar-valley"
    folder.mkdir(parents=True)
    files = team_to_files(team, meta)
    paths = {}
    for name, value in files.items():
        path = folder / name
        path.write_text(value)
        paths[name] = path
    provenance = folder.parent / "provenance" / "cedar-valley.csv"
    provenance.parent.mkdir()
    provenance.write_text(provenance_to_csv(team, meta))
    paths["provenance.csv"] = provenance
    paths["source.pdf"] = pdf
    return ReferenceInput(
        folder.parent,
        folder.name,
        pdf,
        tuple((name, sha256(path.read_bytes()).hexdigest()) for name, path in paths.items()),
    )


def test_inventory_binds_all_840_cells_and_metadata_without_claiming_pdf_reimport(
    tmp_path: Path,
) -> None:
    result = inventory_reference(reference(tmp_path))
    assert result["counts"] == {
        "offense": 270,
        "supplemental": 90,
        "defense": 270,
        "special_teams": 180,
        "pat_outcomes": 30,
    }
    assert result["provenance_records"] == 841
    assert result["season"] == 2026
    assert result["name"] == "Cedar Valley"
    assert len(result["input_sha256"]) == 6
    assert result["pdf_binding_verified"] is True
    assert result["pdf_text_geometry_reimported"] is False
    assert result["power_rating_is_placeholder"] is False


@pytest.mark.parametrize(
    "name",
    ["offense.csv", "defense.csv", "special.csv", "team.yaml", "provenance.csv", "source.pdf"],
)
def test_any_changed_frozen_input_is_rejected(tmp_path: Path, name: str) -> None:
    source = reference(tmp_path)
    pins = tuple(
        (key, "0" * 64 if key == name else digest) for key, digest in source.expected_sha256
    )
    with pytest.raises(ValueError, match="frozen input hash"):
        inventory_reference(replace(source, expected_sha256=pins))


def test_missing_expected_input_cannot_be_silently_rebaselined(tmp_path: Path) -> None:
    source = reference(tmp_path)
    with pytest.raises(ValueError, match="exact six"):
        inventory_reference(replace(source, expected_sha256=source.expected_sha256[:-1]))


def test_duplicate_expected_input_cannot_hide_a_missing_binding(tmp_path: Path) -> None:
    source = reference(tmp_path)
    with pytest.raises(ValueError, match="exact six"):
        inventory_reference(
            replace(source, expected_sha256=source.expected_sha256 + source.expected_sha256[:1])
        )


def test_pdf_bytes_must_be_the_source_named_by_normalized_provenance(tmp_path: Path) -> None:
    source = reference(tmp_path)
    source.source_pdf.write_bytes(b"%PDF-1.4\nanother synthetic source\n")
    pins = tuple(
        (key, sha256(source.source_pdf.read_bytes()).hexdigest() if key == "source.pdf" else digest)
        for key, digest in source.expected_sha256
    )
    with pytest.raises(ValueError, match="PDF provenance hash"):
        inventory_reference(replace(source, expected_sha256=pins))


def test_source_mutation_during_normalization_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tools.reference_inventory as module

    source = reference(tmp_path)
    original = module.team_from_files

    def mutate(files: Mapping[str, str], provenance_csv: str) -> object:
        result = original(files, provenance_csv)
        (source.season_dir / source.slug / "offense.csv").write_text("changed")
        return result

    monkeypatch.setattr(module, "team_from_files", mutate)
    with pytest.raises(ValueError, match="changed during inventory"):
        inventory_reference(source)


def test_wrong_season_directory_is_not_an_accepted_match(tmp_path: Path) -> None:
    source = reference(tmp_path)
    destination = source.season_dir.with_name("2025")
    source.season_dir.rename(destination)
    with pytest.raises(ValueError, match="season or folder mismatch"):
        inventory_reference(replace(source, season_dir=destination))


def test_reference_symlink_is_not_a_separate_source(tmp_path: Path) -> None:
    source = reference(tmp_path)
    alias = tmp_path / "alias.pdf"
    alias.symlink_to(source.source_pdf)
    with pytest.raises(ValueError, match="symlink"):
        inventory_reference(replace(source, source_pdf=alias))


def test_exact_physical_weights_preserve_multiplicities_not_uniform_roll_totals() -> None:
    offense, defense = physical_weights()
    assert sum(offense.values()) == 216
    assert sum(defense.values()) == 36
    assert defense == {1: 12, 2: 11, 3: 9, 4: 3, 5: 1}
    assert offense[10] == 2
    assert offense[39] == 3
    assert len(offense) == 30
