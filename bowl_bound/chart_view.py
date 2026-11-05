"""Read-only chart books from normalized engine facts, without source evidence."""

from dataclasses import dataclass

from .models import (
    Defense,
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    Priority,
    ResultKind,
    SupplementalColumn,
    TeamChart,
)
from .resolution import Operation, resolve_cells
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
class PriorityChartView:
    table: ChartTable
    note: str
    legend: tuple[ChartSymbol, ...]
    notes: tuple[str, ...]


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
    priority: PriorityChartView


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
        priority_reference(),
    )


@dataclass(frozen=True)
class _PriorityAxis:
    label: str
    description: str
    cell: NormalizedCell


def _reference_cell(
    kind: ResultKind, yards: int | None = None, priority: Priority = Priority.NORMAL
) -> NormalizedCell:
    return NormalizedCell(kind, None, yards=yards, priority=priority)


_PRIORITY_OFFENSE = (
    _PriorityAxis(
        "# / B", "Nonnegative yardage or Breakaway", _reference_cell(ResultKind.YARDS, 4)
    ),
    _PriorityAxis("-#", "Negative yardage", _reference_cell(ResultKind.YARDS, -2)),
    _PriorityAxis(
        "(#)",
        "Parenthesized offensive gain",
        _reference_cell(ResultKind.YARDS, 4, Priority.PARENTHESIZED),
    ),
    _PriorityAxis("blank", "White no-change cell", _reference_cell(ResultKind.NO_CHANGE)),
    _PriorityAxis("TD", "Touchdown", _reference_cell(ResultKind.TOUCHDOWN)),
    _PriorityAxis("QR", "Quarterback Run", _reference_cell(ResultKind.QUARTERBACK_RUN)),
    _PriorityAxis("QT", "Quarterback Trapped", _reference_cell(ResultKind.QUARTERBACK_TRAPPED)),
    _PriorityAxis("INC", "Incomplete pass", _reference_cell(ResultKind.INCOMPLETE)),
    _PriorityAxis("INT", "Interception", _reference_cell(ResultKind.INTERCEPTION, 12)),
    _PriorityAxis("F", "Fumble", _reference_cell(ResultKind.FUMBLE, 9)),
    _PriorityAxis(
        "SOP / BLP", "Sprint Out or Boot-leg pass", _reference_cell(ResultKind.SPRINT_OUT_PASS)
    ),
    _PriorityAxis(
        "PEN",
        "Offensive chart penalty",
        NormalizedCell(
            ResultKind.PENALTY, None, penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5)
        ),
    ),
)
_PRIORITY_DEFENSE = (
    _PriorityAxis("#", "Nonnegative yardage", _reference_cell(ResultKind.YARDS, 4)),
    _PriorityAxis("-#", "Negative yardage", _reference_cell(ResultKind.YARDS, -2)),
    _PriorityAxis("blank", "White no-change cell", _reference_cell(ResultKind.NO_CHANGE)),
    _PriorityAxis(
        "(#)", "Parenthesized gain", _reference_cell(ResultKind.YARDS, 4, Priority.PARENTHESIZED)
    ),
    _PriorityAxis(
        "(-#)", "Parenthesized loss", _reference_cell(ResultKind.YARDS, -2, Priority.PARENTHESIZED)
    ),
    _PriorityAxis(
        "[#]", "Bracketed gain", _reference_cell(ResultKind.YARDS, 4, Priority.BRACKETED)
    ),
    _PriorityAxis(
        "[-#]", "Bracketed loss", _reference_cell(ResultKind.YARDS, -2, Priority.BRACKETED)
    ),
    _PriorityAxis(
        "(TD) / [TD]", "Defensive touchdown entry", _reference_cell(ResultKind.TOUCHDOWN)
    ),
    _PriorityAxis("QR", "Quarterback Run", _reference_cell(ResultKind.QUARTERBACK_RUN)),
    _PriorityAxis("QT", "Quarterback Trapped", _reference_cell(ResultKind.QUARTERBACK_TRAPPED)),
    _PriorityAxis("INT", "Interception", _reference_cell(ResultKind.INTERCEPTION, 12)),
    _PriorityAxis("F", "Fumble", _reference_cell(ResultKind.FUMBLE, 9)),
    _PriorityAxis("INC", "Incomplete pass", _reference_cell(ResultKind.INCOMPLETE)),
    _PriorityAxis(
        "(B) †",
        "Approved defensive parenthesized Breakaway extension",
        _reference_cell(ResultKind.BREAKAWAY, priority=Priority.PARENTHESIZED),
    ),
)
_PRIORITY_LEGEND = {
    Operation.ADD: ChartSymbol(
        "ADD",
        "Add signed yardage; blank is zero. B and QR first roll their supplemental column, "
        "then add the defensive yards.",
    ),
    Operation.OFFENSE: ChartSymbol("O", "Use the offensive result and its out-of-bounds marker."),
    Operation.DEFENSE: ChartSymbol("D", "Use the defensive result and its out-of-bounds marker."),
    Operation.INCOMPLETE: ChartSymbol("INC", "Incomplete pass; no supplemental roll."),
    Operation.INTERCEPTION_MIN: ChartSymbol(
        "INT_MIN", "Interception at the lesser signed distance."
    ),
    Operation.FUMBLE_DEFENSE: ChartSymbol("F_DEF", "Offensive fumble at the defensive distance."),
    Operation.FUMBLE_MIN: ChartSymbol("F_MIN", "Offensive fumble at the lesser signed distance."),
    Operation.FUMBLE_END_ZONE: ChartSymbol(
        "F_ENDZONE", "Offensive fumble one yard into the defenders' end zone."
    ),
    Operation.OPTION: ChartSymbol(
        "OPT", "Cancel ordinary defense; reroll under Sprint Out (SOP) or Boot-leg (BLP)."
    ),
    Operation.PENALTY: ChartSymbol(
        "PEN", "Begin the penalty procedure, retaining the original defensive result."
    ),
    Operation.QUARTERBACK_TRAPPED: ChartSymbol(
        "QT", "Roll Quarterback Trapped; do not retain the defensive adjustment."
    ),
}
_PRIORITY_COLORS = {
    Operation.ADD: "green",
    Operation.INCOMPLETE: "black",
    Operation.PENALTY: "yellow",
    Operation.INTERCEPTION_MIN: "red",
    Operation.FUMBLE_DEFENSE: "red",
    Operation.FUMBLE_MIN: "red",
    Operation.FUMBLE_END_ZONE: "red",
    Operation.QUARTERBACK_TRAPPED: "red",
}


