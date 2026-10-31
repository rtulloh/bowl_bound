"""Coordinate views for explicitly supported PDF page rotations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Any

from bowl_bound.models import BoundingBox


def _turn_matrix(char: dict[str, Any]) -> None:
    """Undo the page's clockwise turn in one character's text matrix."""
    matrix = char.get("matrix")
    if not isinstance(matrix, (tuple, list)) or len(matrix) != 6:
        return
    a, b, c, d, e, f = matrix
    linear = (a, b, c, d)
    if any(type(value) not in (int, float) or not isfinite(value) for value in linear):
        return
    scale = max(abs(value) for value in linear)
    if scale == 0:
        return
    orientations = (
        (0, (1, 0, 0, 1)),
        (90, (0, 1, -1, 0)),
        (180, (-1, 0, 0, -1)),
        (270, (0, -1, 1, 0)),
    )
    rotation = None
    for candidate, expected in orientations:
        if all(
            isclose(actual / scale, target, abs_tol=0.01)
            for actual, target in zip(linear, expected, strict=True)
        ):
            rotation = candidate
            break
    if rotation is None:
        return

    normalized = (rotation - 90) % 360
    components = dict(orientations)[normalized]
    char["matrix"] = tuple(scale * value for value in components) + (e, f)
    char["upright"] = normalized in (0, 180)


def _turn_object(item: dict[str, Any], source_height: float, *, character: bool = False) -> dict:
    """Rotate one pdfplumber object's bounding box into landscape coordinates."""
    transformed = dict(item)
    x0, top, x1, bottom = (float(item[key]) for key in ("x0", "top", "x1", "bottom"))
    transformed.update(
        x0=source_height - bottom,
        top=x0,
        x1=source_height - top,
        bottom=x1,
    )
    if "width" in item:
        transformed["width"] = transformed["x1"] - transformed["x0"]
    if "height" in item:
        transformed["height"] = transformed["bottom"] - transformed["top"]
    if character:
        _turn_matrix(transformed)
    return transformed


@dataclass(frozen=True)
class RotatedPortraitPage:
    """A 90-degree normalized view that retains links to original PDF coordinates."""

    source_page: object
    width: float
    height: float
    chars: tuple[dict, ...]
    rects: tuple[dict, ...]
    lines: tuple[dict, ...]
    curves: tuple[dict, ...]
    images: tuple[dict, ...]
    objects: dict[str, list[dict]]

    @classmethod
    def from_page(cls, page: object) -> RotatedPortraitPage:
        source_height = float(page.height)
        source_width = float(page.width)
        chars = tuple(_turn_object(item, source_height, character=True) for item in page.chars)
        rects = tuple(_turn_object(item, source_height) for item in page.rects)
        lines = tuple(_turn_object(item, source_height) for item in page.lines)
        curves = tuple(_turn_object(item, source_height) for item in page.curves)
        images = tuple(_turn_object(item, source_height) for item in page.images)
        objects = {
            "char": list(chars),
            "rect": list(rects),
            "line": list(lines),
            "curve": list(curves),
            "image": list(images),
        }
        return cls(page, source_height, source_width, chars, rects, lines, curves, images, objects)

    def extract_words(self, **kwargs: Any) -> list[dict]:
        """Extract words from normalized characters without importing PDF tools eagerly."""
        from pdfplumber.utils import extract_words

        return extract_words(list(self.chars), **kwargs)

    def source_bbox(self, x0: float, top: float, x1: float, bottom: float) -> BoundingBox:
        """Map a normalized box back to bottom-origin coordinates on the source page."""
        return BoundingBox(top, x0, bottom, x1)


def rotate_portrait_page(page: object) -> RotatedPortraitPage:
    """Return a landscape view of a verified portrait page with 90-degree content."""
    return RotatedPortraitPage.from_page(page)
