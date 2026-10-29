"""Lossless raw cell extraction from a verified pdfplumber page."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import TYPE_CHECKING

from bowl_bound.models import BoundingBox, Provenance

if TYPE_CHECKING:
    from pdfplumber.page import Page

_EPSILON = 0.01


class CellExtractionError(ValueError):
    """Raised when PDF geometry cannot prove a cell's raw evidence."""


@dataclass(frozen=True)
class CellBounds:
    """One cell in pdfplumber's top-origin coordinate system."""

    x0: float
    top: float
    x1: float
    bottom: float

    def __post_init__(self) -> None:
        values = (self.x0, self.top, self.x1, self.bottom)
        if any(type(value) not in (int, float) or not isfinite(value) for value in values):
            raise TypeError("cell bounds must use finite numeric coordinates")
        if self.x0 >= self.x1 or self.top >= self.bottom:
            raise ValueError("cell bounds must have positive width and height")


@dataclass(frozen=True)
class ExtractedCell:
    """Raw text, rendering evidence, and source provenance for a chart cell."""

    bounds: CellBounds
    text: str
    rgb_color: tuple[int, int, int]
    rotation: int
    provenance: Provenance


def extract_cells(
    page: Page | object,
    bounds: tuple[CellBounds, ...],
    *,
    source_sha256: str,
    filename: str,
    page_number: int,
) -> tuple[ExtractedCell, ...]:
    """Extract lossless text and proven background color for each requested cell."""
    if type(bounds) is not tuple or any(type(cell) is not CellBounds for cell in bounds):
        raise TypeError("bounds must be a tuple of CellBounds")
    if len(set(bounds)) != len(bounds):
        raise CellExtractionError("duplicate cell bounds are ambiguous")
    if not bounds:
        return ()
    height = _page_height(page)
    _validate_page_bounds(bounds, page, height)
    chars = tuple(getattr(page, "chars", ()))
    rectangles = tuple(getattr(page, "rects", ()))
    lines = tuple(getattr(page, "lines", ()))
    curves = tuple(getattr(page, "curves", ()))
    images = tuple(getattr(page, "images", ()))
    _validate_objects(chars, "character")
    _validate_objects(rectangles, "rectangle")
    _validate_objects(lines, "line")
    _validate_objects(curves, "curve")
    _validate_objects(images, "image")
    result = []
    for cell in bounds:
        interior = _inset(cell)
        _reject_interior_lines(lines, cell)
        _reject_unsupported(curves, interior, "curve")
        _reject_unsupported(images, interior, "image")
        selected = _cell_chars(chars, cell)
        rotation = _rotation(selected)
        text = _text(selected, rotation)
        color = _background(page, rectangles, cell)
        box = BoundingBox(cell.x0, height - cell.bottom, cell.x1, height - cell.top)
        provenance = Provenance(source_sha256, filename, page_number, box, text, color)
        result.append(ExtractedCell(cell, text, color, rotation, provenance))
    return tuple(result)


def _page_height(page: object) -> float:
    height = getattr(page, "height", None)
    if type(height) not in (int, float) or not isfinite(height) or height <= 0:
        raise CellExtractionError("page has no finite positive height")
    return float(height)


def _validate_page_bounds(bounds: tuple[CellBounds, ...], page: object, height: float) -> None:
    width = getattr(page, "width", None)
    if type(width) not in (int, float) or not isfinite(width) or width <= 0:
        raise CellExtractionError("page has no finite positive width")
    for cell in bounds:
        if cell.x0 < 0 or cell.top < 0 or cell.x1 > width or cell.bottom > height:
            raise CellExtractionError("cell bounds fall outside the page")
    for index, cell in enumerate(bounds):
        if any(_overlaps(cell, other) for other in bounds[index + 1 :]):
            raise CellExtractionError("overlapping cell bounds are ambiguous")


def _overlaps(left: CellBounds, right: CellBounds) -> bool:
    return (
        left.x0 < right.x1 - _EPSILON
        and right.x0 < left.x1 - _EPSILON
        and left.top < right.bottom - _EPSILON
        and right.top < left.bottom - _EPSILON
    )


