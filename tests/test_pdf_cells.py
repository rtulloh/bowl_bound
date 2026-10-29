"""Synthetic PDF tests for raw chart-cell extraction."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import pdfplumber
import pytest
from reportlab.pdfgen import canvas

from tools.pdf_import.cells import CellBounds, CellExtractionError, extract_cells

SHA = "a" * 64


def _page(draw: object):
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(200, 200))
    draw(pdf)
    pdf.showPage()
    pdf.save()
    return pdfplumber.open(BytesIO(stream.getvalue())).pages[0]


def _extract(page: object, *bounds: CellBounds):
    return extract_cells(page, bounds, source_sha256=SHA, filename="synthetic.pdf", page_number=1)


def test_extracts_exact_text_color_and_pdf_coordinate_provenance() -> None:
    def draw(pdf: canvas.Canvas) -> None:
        pdf.setFillColorRGB(1, 0, 0)
        pdf.rect(20, 140, 80, 30, fill=1, stroke=0)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(25, 150, " X ")

    cell = _extract(_page(draw), CellBounds(20, 30, 100, 60))[0]
    assert cell.text == " X "
    assert cell.rgb_color == (255, 0, 0)
    assert cell.rotation == 0
    assert cell.provenance.bounding_box.left == 20
    assert cell.provenance.bounding_box.bottom == 140
    assert cell.provenance.bounding_box.top == 170


def test_extracts_rotated_text_and_merged_background() -> None:
    def draw(pdf: canvas.Canvas) -> None:
        pdf.setFillColorRGB(0, 1, 0)
        pdf.rect(20, 140, 160, 30, fill=1, stroke=0)
        pdf.saveState()
        pdf.translate(30, 145)
        pdf.rotate(90)
        pdf.drawString(0, 0, "R")
        pdf.restoreState()

    cells = _extract(_page(draw), CellBounds(20, 30, 100, 60), CellBounds(100, 30, 180, 60))
    assert cells[0].text == "R"
    assert cells[0].rotation == 90
    assert [cell.rgb_color for cell in cells] == [(0, 255, 0), (0, 255, 0)]


def test_blank_white_requires_explicit_fill_or_enclosing_grid() -> None:
    explicit = _page(lambda pdf: (pdf.setFillColorRGB(1, 1, 1), pdf.rect(20, 140, 80, 30, fill=1)))
    assert _extract(explicit, CellBounds(20, 30, 100, 60))[0].text == ""

    grid = _page(lambda pdf: pdf.rect(20, 140, 80, 30, fill=0, stroke=1))
    assert _extract(grid, CellBounds(20, 30, 100, 60))[0].rgb_color == (255, 255, 255)

    with pytest.raises(CellExtractionError, match="background"):
        _extract(_page(lambda pdf: None), CellBounds(20, 30, 100, 60))


def test_blank_black_and_border_are_not_confused() -> None:
    black = _page(lambda pdf: (pdf.setFillColorRGB(0, 0, 0), pdf.rect(20, 140, 80, 30, fill=1)))
    assert _extract(black, CellBounds(20, 30, 100, 60))[0].rgb_color == (0, 0, 0)

    border = _page(lambda pdf: pdf.rect(20, 140, 80, 30, fill=0, stroke=1))
    assert _extract(border, CellBounds(20, 30, 100, 60))[0].rgb_color == (255, 255, 255)


def test_rejects_cross_cell_characters_and_grid_lines() -> None:
    def draw_crossing(pdf: canvas.Canvas) -> None:
        pdf.setFillColorRGB(1, 1, 1)
        pdf.rect(20, 140, 160, 30, fill=1)
        pdf.drawString(95, 150, "W")

    crossing = _page(draw_crossing)
    with pytest.raises(CellExtractionError, match="crosses"):
        _extract(crossing, CellBounds(20, 30, 100, 60), CellBounds(100, 30, 180, 60))

    def draw_line(pdf: canvas.Canvas) -> None:
        pdf.setFillColorRGB(1, 1, 1)
        pdf.rect(20, 140, 80, 30, fill=1)
        pdf.line(60, 140, 60, 170)

    with pytest.raises(CellExtractionError, match="line"):
        _extract(_page(draw_line), CellBounds(20, 30, 100, 60))


@dataclass
class FakePage:
    width: float = 200
    height: float = 200
    chars: list[dict] | None = None
    rects: list[dict] | None = None
    lines: list[dict] | None = None
    objects: dict | None = None

    def __post_init__(self) -> None:
        self.chars = self.chars or []
        self.rects = self.rects or []
        self.lines = self.lines or []


def test_rejects_ambiguous_or_unsupported_paint_and_rotation() -> None:
    bound = CellBounds(20, 30, 100, 60)
    full = {"x0": 20, "top": 30, "x1": 100, "bottom": 60, "fill": True}
    red = full | {"non_stroking_color": (1, 0, 0)}
    green = full | {"non_stroking_color": (0, 1, 0)}
    with pytest.raises(CellExtractionError, match="paint"):
        _extract(FakePage(rects=[red, green]), bound)

    left = red | {"x1": 70}
    right = green | {"x0": 60}
    with pytest.raises(CellExtractionError, match="partial"):
        _extract(FakePage(rects=[left, right]), bound)
    with pytest.raises(CellExtractionError, match="color"):
        _extract(FakePage(rects=[full | {"non_stroking_color": (0, 0, 0, 1)}]), bound)

    character = {
        "text": "x",
        "x0": 30,
        "x1": 35,
        "top": 35,
        "bottom": 45,
        "matrix": (1, 1, 0, 1, 0, 0),
    }
    with pytest.raises(CellExtractionError, match="matrix"):
        _extract(FakePage(chars=[character], rects=[full | {"non_stroking_color": 1}]), bound)

    upright = character | {"matrix": (1, 0, 0, 1, 0, 0)}
    sideways = character | {"x0": 40, "x1": 45, "matrix": (0, 1, -1, 0, 0, 0)}
    with pytest.raises(CellExtractionError, match="mixed"):
        page = FakePage(
            chars=[upright, sideways],
            rects=[full | {"non_stroking_color": 1}],
        )
        _extract(page, bound)


def test_last_ordered_full_paint_wins_and_validates_bounds() -> None:
    bound = CellBounds(20, 30, 100, 60)
    red = {
        "x0": 20,
        "top": 30,
        "x1": 100,
        "bottom": 60,
        "fill": True,
        "non_stroking_color": (1, 0, 0),
    }
    blue = red | {"non_stroking_color": (0, 0, 1)}
    page = FakePage(rects=[red, blue], objects={"rect": [red, blue]})
    assert _extract(page, bound)[0].rgb_color == (0, 0, 255)

    with pytest.raises((TypeError, ValueError)):
        CellBounds(1, 2, 1, 3)
    with pytest.raises(CellExtractionError, match="duplicate"):
        _extract(page, bound, bound)
    assert _extract(page) == ()


def test_background_rejects_partial_overlay_and_accepts_grayscale() -> None:
    bound = CellBounds(20, 30, 100, 60)
    red = {
        "x0": 20,
        "top": 30,
        "x1": 100,
        "bottom": 60,
        "fill": True,
        "non_stroking_color": (1, 0, 0),
    }
    overlay = {
        "x0": 50,
        "top": 35,
        "x1": 70,
        "bottom": 55,
        "fill": True,
        "non_stroking_color": (0, 1, 0),
    }
    with pytest.raises(CellExtractionError, match="partial"):
        _extract(FakePage(rects=[red, overlay]), bound)

    gray = red | {"non_stroking_color": (1,)}
    assert _extract(FakePage(rects=[gray]), bound)[0].rgb_color == (255, 255, 255)


def test_implicit_white_requires_four_cell_borders_not_an_enclosing_rectangle() -> None:
    bound = CellBounds(20, 30, 100, 60)
    enclosing = {"x0": 0, "top": 0, "x1": 200, "bottom": 200, "fill": False}
    with pytest.raises(CellExtractionError, match="background"):
        _extract(FakePage(rects=[enclosing]), bound)

    borders = [
        {"x0": 19, "top": 29, "x1": 101, "bottom": 31, "fill": True, "non_stroking_color": 0},
        {"x0": 19, "top": 59, "x1": 101, "bottom": 61, "fill": True, "non_stroking_color": 0},
        {"x0": 19, "top": 29, "x1": 21, "bottom": 61, "fill": True, "non_stroking_color": 0},
        {"x0": 99, "top": 29, "x1": 101, "bottom": 61, "fill": True, "non_stroking_color": 0},
    ]
    assert _extract(FakePage(rects=borders), bound)[0].rgb_color == (255, 255, 255)
    with pytest.raises(CellExtractionError, match="background"):
        _extract(FakePage(rects=borders[:-1]), bound)


def test_text_gaps_rotations_and_unknown_rotations_are_explicit() -> None:
    bound = CellBounds(20, 30, 100, 60)
    white = {"x0": 20, "top": 30, "x1": 100, "bottom": 60, "fill": True, "non_stroking_color": 1}
    chars = [
        {"text": "1", "x0": 30, "x1": 35, "top": 40, "bottom": 50, "matrix": (1, 0, 0, 1, 0, 0)},
        {"text": "0", "x0": 45, "x1": 50, "top": 40, "bottom": 50, "matrix": (1, 0, 0, 1, 0, 0)},
    ]
    assert _extract(FakePage(chars=chars, rects=[white]), bound)[0].text == "1 0"

    for rotation, matrix in ((180, (-1, 0, 0, -1, 0, 0)), (270, (0, -1, 1, 0, 0, 0))):
        char = chars[0] | {"matrix": matrix}
        assert _extract(FakePage(chars=[char], rects=[white]), bound)[0].rotation == rotation

    unknown = chars[0] | {"upright": False}
    unknown.pop("matrix")
    with pytest.raises(CellExtractionError, match="matrix"):
        _extract(FakePage(chars=[unknown], rects=[white]), bound)


def test_same_color_split_fill_covers_inset_and_nan_matrix_is_rejected() -> None:
    bound = CellBounds(20, 30, 100, 60)
    left = {"x0": 20, "top": 30, "x1": 60, "bottom": 60, "fill": True, "non_stroking_color": 1}
    right = {"x0": 60, "top": 30, "x1": 100, "bottom": 60, "fill": True, "non_stroking_color": 1}
    assert _extract(FakePage(rects=[left, right]), bound)[0].rgb_color == (255, 255, 255)

    char = {
        "text": "x",
        "x0": 30,
        "x1": 35,
        "top": 40,
        "bottom": 50,
        "matrix": (float("nan"), 0, 0, 1, 0, 0),
    }
    with pytest.raises(CellExtractionError, match="matrix"):
        _extract(FakePage(chars=[char], rects=[left, right]), bound)


def test_segmented_grid_boundaries_with_small_join_gaps_prove_implicit_white() -> None:
    bound = CellBounds(20, 30, 100, 60)
    black = {"fill": True, "non_stroking_color": 0}
    segments = [
        black | {"x0": 21.5, "top": 29, "x1": 59, "bottom": 31},
        black | {"x0": 61, "top": 29, "x1": 98.5, "bottom": 31},
        black | {"x0": 21.5, "top": 59, "x1": 59, "bottom": 61},
        black | {"x0": 61, "top": 59, "x1": 98.5, "bottom": 61},
        black | {"x0": 19, "top": 31.5, "x1": 21, "bottom": 44},
        black | {"x0": 19, "top": 46, "x1": 21, "bottom": 58.5},
        black | {"x0": 99, "top": 31.5, "x1": 101, "bottom": 44},
        black | {"x0": 99, "top": 46, "x1": 101, "bottom": 58.5},
        black | {"x0": 105, "top": 29, "x1": 120, "bottom": 31},
        black | {"x0": 105, "top": 59, "x1": 120, "bottom": 61},
    ]
    assert _extract(FakePage(rects=segments), bound)[0].rgb_color == (255, 255, 255)


def test_same_row_glyphs_are_ordered_by_position_despite_small_top_offsets() -> None:
    bound = CellBounds(20, 30, 100, 60)
    white = {"x0": 20, "top": 30, "x1": 100, "bottom": 60, "fill": True, "non_stroking_color": 1}
    chars = [
        {"text": "A", "x0": 45, "x1": 50, "top": 40.0, "bottom": 50, "matrix": (1, 0, 0, 1, 0, 0)},
        {"text": "B", "x0": 30, "x1": 45, "top": 40.06, "bottom": 50, "matrix": (1, 0, 0, 1, 0, 0)},
    ]
    assert _extract(FakePage(chars=chars, rects=[white]), bound)[0].text == "BA"


def test_rejects_malformed_and_unsupported_objects_only_when_they_touch_a_cell() -> None:
    bound = CellBounds(20, 30, 100, 60)
    white = {"x0": 20, "top": 30, "x1": 100, "bottom": 60, "fill": True, "non_stroking_color": 1}
    page = FakePage(rects=[white], lines=[{"x0": float("nan"), "x1": 1, "top": 1, "bottom": 1}])
    with pytest.raises(CellExtractionError, match="geometry"):
        _extract(page, bound)

    for attribute in ("curves", "images"):
        page = FakePage(rects=[white])
        setattr(page, attribute, [{"x0": 30, "top": 40, "x1": 40, "bottom": 50}])
        with pytest.raises(CellExtractionError, match=attribute[:-1]):
            _extract(page, bound)

        setattr(page, attribute, [{"x0": 120, "top": 40, "x1": 130, "bottom": 50}])
        assert _extract(page, bound)[0].rgb_color == (255, 255, 255)


def test_color_space_and_rotated_text_evidence_are_not_guessed() -> None:
    bound = CellBounds(20, 30, 100, 60)
    unit_white = {
        "x0": 20,
        "top": 30,
        "x1": 100,
        "bottom": 60,
        "fill": True,
        "non_stroking_color": 1,
    }
    with pytest.raises(CellExtractionError, match="color"):
        _extract(FakePage(rects=[unit_white | {"non_stroking_color": (255, 0, 0)}]), bound)
    with pytest.raises(CellExtractionError, match="color"):
        _extract(FakePage(rects=[unit_white | {"ncs": "DeviceCMYK"}]), bound)

    matrix = (0, 1, -1, 0, 0, 0)
    chars = [
        {"text": "A", "x0": 30, "x1": 35, "top": 50, "bottom": 60, "matrix": matrix},
        {"text": "B", "x0": 30, "x1": 35, "top": 35, "bottom": 45, "matrix": matrix},
    ]
    assert _extract(FakePage(chars=chars, rects=[unit_white]), bound)[0].text == "A B"


def test_ordered_paint_mismatch_is_an_extraction_error() -> None:
    bound = CellBounds(20, 30, 100, 60)
    red = {
        "x0": 20,
        "top": 30,
        "x1": 100,
        "bottom": 60,
        "fill": True,
        "non_stroking_color": (1, 0, 0),
    }
    blue = red | {"non_stroking_color": (0, 0, 1)}
    with pytest.raises(CellExtractionError, match="paint"):
        _extract(FakePage(rects=[red, blue], objects={"rect": []}), bound)
