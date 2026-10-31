"""Synthetic coordinate tests for the documented letter-page vector profile."""

from io import BytesIO

import pdfplumber
import pytest
from reportlab.pdfgen import canvas

from tools.pdf_import.layout import LayoutError, locate_cells


def page_bytes(
    role: str, missing: bool = False, variant: bool = False, mays_profile: str | None = None
) -> bytes:
    stream = BytesIO()
    size = (612, 792) if role == "offense" else (792, 612)
    pdf = canvas.Canvas(stream, pagesize=size)
    offense_edges = (
        66.24,
        86.76,
        126.96,
        165.60,
        208.20,
        250.80,
        293.40,
        336.00,
        378.60,
        421.20,
        463.80,
        482.76,
        508.80,
        534.84,
        556.08,
        575.76,
    )
    if variant:
        offense_edges = (
            66.24,
            86.76,
            126.96,
            165.60,
            208.20,
            246.00,
            288.60,
            331.20,
            373.80,
            416.40,
            459.00,
            477.96,
            504.00,
            530.04,
            556.08,
            575.76,
        )
    if mays_profile == "2007":
        offense_edges = (
            66.24,
            86.76,
            126.96,
            165.60,
            208.20,
            250.80,
            293.40,
            336.00,
            378.60,
            421.20,
            463.80,
            474.84,
            500.88,
            526.92,
            548.16,
            567.84,
        )
    elif mays_profile == "2008":
        offense_edges = (
            63.84,
            84.36,
            124.56,
            163.20,
            205.80,
            248.40,
            291.00,
            333.60,
            376.20,
            418.80,
            461.40,
            477.12,
            503.16,
            529.20,
            550.44,
            570.12,
        )
    defense_edges = (
        66.36,
        112.92,
        133.44,
        172.92,
        212.40,
        251.88,
        291.36,
        330.84,
        370.32,
        409.80,
        449.28,
        488.76,
        513.24,
        552.72,
        592.20,
        631.68,
        671.16,
        710.64,
        750.12,
        769.80,
    )
    wide_offense = role == "offense" and mays_profile in {"2005", "2006"}
    if role == "offense":
        top, bottom, pitch = (112.8, 721.2, 20.28) if wide_offense else (112.8, 634.8, 17.4)
    else:
        top, bottom, pitch = 112.56, 548.16, 14.52
    for edge in offense_edges if role == "offense" else defense_edges:
        pdf.rect(edge - 0.48, size[1] - bottom, 0.96, bottom - top, fill=1, stroke=0)
    pdf.setFont("Helvetica", 8)
    for index in range(30):
        if missing and index == 5:
            continue
        y = 122.23 + index * pitch if role == "offense" else 120.46 + index * pitch
        x = 70 if role == "offense" else 754
        pdf.drawString(x, size[1] - y - 2, str(10 + index))
        if role != "offense":
            pdf.drawString(118, size[1] - y - 2, str(index % 5 + 1))
    pdf.showPage()
    pdf.save()
    return stream.getvalue()


def test_offense_and_supplemental_coordinate_mapping() -> None:
    with pdfplumber.open(BytesIO(page_bytes("offense"))) as pdf:
        cells = locate_cells(pdf.pages[0], "offense")
    assert len(cells) == 360
    assert {(cell.section, cell.column) for cell in cells} == {
        *(("offense", str(i)) for i in range(1, 10)),
        ("supplemental", "QT"),
        ("supplemental", "QR"),
        ("supplemental", "B"),
    }
    assert {cell.roll for cell in cells} == set(range(10, 40))
    first = cells[0]
    assert first.column == "1" and first.roll == 10
    assert first.bounds.x0 == pytest.approx(86.76)
    assert first.bounds.x1 == pytest.approx(126.96)


