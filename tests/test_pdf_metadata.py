"""Synthetic metadata evidence: no historical chart fixtures."""

from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pdfplumber
import pytest
from reportlab.pdfgen import canvas

from tools.pdf_import.cells import _rgb as cell_rgb
from tools.pdf_import.metadata import MetadataError, extract_metadata
from tools.pdf_import.metadata import _color as metadata_color


def pages(
    rating: str = "200.5",
    recovery: str = "Fumble Recovered 10-25; Fumble Lost 26-39",
    marker: str = "W",
    rating_background: tuple[float, float, float] | None = None,
    recovery_x: float = 590,
) -> bytes:
    """Build two synthetic vector pages containing supported metadata."""
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(612, 792))
    if rating_background is not None:
        pdf.setFillColorRGB(*rating_background)
        pdf.rect(505, 710, 70, 25, fill=1, stroke=0)
        pdf.setFillColorRGB(0, 0, 0)
    pdf.drawString(510, 720, rating)
    pdf.saveState()
    pdf.translate(recovery_x, 180)
    pdf.rotate(90)
    pdf.drawString(0, 0, recovery)
    pdf.restoreState()
    pdf.showPage()
    pdf.setPageSize((792, 612))
    if marker:
        pdf.setFillColorRGB(1, 0, 0)
        pdf.rect(66, 529, 47, 34, fill=1, stroke=0)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(68, 547, marker)
    pdf.showPage()
    pdf.save()
    return stream.getvalue()


def extract(data: bytes, defense: object | None = None) -> Any:
    """Extract synthetic metadata, optionally replacing the defense page."""
    with pdfplumber.open(BytesIO(data)) as pdf:
        target = defense if defense is not None else pdf.pages[1]
        return extract_metadata(pdf.pages[0], target, "a" * 64, "synthetic.pdf", 1)


def defense_with_rects(page: object, rects: list[dict[str, Any]], ordered: bool = True) -> object:
    """Return a page double with deliberately controlled rectangle ordering."""
    objects = {"rect": rects} if ordered else {}
    return SimpleNamespace(chars=page.chars, height=page.height, rects=rects, objects=objects)


def rect(
    color: tuple[float, float, float],
    x0: float = 66,
    x1: float = 113,
    top: float = 49,
    bottom: float = 83,
) -> dict[str, Any]:
    """Make a filled header rectangle in pdfplumber coordinates."""
    return {
        "x0": x0,
        "x1": x1,
        "top": top,
        "bottom": bottom,
        "fill": True,
        "non_stroking_color": color,
    }


def test_metadata_is_extracted_with_own_evidence() -> None:
    result = extract(pages())
    assert result.power_rating == 200.5
    assert result.recovery_range == range(10, 26)
    assert result.privileges == ("W",)
    assert {fact.label for fact in result.evidence} == {"power_rating", "recovery", "W"}
    assert all(fact.provenance.source_sha256 == "a" * 64 for fact in result.evidence)


@pytest.mark.parametrize("recovery_x", [582, 584.8])
def test_recovery_metadata_with_verified_left_shift_is_recognized(recovery_x: float) -> None:
    result = extract(pages(recovery_x=recovery_x))
    assert result.recovery_range == range(10, 26)


@pytest.mark.parametrize(
    "recovery",
    ["", "Fumble Recovered 10-25; Fumble Lost 28-39", "Fumble Recovered 10-40; Fumble Lost 41-39"],
)
def test_missing_or_inconsistent_recovery_is_rejected(recovery: str) -> None:
    with pytest.raises(MetadataError):
        extract(pages(recovery=recovery))


def test_absent_privilege_is_not_a_wildcard_entitlement() -> None:
    assert extract(pages(marker="")).privileges == ()


@pytest.mark.parametrize(
    "marker,color", [("FBO", (1, 0, 0)), ("SPBO", (1, 0, 0)), ("XWC", (0, 1, 0))]
)
def test_privilege_marker_colors_follow_documented_legend(
    marker: str, color: tuple[int, int, int]
) -> None:
    with pdfplumber.open(BytesIO(pages(marker=marker))) as pdf:
        defense = defense_with_rects(pdf.pages[1], [rect(color)])
        assert extract_metadata(pdf.pages[0], defense, "a" * 64, "synthetic.pdf", 1).privileges == (
            marker,
        )


def test_xwc_on_red_background_is_rejected() -> None:
    with pdfplumber.open(BytesIO(pages(marker="XWC"))) as pdf:
        defense = defense_with_rects(pdf.pages[1], [rect((1, 0, 0))])
        with pytest.raises(MetadataError, match="background"):
            extract_metadata(pdf.pages[0], defense, "a" * 64, "synthetic.pdf", 1)


def test_later_overlapping_rect_wins_by_paint_order() -> None:
    with pdfplumber.open(BytesIO(pages())) as pdf:
        defense = defense_with_rects(pdf.pages[1], [rect((0, 1, 0)), rect((1, 0, 0))])
        assert extract_metadata(pdf.pages[0], defense, "a" * 64, "synthetic.pdf", 1).privileges == (
            "W",
        )


