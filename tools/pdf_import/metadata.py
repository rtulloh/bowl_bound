"""Strict positioned metadata extraction; white means page background; no vector fill present."""

import re
from dataclasses import dataclass
from math import isfinite
from typing import Any

from bowl_bound.models import BoundingBox, Provenance
from bowl_bound.normalization import ChartColor, chart_color_for_rgb
from bowl_bound.team_csv import LOCAL_PLACEHOLDER_POWER_RATING

from .colors import PDFColorError, pdf_color_shape_matches, rgb_from_pdf_color


class MetadataError(ValueError):
    """Required metadata is absent, ambiguous, or inconsistent."""


class MissingPowerRatingError(MetadataError):
    """The supported rating box contains no printed power rating."""


@dataclass(frozen=True)
class MetadataFact:
    label: str
    provenance: Provenance


@dataclass(frozen=True)
class TeamMetadata:
    power_rating: float
    recovery_range: range
    privileges: tuple[str, ...]
    evidence: tuple[MetadataFact, ...]
    power_rating_is_placeholder: bool = False


def _color(rect: dict[str, Any]) -> tuple[int, int, int]:
    color_space = rect.get("ncs")
    if color_space not in (None, "DeviceRGB", "DeviceGray", "DeviceCMYK"):
        raise MetadataError("Background color is unsupported")
    value = rect.get("non_stroking_color")
    if not pdf_color_shape_matches(value, color_space):
        raise MetadataError("Background color is unsupported")
    try:
        return rgb_from_pdf_color(value)
    except PDFColorError as error:
        raise MetadataError("Background color is unsupported") from error


def _contains(rect: dict[str, Any], chars: list[dict[str, Any]]) -> bool:
    return all(
        rect["x0"] <= char["x0"] <= char["x1"] <= rect["x1"]
        and rect["top"] <= char["top"] <= char["bottom"] <= rect["bottom"]
        for char in chars
    )


def _background(
    page: object, chars: list[dict[str, Any]], tight: bool = False
) -> tuple[int, int, int] | None:
    rects = [rect for rect in page.rects if rect.get("fill") and _contains(rect, chars)]
    if tight and any(
        rect["x1"] - rect["x0"] > 150 or rect["bottom"] - rect["top"] > 80 for rect in rects
    ):
        raise MetadataError("Privilege background is not a tight marker box")
    if not rects:
        return None
    objects = getattr(page, "objects", None)
    ordered = objects.get("rect") if isinstance(objects, dict) else None
    if isinstance(ordered, list):
        rects = [rect for rect in ordered if rect in rects]
    elif len({_color(rect) for rect in rects}) > 1:
        raise MetadataError("Background paint order is ambiguous")
    return _color(rects[-1])


def _evidence(
    page: object,
    chars: list[dict[str, Any]],
    digest: str,
    filename: str,
    page_number: int,
    label: str,
    text: str,
) -> MetadataFact:
    if not chars:
        raise MetadataError(f"Missing {label} evidence")
    x0 = min(char["x0"] for char in chars)
    top = min(char["top"] for char in chars)
    x1 = max(char["x1"] for char in chars)
    bottom = max(char["bottom"] for char in chars)
    source_bbox = getattr(page, "source_bbox", None)
    if callable(source_bbox):
        box = source_bbox(x0, top, x1, bottom)
    else:
        box = BoundingBox(x0, page.height - bottom, x1, page.height - top)
    rgb = _background(page, chars)
    return MetadataFact(label, Provenance(digest, filename, page_number, box, text, rgb))


def _rating(page: object) -> tuple[list[dict[str, Any]], str, float]:
    chars = [
        char
        for char in page.chars
        if char["upright"] and 475 < char["x0"] < 576 and 50 < char["top"] < 80
    ]
    chars.sort(key=lambda char: char["x0"])
    text = "".join(char["text"] for char in chars)
    has_numeric_glyph = any(char["text"].isascii() and char["text"].isdigit() for char in chars)
    if not has_numeric_glyph:
        raise MissingPowerRatingError("No numeric power rating in the supported header box")
    if (
        max(char["top"] for char in chars) - min(char["top"] for char in chars) > 1
        or any(right["x0"] - left["x1"] > 3 for left, right in zip(chars, chars[1:], strict=False))
        or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text)
        or (text.startswith("0") and not text.startswith("0."))
    ):
        raise MetadataError("Missing or ambiguous power rating in the supported header box")
    value = float(text)
    if not isfinite(value) or not 50.0 <= value <= 500.0:
        raise MetadataError("Power rating must be between 50.0 and 500.0")
    return chars, text, value