def priority_reference() -> PriorityChartView:
    """Derive a shared reference from pure engine lookups, without a second matrix."""
    rows = []
    for offense in _PRIORITY_OFFENSE:
        cells = []
        for defense in _PRIORITY_DEFENSE:
            operation = resolve_cells(offense.cell, defense.cell).operation
            key = _PRIORITY_LEGEND[operation]
            cells.append(
                ChartCellView(key.label, _PRIORITY_COLORS.get(operation, "white"), key.description)
            )
        rows.append(ChartRow(offense.label, offense.description, tuple(cells)))
    return PriorityChartView(
        ChartTable(
            "priority",
            "Priority chart",
            "Offense ↓ / Defense →",
            tuple(ChartColumn(axis.label, axis.label) for axis in _PRIORITY_DEFENSE),
            tuple(rows),
        ),
        "Read the offensive row across to the defensive column. This shared reference selects "
        "the controlling result; follow-up decisions still apply.",
        tuple(_PRIORITY_LEGEND.values()),
        (
            "# is nonnegative yardage; -# is a loss; blank is a white no-change cell. Parentheses "
            "and brackets are part of the entry.",
            "Offensive parenthesized gains beat ordinary defense and defensive parentheses; "
            "defensive brackets or TD still win.",
            "INT against defensive QR becomes QT. INT against defensive TD is incomplete; F "
            "against defensive TD is a fumble one yard deep.",
            "Minimum locations use signed comparison: min(12, -3) = -3.",
            "† The (B) column is the approved defensive Breakaway extension. Offensive "
            "parenthesized yardage, SOP/BLP rerolls and the penalty procedure still take priority; "
            "otherwise the offense rolls its B column.",
            "This is the ordinary scrimmage reference. Offered special calls use their own engine "
            "procedures.",
        ),
    )
