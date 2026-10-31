"""Complete synthetic vector PDFs for exercising the PDF import pipeline."""

import typing
from pathlib import Path

from reportlab.pdfgen import canvas

OFFENSE_EDGES = (
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
DEFENSE_EDGES = (
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
Color = tuple[int, int, int]
Spec = dict[tuple[str, str, int, str | None], tuple[str, Color]]


def _token(section: str, column: str, roll: int, defense: str | None) -> tuple[str, Color]:
    """Return deterministic valid raw evidence for one non-PAT chart address."""
    if (section, column, roll, defense) == ("offense", "1", 10, None):
        return "3", (255, 0, 0)
    seed = roll + sum(map(ord, section + column + (defense or "")))
    choices = (("3", (255, 0, 0)), ("5", (0, 255, 0)), ("", (255, 255, 255)), ("", (0, 0, 0)))
    return choices[seed % 4]


def _set_color(pdf: canvas.Canvas, color: Color) -> None:
    pdf.setFillColorRGB(*(channel / 255 for channel in color))


def _rect(
    pdf: canvas.Canvas, height: float, x0: float, top: float, x1: float, bottom: float
) -> None:
    pdf.rect(x0, height - bottom, x1 - x0, bottom - top, fill=1, stroke=0)


def _header(pdf: canvas.Canvas, name: str, season: int, role: str) -> None:
    pdf.saveState()
    pdf.translate(20, 70)
    pdf.rotate(90)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(0, 0, f"{season} {name} {role}")
    pdf.restoreState()


def _grid(
    pdf: canvas.Canvas,
    height: float,
    edges: tuple[float, ...],
    top: float,
    bottom: float,
    pitch: float,
    omit_boundary: bool,
) -> None:
    pdf.setFillColorRGB(0, 0, 0)
    for index, edge in enumerate(edges):
        if omit_boundary and index == len(edges) // 2:
            continue
        _rect(pdf, height, edge - 0.48, top, edge + 0.48, bottom)
    for row in range(31):
        boundary = top + row * pitch
        _rect(pdf, height, edges[0], boundary - 0.25, edges[-1], boundary + 0.25)


def _draw_cells(
    pdf: canvas.Canvas,
    height: float,
    edges: tuple[float, ...],
    top: float,
    pitch: float,
    groups: tuple[tuple[str, tuple[str, ...], tuple[float, ...]], ...],
    spec: Spec,
    overrides: dict[tuple[str, str, int, str | None], tuple[str, Color]],
    bad_token: bool,
    unknown_fill: bool,
) -> None:
    for row in range(30):
        row_top = top + row * pitch
        row_bottom = row_top + pitch
        for section, columns, group_edges in groups:
            defense = chr(ord("A") + row // 5) if section == "defense" else None
            roll = row % 5 + 1 if section == "defense" else row + 10
            for index, column in enumerate(columns):
                text, color = _token(section, column, roll, defense)
                override = overrides.get((section, column, roll, defense))
                if override is not None:
                    text, color = override
                if bad_token and (section, column, roll, defense) == ("offense", "1", 10, None):
                    text = "NOPE"
                if unknown_fill and (section, column, roll, defense) == ("offense", "2", 10, None):
                    color = (26, 51, 76)
                spec[(section, column, roll, defense)] = (text, color)
                _set_color(pdf, color)
                _rect(pdf, height, group_edges[index], row_top, group_edges[index + 1], row_bottom)
                if text:
                    pdf.setFillColorRGB(0, 0, 0)
                    pdf.setFont("Helvetica", 6)
                    pdf.drawCentredString(
                        (group_edges[index] + group_edges[index + 1]) / 2,
                        height - row_bottom + (pitch - 6) / 2,
                        text,
                    )


def _offense(pdf: canvas.Canvas, team: dict[str, typing.Any], spec: Spec) -> None:
    height, top, pitch = 792.0, 112.80, 17.40
    pdf.setPageSize((612, 792))
    _header(pdf, str(team["school"]), int(team["season"]), "offense")
    _grid(pdf, height, OFFENSE_EDGES, top, 634.80, pitch, bool(team.get("omit_boundary")))
    if not team.get("missing_rating"):
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(510, 720, str(team.get("rating_text", "200.5")))
    pdf.saveState()
    pdf.translate(590, 180)
    pdf.rotate(90)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(0, 0, str(team.get("recovery", "Fumble Recovered 10-25; Fumble Lost 26-39")))
    pdf.restoreState()
    pdf.setFont("Helvetica", 9)
    pdf.drawString(90, 690, "Line Plunge  Option  QT  QR  B")
    _draw_cells(
        pdf,
        height,
        OFFENSE_EDGES,
        top,
        pitch,
        (
            ("offense", tuple(map(str, range(1, 10))), OFFENSE_EDGES[1:11]),
            ("supplemental", ("QT", "QR", "B"), OFFENSE_EDGES[11:15]),
        ),
        spec,
        team.get("cell_overrides", {}),
        bool(team.get("bad_token")),
        bool(team.get("unknown_fill")),
    )
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 8)
    for row in range(30):
        y = 122.23 + row * pitch
        pdf.drawString(70, height - y - 2, str(row + 10))
    pdf.showPage()


def _defense(
    pdf: canvas.Canvas,
    team: dict[str, typing.Any],
    spec: Spec,
    team_index: int,
    *,
    rotated: bool = False,
) -> None:
    height, top, pitch = 612.0, 112.56, 14.52
    if rotated:
        pdf.setPageSize((612, 792))
        pdf.saveState()
        pdf.translate(612, 0)
        pdf.rotate(90)
    else:
        pdf.setPageSize((792, 612))
        _header(pdf, str(team["mascot"]), int(team["season"]), "defense")
    _grid(pdf, height, DEFENSE_EDGES, top, 548.16, pitch, False)
    pdf.setFillColorRGB(1, 0, 0)
    pdf.rect(66, 529, 47, 34, fill=1, stroke=0)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(82, 547, "W")
    pdf.drawString(150, 570, "Defense  Kickoff  Punt  Field Goal")
    _draw_cells(
        pdf,
        height,
        DEFENSE_EDGES,
        top,
        pitch,
        (
            ("defense", tuple(map(str, range(1, 10))), DEFENSE_EDGES[2:12]),
            (
                "special_teams",
                (
                    "kickoff",
                    "kickoff_return",
                    "punt",
                    "punt_return",
                    "interception_return",
                    "field_goal",
                ),
                DEFENSE_EDGES[12:19],
            ),
        ),
        spec,
        team.get("cell_overrides", {}),
        False,
        False,
    )
    failures = {16} if team_index == 0 else {12, 26}
    for row in range(30):
        row_top = top + row * pitch
        row_bottom = row_top + pitch
        roll = row + 10
        color = (255, 0, 0) if roll in failures else (255, 255, 255)
        _set_color(pdf, color)
        _rect(pdf, height, DEFENSE_EDGES[18], row_top, DEFENSE_EDGES[19], row_bottom)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 8)
    for row in range(30):
        y = 120.46 + row * pitch
        roll = row + 10
        printed = str(roll + 1) if team.get("bad_pat") and roll == 16 else str(roll)
        pdf.drawString(754, height - y - 2, printed)
        pdf.drawString(118, height - y - 2, str(row % 5 + 1))
    if rotated:
        pdf.restoreState()
    pdf.showPage()


def write_chart_pdf(path: Path, teams: list[dict[str, typing.Any]]) -> Spec:
    """Write complete supported synthetic chart pairs and return their independent cell spec."""
    pdf = canvas.Canvas(str(path), pagesize=(612, 792))
    spec: Spec = {}
    for index, team in enumerate(teams):
        _offense(pdf, team, spec)
        if not team.get("drop_defense"):
            _defense(pdf, team, spec, index, rotated=bool(team.get("rotated_defense")))
    pdf.save()
    return spec