def _recovery(page: object) -> tuple[list[dict[str, Any]], str, int]:
    chars = [char for char in page.chars if not char["upright"] and char["x0"] > page.width * 0.90]
    if (
        not chars
        or max(char["x0"] for char in chars) - min(char["x0"] for char in chars) > 2
        or any(not (100 < char["top"] and char["bottom"] < 700) for char in chars)
    ):
        raise MetadataError("Missing or ambiguous fumble recovery endpoints")
    chars.sort(key=lambda char: -char["top"])
    text = "".join(char["text"] for char in chars)
    normalized = " ".join(text.replace("–", "-").split())
    match = re.fullmatch(
        r"Fumble Recovered ([0-9]+)-([0-9]+);?\s*Fumble Lost ([0-9]+)-([0-9]+)",
        normalized,
        re.I,
    )
    if match is None:
        raise MetadataError("Missing or ambiguous fumble recovery endpoints")
    start, end, lost_start, lost_end = map(int, match.groups())
    if start != 10 or lost_start != end + 1 or lost_end != 39 or not 10 <= end < 39:
        raise MetadataError("Recovery and loss endpoints must partition rolls 10 through 39")
    return chars, text, end


def extract_metadata(
    offense: object,
    defense: object,
    source_sha256: str,
    filename: str,
    offense_page: int,
    *,
    use_local_rating_placeholder: bool = False,
) -> TeamMetadata:
    """Extract rating, recovery endpoints, and privilege markers without enforcing options."""
    if type(use_local_rating_placeholder) is not bool:
        raise TypeError("use_local_rating_placeholder must be a boolean")
    try:
        rating_chars, rating_text, rating = _rating(offense)
        rating_is_placeholder = False
    except MissingPowerRatingError:
        if not use_local_rating_placeholder:
            raise
        rating_chars, rating_text = [], ""
        rating = LOCAL_PLACEHOLDER_POWER_RATING
        rating_is_placeholder = True
    recovery_chars, recovery_text, end = _recovery(offense)
    facts = []
    if not rating_is_placeholder:
        facts.append(
            _evidence(
                offense,
                rating_chars,
                source_sha256,
                filename,
                offense_page,
                "power_rating",
                rating_text,
            )
        )
    facts.extend(
        [
            _evidence(
                offense,
                recovery_chars,
                source_sha256,
                filename,
                offense_page,
                "recovery",
                recovery_text,
            ),
        ]
    )
    marker_chars = [
        char
        for char in defense.chars
        if char["upright"] and 65 <= char["x0"] < 114 and 48 <= char["top"] < 83
    ]
    marker = "".join(char["text"] for char in sorted(marker_chars, key=lambda c: c["x0"])).strip()
    if not marker:
        header_rects = [
            rect
            for rect in defense.rects
            if (
                rect.get("fill")
                and 65 <= rect["x0"]
                and rect["x1"] <= 114
                and 48 <= rect["top"]
                and rect["bottom"] <= 83
                and rect["x1"] - rect["x0"] <= 150
                and rect["bottom"] - rect["top"] <= 80
            )
        ]
        if any(
            chart_color_for_rgb(_color(rect)) in {ChartColor.RED, ChartColor.GREEN}
            for rect in header_rects
        ):
            raise MetadataError("Privilege marker box is present without text")
        return TeamMetadata(rating, range(10, end + 1), (), tuple(facts), rating_is_placeholder)
    if marker not in {"W", "FBO", "SPBO", "XWC"}:
        raise MetadataError("Unrecognized privilege marker in supported header box")
    rgb = _background(defense, marker_chars, tight=True)
    if rgb is None:
        raise MetadataError("Privilege background evidence is missing")
    expected = ChartColor.GREEN if marker == "XWC" else ChartColor.RED
    if chart_color_for_rgb(rgb) is not expected:
        raise MetadataError("Privilege marker conflicts with its background")
    facts.append(
        _evidence(
            defense,
            marker_chars,
            source_sha256,
            filename,
            offense_page + 1,
            marker,
            marker,
        )
    )
    return TeamMetadata(rating, range(10, end + 1), (marker,), tuple(facts), rating_is_placeholder)
