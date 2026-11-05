"""Read-only chart books from normalized engine facts, without source evidence."""

from dataclasses import dataclass

from .models import (
    Defense,
    NormalizedCell,
    Play,
    Priority,
    ResultKind,
    SupplementalColumn,
    TeamChart,
)
from .session import DEFENSE_LABELS, PLAY_LABELS
from .team_csv import format_cell


@dataclass(frozen=True)
class ChartCellView:
    label: str
    color: str
    description: str


@dataclass(frozen=True)
class ChartColumn:
    key: str
    label: str


@dataclass(frozen=True)
class ChartRow:
    label: str
    description: str
    cells: tuple[ChartCellView, ...]


@dataclass(frozen=True)
class ChartTable:
    key: str
    title: str
    roll_label: str
    columns: tuple[ChartColumn, ...]
    rows: tuple[ChartRow, ...]


@dataclass(frozen=True)
class ChartLegend:
    color: str
    label: str
    description: str


@dataclass(frozen=True)
class ChartSymbol:
    label: str
    description: str


@dataclass(frozen=True)
class ChartBook:
    team: str
    season: int
    note: str
    offense: ChartTable
    defense: ChartTable
    legend: tuple[ChartLegend, ...]
    symbols: tuple[ChartSymbol, ...]
    formations: tuple[ChartColumn, ...]


LEGEND = (
    ChartLegend("green", "Green", "Gains and results such as B or TD; read the cell."),
    ChartLegend("red", "Red", "Losses, turnovers and results such as QT; read the cell."),
    ChartLegend("white", "White", "No change or a named chart reference; read the cell."),
    ChartLegend("black", "Black", "Incomplete pass (INC)."),
    ChartLegend("yellow", "Yellow", "Penalty; OFF, DEF or PI identifies the call."),
)
SYMBOLS = (
    ChartSymbol("0", "No yardage adjustment. A white blank is shown as 0."),
    ChartSymbol("*", "Out of bounds when the applicable result is used."),
    ChartSymbol("( ) / [ ]", "Printed priority markers; the engine applies the resolution rules."),
    ChartSymbol(
        "B / QR / QT", "Breakaway / quarterback run / quarterback trapped supplemental column."
    ),
    ChartSymbol("SOP / BLP", "Resolve using Sprint Out / Boot-leg."),
    ChartSymbol(
        "INT / F", "Interception / fumble at the printed distance from the line of scrimmage."
    ),
    ChartSymbol(
        "DS / X / T1–T3",
        "DS sums die faces; X is 40 minus the total. T1–T3 sum one to three fresh totals.",
    ),
    ChartSymbol("INC / TD", "Incomplete pass / touchdown."),
    ChartSymbol("OFF / DEF / PI", "Offensive penalty / defensive penalty / pass interference."),
)
_NAMES = {
    ResultKind.BREAKAWAY: "Breakaway",
    ResultKind.QUARTERBACK_RUN: "Quarterback run",
    ResultKind.QUARTERBACK_TRAPPED: "Quarterback trapped",
    ResultKind.SPRINT_OUT_PASS: "Sprint Out pass",
    ResultKind.BOOTLEG_PASS: "Boot-leg pass",
}


def _cell_view(cell: NormalizedCell) -> ChartCellView:
    label = format_cell(cell)
    if cell.kind is ResultKind.NO_CHANGE:
        label = "0*" if cell.out_of_bounds else "0"
    elif cell.kind is ResultKind.INCOMPLETE:
        label = "INC"
    name = _NAMES.get(cell.kind, cell.kind.value.replace("_", " "))
    details = [f"{name}: {label}"]
    if cell.priority is not Priority.NORMAL:
        details.append(f"{cell.priority.value} priority")
    if cell.out_of_bounds:
        details.append("out of bounds")
    color = cell.chart_color.value if cell.chart_color is not None else "unclassified"
    details.append(f"{color} chart cell")
    return ChartCellView(label, color, "; ".join(details))


def chart_book(chart: TeamChart) -> ChartBook:
    """Present every offensive/defensive cell without rolling or resolving a play."""
    plays = tuple(
        ChartColumn(str(play.value), f"{play.value} · {PLAY_LABELS[play]}") for play in Play
    )
    supplemental = tuple(
        ChartColumn(column.value, f"{column.value} · {_NAMES[ResultKind(column.value)]}")
        for column in SupplementalColumn
    )
    offense = {(record.roll, record.play): record.cell for record in chart.offense}
    extra = {(record.roll, record.column): record.cell for record in chart.supplemental}
    defense = {(record.defense, record.roll, record.play): record.cell for record in chart.defense}
    return ChartBook(
        chart.name,
        chart.season,
        "Chart reference: these are chart cells, not predicted final yardage. "
        "The engine combines the applicable offense and defense results. "
        "Dice totals are not equally likely.",
        ChartTable(
            "offense",
            "Offense",
            "Offensive total",
            plays + supplemental,
            tuple(
                ChartRow(
                    str(roll),
                    f"Offensive total {roll}",
                    tuple(_cell_view(offense[roll, play]) for play in Play)
                    + tuple(_cell_view(extra[roll, column]) for column in SupplementalColumn),
                )
                for roll in range(10, 40)
            ),
        ),
        ChartTable(
            "defense",
            "Defense",
            "Formation · total",
            plays,
            tuple(
                ChartRow(
                    f"{formation.value} · {roll}",
                    f"{formation.value} {DEFENSE_LABELS[formation]}; defensive total {roll}",
                    tuple(_cell_view(defense[formation, roll, play]) for play in Play),
                )
                for formation in Defense
                for roll in range(1, 6)
            ),
        ),
        LEGEND,
        SYMBOLS,
        tuple(ChartColumn(d.value, f"{d.value} · {DEFENSE_LABELS[d]}") for d in Defense),
    )