@pytest.mark.parametrize(
    ("profile", "supplemental_edges"),
    [
        ("2007", (474.84, 500.88, 526.92, 548.16)),
        ("2008", (477.12, 503.16, 529.20, 550.44)),
    ],
)
def test_verified_mays_offense_profiles_preserve_all_cell_columns(
    profile: str, supplemental_edges: tuple[float, ...]
) -> None:
    with pdfplumber.open(BytesIO(page_bytes("offense", mays_profile=profile))) as pdf:
        cells = locate_cells(pdf.pages[0], "offense")

    assert len(cells) == 360
    supplemental = [cell for cell in cells if cell.section == "supplemental" and cell.roll == 10]
    assert [(cell.column, cell.bounds.x0, cell.bounds.x1) for cell in supplemental] == [
        ("QT", pytest.approx(supplemental_edges[0]), pytest.approx(supplemental_edges[1])),
        ("QR", pytest.approx(supplemental_edges[1]), pytest.approx(supplemental_edges[2])),
        ("B", pytest.approx(supplemental_edges[2]), pytest.approx(supplemental_edges[3])),
    ]


@pytest.mark.parametrize("profile", ["2005", "2006"])
def test_verified_tall_mays_offense_profiles_preserve_all_rows(profile: str) -> None:
    with pdfplumber.open(BytesIO(page_bytes("offense", mays_profile=profile))) as pdf:
        cells = locate_cells(pdf.pages[0], "offense")

    assert len(cells) == 360
    first = next(cell for cell in cells if cell.section == "offense" and cell.column == "1")
    last = next(
        cell
        for cell in cells
        if cell.section == "supplemental" and cell.column == "B" and cell.roll == 39
    )
    assert first.bounds.top == pytest.approx(112.8)
    assert first.bounds.bottom == pytest.approx(133.08)
    assert first.roll == 10
    assert last.bounds.top == pytest.approx(700.92)
    assert last.bounds.bottom == pytest.approx(721.2)


def test_defense_special_and_pat_coordinate_mapping() -> None:
    with pdfplumber.open(BytesIO(page_bytes("defense_special"))) as pdf:
        cells = locate_cells(pdf.pages[0], "defense_special")
    assert len(cells) == 480
    defense = [cell for cell in cells if cell.section == "defense"]
    assert len(defense) == 270
    assert {cell.defense for cell in defense} == set("ABCDEF")
    assert {cell.roll for cell in defense} == set(range(1, 6))
    assert len([cell for cell in cells if cell.section == "special_teams"]) == 180
    assert len([cell for cell in cells if cell.section == "pat"]) == 30


@pytest.mark.parametrize("role", ["offense", "defense_special"])
def test_missing_roll_anchor_is_not_invented(role: str) -> None:
    with pdfplumber.open(BytesIO(page_bytes(role, missing=True))) as pdf:
        with pytest.raises(LayoutError, match="roll"):
            locate_cells(pdf.pages[0], role)


def test_unknown_role_fails() -> None:
    with pdfplumber.open(BytesIO(page_bytes("offense"))) as pdf:
        with pytest.raises(LayoutError):
            locate_cells(pdf.pages[0], "unknown")


@pytest.mark.parametrize("role", ["offense", "defense_special"])
def test_every_chart_coordinate_occurs_exactly_once(role: str) -> None:
    with pdfplumber.open(BytesIO(page_bytes(role))) as pdf:
        cells = locate_cells(pdf.pages[0], role)
    keys = [(cell.section, cell.column, cell.roll, cell.defense) for cell in cells]
    assert len(keys) == len(set(keys))
    if role == "offense":
        expected = {
            ("offense", str(column), roll, None)
            for column in range(1, 10)
            for roll in range(10, 40)
        }
        expected |= {
            ("supplemental", column, roll, None)
            for column in ("QT", "QR", "B")
            for roll in range(10, 40)
        }
    else:
        expected = {
            ("defense", str(column), roll, defense)
            for column in range(1, 10)
            for roll in range(1, 6)
            for defense in "ABCDEF"
        }
        expected |= {
            ("special_teams", column, roll, None)
            for column in (
                "kickoff",
                "kickoff_return",
                "punt",
                "punt_return",
                "interception_return",
                "field_goal",
            )
            for roll in range(10, 40)
        }
        expected |= {("pat", "pat", roll, None) for roll in range(10, 40)}
    assert set(keys) == expected