def test_ambiguous_covering_rectangle_order_is_rejected() -> None:
    with pdfplumber.open(BytesIO(pages())) as pdf:
        defense = defense_with_rects(
            pdf.pages[1], [rect((0, 1, 0)), rect((1, 0, 0))], ordered=False
        )
        with pytest.raises(MetadataError, match="ambiguous"):
            extract_metadata(pdf.pages[0], defense, "a" * 64, "synthetic.pdf", 1)


def test_page_wide_privilege_rectangle_is_rejected() -> None:
    with pdfplumber.open(BytesIO(pages())) as pdf:
        defense = defense_with_rects(pdf.pages[1], [rect((1, 0, 0), 0, 792, 0, 612)])
        with pytest.raises(MetadataError, match="background"):
            extract_metadata(pdf.pages[0], defense, "a" * 64, "synthetic.pdf", 1)


def test_marker_box_without_text_is_rejected() -> None:
    with pdfplumber.open(BytesIO(pages(marker=""))) as pdf:
        defense = defense_with_rects(pdf.pages[1], [rect((1, 0, 0))])
        with pytest.raises(MetadataError, match="without text"):
            extract_metadata(pdf.pages[0], defense, "a" * 64, "synthetic.pdf", 1)


def test_evidence_uses_measured_fill_or_page_background() -> None:
    colored = extract(pages(rating_background=(0, 1, 0)))
    plain = extract(pages())
    colored_fact = next(f for f in colored.evidence if f.label == "power_rating")
    assert colored_fact.provenance.rgb_color == (0, 255, 0)
    plain_fact = next(f for f in plain.evidence if f.label == "power_rating")
    assert plain_fact.provenance.rgb_color is None


@pytest.mark.parametrize(
    "value",
    [
        0.25,
        (0.25,),
        [0.25],
        (0.25, 0.25, 0.25),
        [0.25, 0.25, 0.25],
        (0.2, 0.3, 0.4, 0.1),
    ],
)
def test_metadata_and_chart_color_parsers_share_rgb_shapes(value: object) -> None:
    expected = (184, 161, 138) if isinstance(value, tuple) and len(value) == 4 else (64, 64, 64)
    assert cell_rgb(value) == expected
    assert metadata_color({"non_stroking_color": value}) == expected


@pytest.mark.parametrize("rating", ["0200", "49.9", "500.1", "٢٠٠"])
def test_invalid_rating_format_or_plausibility_is_rejected(rating: str) -> None:
    with pytest.raises(MetadataError):
        extract(pages(rating=rating))


def test_rating_chars_on_different_baselines_do_not_merge() -> None:
    with pdfplumber.open(BytesIO(pages(rating="200"))) as pdf:
        chars = list(pdf.pages[0].chars)
        last_digit = [c for c in chars if c["upright"]][-1]
        stray = dict(last_digit, text="5", top=70, bottom=80, x0=535, x1=540)
        offense = SimpleNamespace(
            chars=chars + [stray],
            height=pdf.pages[0].height,
            width=pdf.pages[0].width,
            rects=pdf.pages[0].rects,
            objects=pdf.pages[0].objects,
        )
        with pytest.raises(MetadataError):
            extract_metadata(offense, pdf.pages[1], "a" * 64, "synthetic.pdf", 1)


def test_rating_char_gap_is_rejected() -> None:
    with pdfplumber.open(BytesIO(pages(rating="200"))) as pdf:
        chars = [dict(char) for char in pdf.pages[0].chars]
        last_digit = [c for c in chars if c["upright"]][-1]
        last_digit["x0"] += 10
        last_digit["x1"] += 10
        offense = SimpleNamespace(
            chars=chars,
            height=pdf.pages[0].height,
            width=pdf.pages[0].width,
            rects=pdf.pages[0].rects,
            objects=pdf.pages[0].objects,
        )
        with pytest.raises(MetadataError):
            extract_metadata(offense, pdf.pages[1], "a" * 64, "synthetic.pdf", 1)


@pytest.mark.parametrize(
    "recovery",
    [
        "Fumble Recovered 11-25; Fumble Lost 26-39",
        "Fumble Recovered 10-25; Fumble Lost 26-38",
        "Fumble Recovered ١٠-25; Fumble Lost 26-39",
    ],
)
def test_recovery_partition_and_ascii_digits_are_required(recovery: str) -> None:
    with pytest.raises(MetadataError):
        extract(pages(recovery=recovery))


def test_recovery_chars_must_share_a_column_and_chart_region() -> None:
    with pdfplumber.open(BytesIO(pages())) as pdf:
        chars = [dict(char) for char in pdf.pages[0].chars]
        rotated = [char for char in chars if not char["upright"]]
        rotated[0]["x0"] -= 3
        offense = SimpleNamespace(
            chars=chars,
            height=pdf.pages[0].height,
            width=pdf.pages[0].width,
            rects=pdf.pages[0].rects,
            objects=pdf.pages[0].objects,
        )
        with pytest.raises(MetadataError):
            extract_metadata(offense, pdf.pages[1], "a" * 64, "synthetic.pdf", 1)