def _validate_objects(objects: tuple[dict, ...], label: str) -> None:
    for item in objects:
        try:
            values = tuple(float(item[key]) for key in ("x0", "top", "x1", "bottom"))
        except (KeyError, TypeError, ValueError) as error:
            raise CellExtractionError(f"{label} has invalid geometry") from error
        x0, top, x1, bottom = values
        if not all(isfinite(value) for value in values) or x0 > x1 or top > bottom:
            raise CellExtractionError(f"{label} has invalid geometry")


def _cell_chars(chars: tuple[dict, ...], cell: CellBounds) -> list[dict]:
    selected = []
    for char in chars:
        try:
            intersects = _intersects(char, cell)
            contained = _contains(cell, char)
        except (KeyError, TypeError, ValueError) as error:
            raise CellExtractionError("character has invalid geometry") from error
        if intersects and not contained:
            raise CellExtractionError("character crosses a cell boundary")
        if contained:
            if not isinstance(char.get("text"), str):
                raise CellExtractionError("character has non-text content")
            selected.append(char)
    return selected


def _contains(cell: CellBounds, item: dict) -> bool:
    return (
        float(item["x0"]) >= cell.x0 - _EPSILON
        and float(item["x1"]) <= cell.x1 + _EPSILON
        and float(item["top"]) >= cell.top - _EPSILON
        and float(item["bottom"]) <= cell.bottom + _EPSILON
    )


def _intersects(item: dict, cell: CellBounds) -> bool:
    return (
        float(item["x0"]) < cell.x1 - _EPSILON
        and float(item["x1"]) > cell.x0 + _EPSILON
        and float(item["top"]) < cell.bottom - _EPSILON
        and float(item["bottom"]) > cell.top + _EPSILON
    )


def _rotation(chars: list[dict]) -> int:
    rotations = {_char_rotation(char) for char in chars}
    if len(rotations) > 1:
        raise CellExtractionError("cell contains mixed text rotations")
    return rotations.pop() if rotations else 0


def _char_rotation(char: dict) -> int:
    matrix = char.get("matrix")
    if matrix is None:
        if char.get("upright", True):
            return 0
        raise CellExtractionError("rotated character lacks a text matrix")
    if not isinstance(matrix, (tuple, list)) or len(matrix) != 6:
        raise CellExtractionError("character has an impossible text matrix")
    a, b, c, d, e, f = matrix
    if any(type(value) not in (int, float) or not isfinite(value) for value in (a, b, c, d, e, f)):
        raise CellExtractionError("character has an impossible text matrix")
    candidates = {
        0: (1, 0, 0, 1),
        90: (0, 1, -1, 0),
        180: (-1, 0, 0, -1),
        270: (0, -1, 1, 0),
    }
    scale = next((abs(value) for value in (a, b, c, d) if abs(value) > _EPSILON), 0)
    for rotation, expected in candidates.items():
        normalized = zip((a, b, c, d), expected, strict=True)
        matches = (
            isclose(actual / scale, target, abs_tol=_EPSILON) for actual, target in normalized
        )
        if scale and all(matches):
            return rotation
    raise CellExtractionError("character has an impossible text matrix")


def _ordered(chars: list[dict], rotation: int) -> list[dict]:
    rows: list[list[dict]] = []
    for char in sorted(chars, key=lambda item: _axes(item, rotation)[0]):
        cross_axis, _, _ = _axes(char, rotation)
        if not rows or abs(cross_axis - _axes(rows[-1][0], rotation)[0]) > 1:
            rows.append([char])
        else:
            rows[-1].append(char)
    return [char for row in rows for char in sorted(row, key=lambda item: _axes(item, rotation)[1])]


def _axes(char: dict, rotation: int) -> tuple[float, float, float]:
    x0, top, x1, bottom = (float(char[key]) for key in ("x0", "top", "x1", "bottom"))
    if rotation == 0:
        return top, x0, x1
    if rotation == 90:
        return x0, -top, -bottom
    if rotation == 180:
        return -bottom, -x1, -x0
    return -x1, top, bottom