def test_incorrect_page_size_is_rejected() -> None:
    from types import SimpleNamespace

    with pytest.raises(LayoutError, match="letter"):
        locate_cells(SimpleNamespace(width=595, height=842), "offense")


def test_displaced_printed_rolls_are_rejected() -> None:
    from types import SimpleNamespace

    words = [
        {
            "text": str(roll),
            "x0": 70,
            "top": 120 + (roll - 10) * 17.4 + 4,
            "bottom": 128 + (roll - 10) * 17.4 + 4,
        }
        for roll in range(10, 40)
    ]
    page = SimpleNamespace(width=612, height=792, extract_words=lambda: words)
    with pytest.raises(LayoutError, match="row grid"):
        locate_cells(page, "offense")


def test_variable_column_widths_are_read_from_vector_grid_not_school_identity() -> None:
    with pdfplumber.open(BytesIO(page_bytes("offense", variant=True))) as pdf:
        cells = locate_cells(pdf.pages[0], "offense")
    play_four = next(cell for cell in cells if cell.section == "offense" and cell.column == "4")
    qt = next(cell for cell in cells if cell.section == "supplemental" and cell.column == "QT")
    assert play_four.bounds.x1 == pytest.approx(246)
    assert qt.bounds.x0 == pytest.approx(477.96)
    assert qt.bounds.x1 == pytest.approx(504)


def test_missing_vector_column_boundaries_are_not_assumed() -> None:
    from types import SimpleNamespace

    with pdfplumber.open(BytesIO(page_bytes("offense"))) as pdf:
        original = pdf.pages[0]
        page = SimpleNamespace(
            width=original.width,
            height=original.height,
            extract_words=original.extract_words,
            rects=[],
        )
        with pytest.raises(LayoutError, match="column"):
            locate_cells(page, "offense")


def test_foreign_line_cannot_replace_a_missing_grid_boundary() -> None:
    from types import SimpleNamespace

    with pdfplumber.open(BytesIO(page_bytes("offense"))) as pdf:
        original = pdf.pages[0]
        rectangles = [
            rect for rect in original.rects if abs(rect["x0"] + rect["width"] / 2 - 126.96) > 0.5
        ]
        rectangles.append(dict(x0=20, width=1, height=100, top=650, bottom=750))
        page = SimpleNamespace(
            width=612, height=792, rects=rectangles, extract_words=original.extract_words
        )
        with pytest.raises(LayoutError, match="column"):
            locate_cells(page, "offense")


def test_split_nearly_coincident_vector_segments_are_one_boundary() -> None:
    from types import SimpleNamespace

    with pdfplumber.open(BytesIO(page_bytes("offense"))) as pdf:
        original = pdf.pages[0]
        rectangles = list(original.rects)
        rect = rectangles[0]
        rectangles.append(dict(rect, x0=rect["x0"] + 0.02))
        page = SimpleNamespace(
            width=612, height=792, rects=rectangles, extract_words=original.extract_words
        )
        assert len(locate_cells(page, "offense")) == 360


def test_wide_shift_of_an_internal_grid_boundary_is_rejected() -> None:
    from types import SimpleNamespace

    with pdfplumber.open(BytesIO(page_bytes("offense"))) as pdf:
        original = pdf.pages[0]
        rectangles = [
            dict(rect, x0=rect["x0"] + 20)
            if abs(rect["x0"] + rect["width"] / 2 - 126.96) < 0.5
            else rect
            for rect in original.rects
        ]
        page = SimpleNamespace(
            width=612, height=792, rects=rectangles, extract_words=original.extract_words
        )
        with pytest.raises(LayoutError, match="column"):
            locate_cells(page, "offense")
