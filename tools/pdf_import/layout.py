"""Cell coordinates for the explicitly supported 2002 vector-layout profile."""

import re
from dataclasses import dataclass

from .cells import CellBounds


class LayoutError(ValueError):
    """Page geometry or roll anchors do not match the supported layout."""


@dataclass(frozen=True)
class CellPosition:
    """A chart address and its top-origin PDF bounds, not a game result."""

    section: str
    column: str
    roll: int
    bounds: CellBounds
    defense: str | None = None


def _column_edges(page: object, offense: bool) -> tuple[tuple[float, ...], ...]:
    """Read vertical vector-grid centers; supported pages vary their column widths."""
    top, bottom = (112.8, 634.8) if offense else (112.56, 548.16)
    candidates = sorted(
        rect["x0"] + rect["width"] / 2
        for rect in getattr(page, "rects", ())
        if 0 < rect["width"] <= 3
        and rect["height"] >= 14
        and rect["top"] < bottom
        and rect["bottom"] > top
        and 0 <= rect["x0"] < page.width
    )
    clusters: list[list[float]] = []
    for center in candidates:
        if clusters and center - clusters[-1][0] <= 0.5:
            clusters[-1].append(center)
        else:
            clusters.append([center])
    centers = [round(sum(cluster) / len(cluster), 2) for cluster in clusters]
    expected = 16 if offense else 20
    if len(centers) != expected:
        raise LayoutError(f"Expected {expected} proven vertical column boundaries")
    reference = (
        (
            66.24,
            86.76,
            126.96,
            165.60,
            208.20,
            248.40,
            291.00,
            333.60,
            376.20,
            418.80,
            461.40,
            480.36,
            506.40,
            532.44,
            556.08,
            575.76,
        )
        if offense
        else (
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
    )
    if any(
        abs(actual - nominal) > (2.6 if offense else 0.75)
        for actual, nominal in zip(centers, reference, strict=True)
    ):
        raise LayoutError("Unsupported vertical column geometry or foreign boundary")
    if offense:
        return tuple(centers[1:11]), tuple(centers[11:15])
    return tuple(centers[2:12]), tuple(centers[12:19]), tuple(centers[18:20])


_SPECIAL_COLUMNS = (
    "kickoff",
    "kickoff_return",
    "punt",
    "punt_return",
    "interception_return",
    "field_goal",
)


def _roll_centers(page: object, x0: float, x1: float, sequence: tuple[int, ...]) -> list[float]:
    words = sorted(
        (
            word
            for word in page.extract_words()
            if x0 <= word["x0"] < x1
            and 110 < word["top"] < 640
            and re.fullmatch(r"[0-9]+", word["text"])
        ),
        key=lambda word: word["top"],
    )
    if tuple(int(word["text"]) for word in words) != sequence:
        raise LayoutError("Missing, duplicate, or displaced roll anchors in supported chart layout")
    return [(word["top"] + word["bottom"]) / 2 for word in words]


def locate_cells(page: object, role: str) -> tuple[CellPosition, ...]:
    """Return every chart/PAT address after checking page size and printed roll anchors.

    Coordinates are a named layout profile, not inferred from historical yardage.
    Other sizes, shifts, or row sequences fail instead of inventing cell positions.
    """
    if role not in {"offense", "defense_special"}:
        raise LayoutError("Unknown page role")
    expected_size = (612, 792) if role == "offense" else (792, 612)
    if any(
        abs(actual - expected) > 0.5
        for actual, expected in zip((page.width, page.height), expected_size, strict=True)
    ):
        raise LayoutError("Only the documented letter-page vector layout is supported")
    offense = role == "offense"
    top, pitch = (112.80, 17.40) if offense else (112.56, 14.52)
    centers = _roll_centers(
        page, 67 if offense else 751, 85 if offense else 769, tuple(range(10, 40))
    )
    if any(
        abs(center - (top + pitch * (index + 0.5))) > 1.5 for index, center in enumerate(centers)
    ):
        raise LayoutError("Printed roll anchors do not match the supported row grid")
    if not offense:
        defense_centers = _roll_centers(page, 114, 132, tuple(range(1, 6)) * 6)
        if any(
            abs(left - right) > 0.5 for left, right in zip(centers, defense_centers, strict=True)
        ):
            raise LayoutError("Defense roll anchors do not align with special-team rows")
    edges_by_group = _column_edges(page, offense)
    positions: list[CellPosition] = []
    for index in range(30):
        row_top = top + pitch * index
        row_bottom = row_top + pitch
        if offense:
            groups = (
                ("offense", tuple(str(i) for i in range(1, 10)), edges_by_group[0]),
                ("supplemental", ("QT", "QR", "B"), edges_by_group[1]),
            )
        else:
            groups = (
                ("defense", tuple(str(i) for i in range(1, 10)), edges_by_group[0]),
                ("special_teams", _SPECIAL_COLUMNS, edges_by_group[1]),
                ("pat", ("pat",), edges_by_group[2]),
            )
        for section, columns, edges in groups:
            for column_index, column in enumerate(columns):
                positions.append(
                    CellPosition(
                        section,
                        column,
                        index % 5 + 1 if section == "defense" else index + 10,
                        CellBounds(
                            edges[column_index], row_top, edges[column_index + 1], row_bottom
                        ),
                        chr(ord("A") + index // 5) if section == "defense" else None,
                    )
                )
    return tuple(positions)
