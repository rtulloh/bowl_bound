"""Synthetic supported-layout tests for PDF chart inspection."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.pdfgen import canvas

from tools.pdf_import.inspection import (
    ImportInspectionError,
    PageInfo,
    UnsupportedDocumentError,
    inspect_document,
)


def _draw_rotated_header(pdf: canvas.Canvas, name: str, season: int, role: str) -> None:
    pdf.saveState()
    pdf.translate(20, 70)
    pdf.rotate(90)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(0, 0, f"{season} {name} {role}")
    pdf.restoreState()


def _draw_grid(pdf: canvas.Canvas) -> None:
    for x in range(36, int(pdf._pagesize[0] - 36), 72):
        for y in range(120, 400, 40):
            pdf.rect(x, y, 60, 36)


def _draw_offense(
    pdf: canvas.Canvas, name: str, season: int, *, labels: bool = True, grid: bool = True
) -> None:
    pdf.setPageSize(letter)
    _draw_rotated_header(pdf, name, season, "offense")
    if grid:
        _draw_grid(pdf)
    if labels:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(45, 650, "Line Plunge   Option   QT   QR   B")
    pdf.showPage()


def _draw_defense(pdf: canvas.Canvas, name: str, season: int) -> None:
    pdf.setPageSize(landscape(letter))
    _draw_rotated_header(pdf, name, season, "defense")
    _draw_grid(pdf)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, 470, "Defense   Kickoff   Punt   Field Goal")
    pdf.showPage()


def _draw_rotated_defense_portrait(pdf: canvas.Canvas) -> None:
    """Draw a landscape defense chart rotated onto a portrait sheet."""
    pdf.setPageSize(letter)
    pdf.saveState()
    pdf.translate(612, 0)
    pdf.rotate(90)
    _draw_grid(pdf)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, 470, "Defense   Kickoff   Punt   Field Goal")
    pdf.restoreState()
    pdf.showPage()


def _write_document(path: Path, pairs: list[tuple[str, str, int]]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    for school, mascot, season in pairs:
        _draw_offense(pdf, school, season)
        _draw_defense(pdf, mascot, season)
    pdf.save()


def test_inspect_document_returns_rotated_paired_page_metadata(tmp_path: Path) -> None:
    path = tmp_path / "charts.pdf"
    _write_document(path, [("Synthetic State", "Synths", 2002), ("Example U", "Examples", 2003)])

    inspection = inspect_document(path)

    assert len(inspection.source_sha256) == 64
    assert inspection.pages == (
        PageInfo(1, "offense", "Synthetic State", 2002),
        PageInfo(2, "defense_special", "Synths", 2002),
        PageInfo(3, "offense", "Example U", 2003),
        PageInfo(4, "defense_special", "Examples", 2003),
    )


def test_inspect_document_accepts_rotated_defense_on_portrait_sheet(tmp_path: Path) -> None:
    path = tmp_path / "portrait-defense.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _draw_offense(pdf, "Synthetic State", 2002)
    _draw_rotated_defense_portrait(pdf)
    pdf.save()

    inspection = inspect_document(path)

    assert inspection.pages[1] == PageInfo(2, "defense_special", "Synthetic State", 2002, 90)


def test_inspect_document_rejects_odd_page_count(tmp_path: Path) -> None:
    path = tmp_path / "odd.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _draw_offense(pdf, "Synthetic State", 2002)
    pdf.save()

    with pytest.raises(UnsupportedDocumentError, match="pairs"):
        inspect_document(path)


def test_inspect_document_allows_different_school_and_mascot_names(tmp_path: Path) -> None:
    path = tmp_path / "names.pdf"
    _write_document(path, [("Synthetic State", "Synths", 2002)])

    assert inspect_document(path).pages[1].team_name == "Synths"


def test_inspect_document_rejects_pair_with_mismatched_season(tmp_path: Path) -> None:
    path = tmp_path / "mismatched.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _draw_offense(pdf, "Synthetic State", 2002)
    _draw_defense(pdf, "Synths", 2003)
    pdf.save()

    with pytest.raises(UnsupportedDocumentError, match="same season"):
        inspect_document(path)


def test_inspect_document_rejects_duplicate_offense_identity(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.pdf"
    _write_document(path, [("Synthetic State", "Synths", 2002)] * 2)

    with pytest.raises(UnsupportedDocumentError, match="Duplicate offense"):
        inspect_document(path)


def test_inspect_document_rejects_scanned_or_missing_label_page(tmp_path: Path) -> None:
    path = tmp_path / "scanned.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _draw_offense(pdf, "Synthetic State", 2002, labels=False)
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()

    with pytest.raises(UnsupportedDocumentError, match="required labels"):
        inspect_document(path)


def test_inspect_document_rejects_page_without_vector_rectangles(tmp_path: Path) -> None:
    path = tmp_path / "no-grid.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _draw_offense(pdf, "Synthetic State", 2002, grid=False)
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()

    with pytest.raises(UnsupportedDocumentError, match="vector chart rectangles"):
        inspect_document(path)


def test_inspect_document_reports_malformed_and_encrypted_sources(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.pdf"
    malformed.write_bytes(b"not a PDF")
    encrypted = tmp_path / "encrypted.pdf"
    pdf = canvas.Canvas(str(encrypted), encrypt=StandardEncryption("secret"))
    _draw_offense(pdf, "Synthetic State", 2002)
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()

    with pytest.raises(ImportInspectionError, match="malformed"):
        inspect_document(malformed)
    with pytest.raises(ImportInspectionError, match="encrypted"):
        inspect_document(encrypted)


def test_inspect_document_reports_missing_file_as_import_error(tmp_path: Path) -> None:
    with pytest.raises(ImportInspectionError, match="does not exist"):
        inspect_document(tmp_path / "missing.pdf")


# --- Review corrections: identity, roles, labels, geometry, hashing ---


def test_same_mascot_for_different_schools_is_accepted_and_kept_separate(tmp_path: Path) -> None:
    """LSU, Clemson, and Missouri are all Tigers; the mascot is never an identifier."""
    path = tmp_path / "tigers.pdf"
    _write_document(
        path,
        [
            ("Synthetic State", "Tigers", 2002),
            ("Example U", "Tigers", 2002),
            ("Sample College", "Tigers", 2002),
        ],
    )
    pages = inspect_document(path).pages
    offense_names = [p.team_name for p in pages if p.role == "offense"]
    assert offense_names == ["Synthetic State", "Example U", "Sample College"]
    assert [p.team_name for p in pages if p.role == "defense_special"] == ["Tigers"] * 3


def test_duplicate_school_detection_ignores_case_and_spacing(tmp_path: Path) -> None:
    path = tmp_path / "dup.pdf"
    _write_document(
        path, [("Synthetic State", "Synths", 2002), ("SYNTHETIC  STATE", "Synths", 2002)]
    )
    with pytest.raises(UnsupportedDocumentError, match="Duplicate offense"):
        inspect_document(path)


def test_role_word_in_header_must_match_page_position(tmp_path: Path) -> None:
    path = tmp_path / "wrong-role.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setPageSize(letter)
    _draw_rotated_header(pdf, "Synthetic State", 2002, "defense")  # offense page, defense header
    _draw_grid(pdf)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, 650, "Line Plunge   Option   QT   QR   B")
    pdf.showPage()
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()
    with pytest.raises(UnsupportedDocumentError, match="header"):
        inspect_document(path)


def test_defense_label_cannot_be_satisfied_by_the_header_alone(tmp_path: Path) -> None:
    path = tmp_path / "header-only.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _draw_offense(pdf, "Synthetic State", 2002)
    pdf.setPageSize(landscape(letter))
    _draw_rotated_header(pdf, "Synths", 2002, "defense")
    _draw_grid(pdf)
    pdf.showPage()  # the page body has no Kickoff/Punt/Field Goal labels
    pdf.save()
    with pytest.raises(UnsupportedDocumentError, match="required labels"):
        inspect_document(path)


def test_labels_must_be_adjacent_phrases_not_scattered_words(tmp_path: Path) -> None:
    path = tmp_path / "scattered.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setPageSize(letter)
    _draw_rotated_header(pdf, "Synthetic State", 2002, "offense")
    _draw_grid(pdf)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, 650, "Line   Option   QT   QR   B")
    pdf.drawString(45, 600, "Plunge")
    pdf.showPage()
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()
    with pytest.raises(UnsupportedDocumentError, match="required labels"):
        inspect_document(path)


def test_single_rectangle_is_not_a_chart(tmp_path: Path) -> None:
    path = tmp_path / "one-rect.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setPageSize(letter)
    _draw_rotated_header(pdf, "Synthetic State", 2002, "offense")
    pdf.rect(36, 120, 60, 280)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, 650, "Line Plunge   Option   QT   QR   B")
    pdf.showPage()
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()
    with pytest.raises(UnsupportedDocumentError, match="vector chart rectangles"):
        inspect_document(path)


def test_wrong_page_geometry_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "geometry.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setPageSize(landscape(letter))  # offense must be portrait
    _draw_rotated_header(pdf, "Synthetic State", 2002, "offense")
    _draw_grid(pdf)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, 470, "Line Plunge   Option   QT   QR   B")
    pdf.showPage()
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()
    with pytest.raises(UnsupportedDocumentError, match="geometry"):
        inspect_document(path)


def test_zero_page_and_non_pdf_inputs_are_import_errors(tmp_path: Path) -> None:
    text = tmp_path / "text.pdf"
    text.write_text("plain text, not a PDF")
    with pytest.raises(ImportInspectionError):
        inspect_document(text)


def test_missing_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "no-header.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    pdf.setPageSize(letter)
    _draw_grid(pdf)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, 650, "Line Plunge   Option   QT   QR   B")
    pdf.showPage()
    _draw_defense(pdf, "Synths", 2002)
    pdf.save()
    with pytest.raises(UnsupportedDocumentError, match="header"):
        inspect_document(path)


def test_digest_is_the_sha256_of_the_exact_bytes_parsed(tmp_path: Path) -> None:
    import hashlib

    path = tmp_path / "charts.pdf"
    _write_document(path, [("Synthetic State", "Synths", 2002)])
    assert inspect_document(path).source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_unexpected_parser_failure_is_wrapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.pdf_import import inspection

    path = tmp_path / "charts.pdf"
    _write_document(path, [("Synthetic State", "Synths", 2002)])

    def explode(*args: object, **kwargs: object) -> None:
        raise KeyError("PRIVATE")

    monkeypatch.setattr(inspection, "_inspect_page", explode)
    with pytest.raises(ImportInspectionError) as error:
        inspect_document(path)
    assert "PRIVATE" not in str(error.value)