def _text(chars: list[dict], rotation: int) -> str:
    ordered = _ordered(chars, rotation)
    pieces: list[str] = []
    previous: dict | None = None
    for char in ordered:
        if previous is not None:
            previous_cross, _, previous_end = _axes(previous, rotation)
            cross_axis, primary, _ = _axes(char, rotation)
            separator = "\n" if abs(previous_cross - cross_axis) > 1 else ""
            if not separator and primary - previous_end > _gap_threshold(previous, char):
                separator = " "
            preserves_space = pieces[-1].endswith((" ", "\n")) or char["text"].startswith(" ")
            if separator and not preserves_space:
                pieces.append(separator)
        pieces.append(char["text"])
        previous = char
    return "".join(pieces)


def _gap_threshold(previous: dict, following: dict) -> float:
    sizes = (previous.get("size"), following.get("size"))
    numeric = [float(size) for size in sizes if type(size) in (int, float) and isfinite(size)]
    return min(2, (min(numeric) if numeric else 5) * 0.2)


def _reject_interior_lines(lines: tuple[dict, ...], cell: CellBounds) -> None:
    for line in lines:
        try:
            if _intersects(line, cell):
                raise CellExtractionError("vector line crosses a cell interior")
        except KeyError as error:
            raise CellExtractionError("line has invalid geometry") from error


def _reject_unsupported(objects: tuple[dict, ...], cell: CellBounds, label: str) -> None:
    if any(_intersects(item, cell) for item in objects):
        raise CellExtractionError(f"unsupported {label} intersects a cell interior")


def _background(page: object, rects: tuple[dict, ...], cell: CellBounds) -> tuple[int, int, int]:
    interior = _inset(cell)
    filled = [rect for rect in rects if rect.get("fill") and _intersects(rect, interior)]
    colors = [(rect, _rect_color(rect)) for rect in filled]
    full = [(rect, color) for rect, color in colors if _covers(rect, interior)]
    if full:
        if len(full) != len(colors):
            raise CellExtractionError("partial background paint is ambiguous")
        distinct = {color for _, color in full}
        if len(distinct) == 1:
            return full[-1][1]
        ordered = _ordered_rects(page, rects)
        if ordered is None:
            raise CellExtractionError("overlapping full paint has ambiguous order")
        try:
            return max(full, key=lambda entry: ordered.index(id(entry[0])))[1]
        except ValueError as error:
            raise CellExtractionError("overlapping full paint has ambiguous order") from error
    by_color: dict[tuple[int, int, int], list[dict]] = {}
    for rect, color in colors:
        by_color.setdefault(color, []).append(rect)
    if len(by_color) == 1 and by_color and _covers_union(next(iter(by_color.values())), interior):
        return next(iter(by_color))
    if colors:
        raise CellExtractionError("partial background paint is ambiguous")
    if _has_grid(cell, rects, tuple(getattr(page, "lines", ()))):
        return (255, 255, 255)
    raise CellExtractionError("cell background is not proven by fill or grid geometry")


def _ordered_rects(page: object, rects: tuple[dict, ...]) -> list[int] | None:
    objects = getattr(page, "objects", None)
    ordered = objects.get("rect") if isinstance(objects, dict) else None
    if not isinstance(ordered, list):
        return None
    return [id(rect) for rect in ordered if rect in rects]


def _rect_color(rect: dict) -> tuple[int, int, int]:
    color_space = rect.get("ncs")
    if color_space not in (None, "DeviceRGB", "DeviceGray"):
        raise CellExtractionError("background has unsupported color space")
    return _rgb(rect.get("non_stroking_color"))


def _rgb(value: object) -> tuple[int, int, int]:
    if type(value) in (int, float):
        channels = (value, value, value)
    elif isinstance(value, (tuple, list)) and len(value) == 1:
        channels = (value[0],) * 3
    elif isinstance(value, (tuple, list)) and len(value) == 3:
        channels = tuple(value)
    else:
        raise CellExtractionError("background has unsupported color space")
    if any(type(channel) not in (int, float) or not isfinite(channel) for channel in channels):
        raise CellExtractionError("background has unsupported color values")
    if not all(0 <= channel <= 1 for channel in channels):
        raise CellExtractionError("background has unsupported color values")
    return tuple(round(channel * 255) for channel in channels)


def _inset(cell: CellBounds) -> CellBounds:
    horizontal = min(2, (cell.x1 - cell.x0) / 2 - _EPSILON)
    vertical = min(2, (cell.bottom - cell.top) / 2 - _EPSILON)
    return CellBounds(
        cell.x0 + horizontal,
        cell.top + vertical,
        cell.x1 - horizontal,
        cell.bottom - vertical,
    )


def _covers(rect: dict, cell: CellBounds) -> bool:
    return (
        float(rect["x0"]) <= cell.x0 + _EPSILON
        and float(rect["x1"]) >= cell.x1 - _EPSILON
        and float(rect["top"]) <= cell.top + _EPSILON
        and float(rect["bottom"]) >= cell.bottom - _EPSILON
    )


def _has_grid(cell: CellBounds, rects: tuple[dict, ...], lines: tuple[dict, ...]) -> bool:
    objects = (*rects, *lines)
    return (
        _boundary(objects, cell, "top")
        and _boundary(objects, cell, "bottom")
        and _boundary(objects, cell, "left")
        and _boundary(objects, cell, "right")
    )


def _boundary(objects: tuple[dict, ...], cell: CellBounds, side: str) -> bool:
    horizontal = side in {"top", "bottom"}
    coordinate = (
        (cell.top if side == "top" else cell.bottom)
        if horizontal
        else (cell.x0 if side == "left" else cell.x1)
    )
    intervals: list[tuple[float, float]] = []
    for item in objects:
        x0, top, x1, bottom = (float(item[key]) for key in ("x0", "top", "x1", "bottom"))
        if horizontal:
            thin = bottom - top <= 4
            spans_side = top - 2 <= coordinate <= bottom + 2
            intervals.extend([(max(cell.x0, x0), min(cell.x1, x1))] if thin and spans_side else [])
        else:
            thin = x1 - x0 <= 4
            spans_side = x0 - 2 <= coordinate <= x1 + 2
            if thin and spans_side:
                intervals.append((max(cell.top, top), min(cell.bottom, bottom)))
        if not item.get("fill") and _is_cell_stroke(item, cell):
            intervals.append((cell.x0, cell.x1) if horizontal else (cell.top, cell.bottom))
    start = cell.x0 if horizontal else cell.top
    end = cell.x1 if horizontal else cell.bottom
    return _covers_interval(intervals, start, end)


def _is_cell_stroke(item: dict, cell: CellBounds) -> bool:
    return (
        abs(float(item["x0"]) - cell.x0) <= 2
        and abs(float(item["x1"]) - cell.x1) <= 2
        and abs(float(item["top"]) - cell.top) <= 2
        and abs(float(item["bottom"]) - cell.bottom) <= 2
    )


def _covers_interval(intervals: list[tuple[float, float]], start: float, end: float) -> bool:
    edge = start
    for left, right in sorted(intervals):
        if right <= edge:
            continue
        if left > edge + 2:
            return False
        edge = max(edge, right)
        if edge >= end - 2:
            return True
    return edge >= end - 2


def _covers_union(rects: list[dict], cell: CellBounds) -> bool:
    points = {cell.x0, cell.x1}
    for rect in rects:
        points.update((max(cell.x0, float(rect["x0"])), min(cell.x1, float(rect["x1"]))))
    for left, right in zip(sorted(points), sorted(points)[1:], strict=False):
        intervals = sorted(
            (max(cell.top, float(rect["top"])), min(cell.bottom, float(rect["bottom"])))
            for rect in rects
            if float(rect["x0"]) < right - _EPSILON and float(rect["x1"]) > left + _EPSILON
        )
        edge = cell.top
        for top, bottom in intervals:
            if top > edge + _EPSILON:
                return False
            edge = max(edge, bottom)
        if edge < cell.bottom - _EPSILON:
            return False
    return True
