"""Bowl Bound priority resolution plus B/QR/QT and Option rerolls; no state transitions."""

# Priority Chart Reference (Bowl Bound 2007, printed p.34 / PDF p.37):
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |OFF \ DEF|#    |-#   |blank|(#)  |(-#) |[#]  |[-#] |TD*  |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |# / B    |ADD  |ADD  |ADD  |(#)  |(-#) |[#]  |[-#] |TD   |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |-#       |ADD  |ADD  |ADD  |(#)  |(-#) |[#]  |[-#] |TD   |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |(#)      |O(#) |O(#) |O(#) |O(#) |O(#) |[#]  |[-#] |TD   |O(#) |O(#) |O(#) |O(#) |O(#) |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |blank    |ADD  |ADD  |ADD  |(#)  |(-#) |[#]  |[-#] |TD   |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |TD       |TD   |TD   |TD   |(#)  |(-#) |[#]  |[-#] |TD   |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |QR       |ADD  |ADD  |ADD  |(#)  |(-#) |[#]  |[-#] |TD   |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |QT       |QT   |QT   |QT   |(#)  |(-#) |[#]  |[-#] |TD   |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |INC      |INC  |INC  |INC  |(#)  |(-#) |[#]  |[-#] |TD   |QR   |QT   |INT #|F #  |INC  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |INT #    |INT #|INT #|INT #|INC  |INT< |INC  |INT< |INC  |QT   |INT #|INT< |INT #|INT #|
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |F #      |F #  |F #  |F #  |Fdef |F<   |Fdef |F<   |FdEZ |F #  |F #  |INT #|F<   |F #  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |SOP/BLP  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |OPT  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# |PEN      |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |PEN  |
# +---------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
# TD*: defensive (TD) and [TD] share this column; see printed p.38 correction.
# O(#): offensive parenthesized yards win. Other (#)/[#] entries select defense.
# INT< / F<: turnover at the lesser signed yardage of offense and defense.
# Fdef: offensive fumble at defensive yardage. FdEZ: fumble one yard into defense EZ.
# OPT: cancel ordinary defense; one offensive reroll under Play 7 (SOP) / 8 (BLP).
# PEN: penalty procedure takes priority; original defense retained (Milestone 11).
# B/QR/QT: reroll the matching supplemental column; B/QR ADD keeps the defensive yards.
# Chart/prose conflicts and project interpretations: docs/priority-chart.md.
from dataclasses import dataclass, replace
from enum import Enum

from .dice import DefensiveRoll, DiceSource, OffensiveRoll
from .models import (
    ChartColor,
    Defense,
    NormalizedCell,
    PenaltyData,
    Play,
    Priority,
    ResultKind,
    SupplementalColumn,
    TeamChart,
)
from .variable_yardage import roll_variable


class ChartResolutionError(ValueError):
    """A chart coordinate or bounded supplemental sequence cannot be resolved."""


class Operation(str, Enum):
    ADD = "ADD"
    OFFENSE = "O"
    DEFENSE = "D"
    INCOMPLETE = "INC"
    INTERCEPTION_MIN = "INT_MIN"
    FUMBLE_DEFENSE = "F_DEF"
    FUMBLE_MIN = "F_MIN"
    FUMBLE_END_ZONE = "F_ENDZONE"
    OPTION = "OPTION"
    PENALTY = "PENALTY"
    QUARTERBACK_TRAPPED = "QT"


class Source(str, Enum):
    OFFENSE = "offense"
    DEFENSE = "defense"
    BOTH = "both"
    CHART = "priority_chart"


# Columns: +#, -#, blank, (#), (-#), [#], [-#], TD, QR, QT, INT, F, INC, defensive (B).
# The printed chart combines (TD) and [TD]; the p.38 correction gives both TD priority.
_BASE = "ADD ADD ADD D D D D D D D D D INC"
_PRIORITY_TABLE = {
    "positive": _BASE + " D",
    "negative": _BASE + " D",
    "B": _BASE + " D",
    "blank": _BASE + " D",
    "parenthesized": "O O O O O D D D O O O O O O",
    "TD": "O O O D D D D D D D D D INC D",
    "QR": _BASE + " D",
    "QT": "O O O D D D D D D D D D INC D",
    "INC": "INC INC INC D D D D D D D D D INC D",
    "INT": "O O O INC INT_MIN INC INT_MIN INC QT O INT_MIN O O D",
    "F": "O O O F_DEF F_MIN F_DEF F_MIN F_ENDZONE O O D F_MIN O D",
    "OPTION": " ".join(["OPTION"] * 14),
    "PENALTY": " ".join(["PENALTY"] * 14),
}
_COLUMNS = (
    "positive",
    "negative",
    "blank",
    "paren_positive",
    "paren_negative",
    "bracket_positive",
    "bracket_negative",
    "TD",
    "QR",
    "QT",
    "INT",
    "F",
    "INC",
    "paren_breakaway",
)
_VARIABLES = {
    ResultKind.VARIABLE_DS,
    ResultKind.VARIABLE_X,
    ResultKind.VARIABLE_T1,
    ResultKind.VARIABLE_T2,
    ResultKind.VARIABLE_T3,
}
_PENDING = _VARIABLES | {
    ResultKind.BREAKAWAY,
    ResultKind.QUARTERBACK_RUN,
    ResultKind.QUARTERBACK_TRAPPED,
    ResultKind.PENALTY,
    ResultKind.SPRINT_OUT_PASS,
    ResultKind.BOOTLEG_PASS,
    ResultKind.INTERCEPTION,
    ResultKind.FUMBLE,
}


@dataclass(frozen=True)
class PriorityResult:
    """Resolved ordinary fact or explicit pending branch; original facts stay intact."""

    operation: Operation
    source: Source
    kind: ResultKind | None
    yards: int | None
    pending: bool
    offense: NormalizedCell
    defense: NormalizedCell
    offense_category: str
    defense_category: str
    out_of_bounds: bool = False
    penalty: PenaltyData | None = None
    defensive_end_zone_depth: int | None = None
    guaranteed_out_of_bounds: bool = False
    bounds_declaration: str | None = None
    bounds_cost: int = 0


@dataclass(frozen=True)
class LookupTrace:
    section: str
    team_name: str
    season: int
    play: Play
    formation: Defense | None
    roll: OffensiveRoll | DefensiveRoll
    cell: NormalizedCell


@dataclass(frozen=True)
class AdvancedDefenseTrace:
    """A rule-table defensive result, separate from a team-chart cell lookup."""

    call: str
    team_name: str
    season: int
    play: Play
    roll: DefensiveRoll
    cell: str
    section: str = "advanced_defense"


@dataclass(frozen=True)
class RazzleDazzleTrace:
    """Record an observed Razzle-Dazzle comparison roll without implying a chart lookup."""

    section: str
    team_name: str
    season: int
    roll: OffensiveRoll


@dataclass(frozen=True)
class PlayResolution:
    called_play: Play
    resolved_play: Play
    result: PriorityResult
    trace: tuple[LookupTrace | AdvancedDefenseTrace | RazzleDazzleTrace, ...]
    bad_snap: bool = False
    conditional_double: bool = False
    qb_sneak: bool = False
    razzle_dazzle: bool = False


def _rule_cell(
    kind: ResultKind, *, yards: int | None = None, priority: Priority = Priority.NORMAL
) -> NormalizedCell:
    return NormalizedCell(kind, None, yards=yards, priority=priority)


def resolve_advanced_play(
    offense: TeamChart,
    defense: TeamChart,
    play: Play,
    call: str,
    dice: DiceSource,
    *,
    free_wildcard: bool,
) -> PlayResolution:
    """Resolve an Advanced II call using rule facts, never another team's chart cells."""
    wildcard_calls = {
        *(f"WC{item.value}" for item in Play if item is not Play.FIVE),
        "WC5",
        "WC5SOP",
        "WC5BLP",
        "WCSNEAK",
        "WCRZDZ",
    }
    if type(play) is not Play or call not in {"RUN", "PASS", "NICKEL", "REDZONE"} | wildcard_calls:
        raise ValueError("unknown Advanced II defense")

    wildcard = call.startswith("WC")
    guessed = Play(int(call[2])) if wildcard and call not in {"WCSNEAK", "WCRZDZ"} else None
    wildcard_branch = call[3:] if wildcard and play is Play.FIVE else ""
    if wildcard and play is not Play.FIVE and guessed is play:
        kind = ResultKind.YARDS if play.value <= 5 else ResultKind.INCOMPLETE
        result = resolve_cells(
            _rule_cell(kind, yards=0) if kind is ResultKind.YARDS else _rule_cell(kind),
            _rule_cell(ResultKind.NO_CHANGE),
        )
        return PlayResolution(play, play, result, ())

    off_roll = dice.offensive()
    off_cell = next(
        record.cell
        for record in offense.offense
        if record.play is play and record.roll == off_roll.total
    )
    blank = _rule_cell(ResultKind.NO_CHANGE)
    trace: list[LookupTrace | AdvancedDefenseTrace] = [
        LookupTrace("offense", offense.name, offense.season, play, None, off_roll, off_cell)
    ]
    option_branch = off_cell.kind in {
        ResultKind.SPRINT_OUT_PASS,
        ResultKind.BOOTLEG_PASS,
    }
    resolved_play = (
        Play.SEVEN
        if off_cell.kind is ResultKind.SPRINT_OUT_PASS
        else Play.EIGHT
        if off_cell.kind is ResultKind.BOOTLEG_PASS
        else play
    )
    if wildcard and play is Play.FIVE:
        actual_branch = {
            ResultKind.SPRINT_OUT_PASS: "SOP",
            ResultKind.BOOTLEG_PASS: "BLP",
        }.get(off_cell.kind, "")
        if actual_branch == wildcard_branch:
            resolved_play = {
                "SOP": Play.SEVEN,
                "BLP": Play.EIGHT,
            }.get(actual_branch, Play.FIVE)
            kind = ResultKind.INCOMPLETE if actual_branch else ResultKind.YARDS
            result = resolve_cells(
                _rule_cell(kind, yards=0) if kind is ResultKind.YARDS else _rule_cell(kind),
                blank,
            )
            return PlayResolution(play, resolved_play, result, tuple(trace))
    defensive_cell = blank
    conditional_double = wildcard and not free_wildcard
    if not wildcard and call != "REDZONE":
        defensive_roll = dice.defensive()
        pass_like = _is_pass_like(resolved_play, off_cell)
        defensive_cell = _advanced_defensive_cell(call, resolved_play, defensive_roll.total)
        trace.append(
            AdvancedDefenseTrace(
                call,
                defense.name,
                defense.season,
                resolved_play,
                defensive_roll,
                _rule_cell_label(defensive_cell),
            )
        )
        conditional_double = (
            call in {"RUN", "PASS"}
            and ((call == "RUN" and pass_like) or (call == "PASS" and not pass_like))
            and not free_wildcard
        )

    resolved_offense = off_cell
    if option_branch:
        option_roll = dice.offensive()
        option_cell = next(
            record.cell
            for record in offense.offense
            if record.play is resolved_play and record.roll == option_roll.total
        )
        trace.append(
            LookupTrace(
                "option",
                offense.name,
                offense.season,
                resolved_play,
                None,
                option_roll,
                option_cell,
            )
        )
        resolved_offense = option_cell

    result = resolve_cells(resolved_offense, defensive_cell)
    result = _supplemental_result(offense, result, resolved_play, dice, trace)
    result = _variable_result(result, offense, defense, resolved_play, dice, trace)
    return PlayResolution(
        play, resolved_play, result, tuple(trace), conditional_double=conditional_double
    )


def resolve_qb_sneak(
    offense: TeamChart,
    call: str | None,
    dice: DiceSource,
    *,
    free_wildcard: bool,
) -> PlayResolution:
    """Resolve Advanced I-2 from Play 1's classified box color only."""
    blank = _rule_cell(ResultKind.NO_CHANGE)
    if call == "WCSNEAK":
        result = resolve_cells(_rule_cell(ResultKind.YARDS, yards=0), blank)
        return PlayResolution(Play.ONE, Play.ONE, result, (), qb_sneak=True)

    roll = dice.offensive()
    cell = next(
        record.cell
        for record in offense.offense
        if record.play is Play.ONE and record.roll == roll.total
    )
    color = cell.chart_color
    if color is ChartColor.GREEN:
        sneak_cell = _rule_cell(ResultKind.YARDS, yards=1)
    elif color in {ChartColor.WHITE, ChartColor.YELLOW}:
        sneak_cell = _rule_cell(ResultKind.YARDS, yards=0)
    elif color is ChartColor.RED:
        sneak_cell = _rule_cell(ResultKind.FUMBLE, yards=0)
    else:
        raise ChartResolutionError(
            "QB Sneak requires a recognized green, white, yellow, or red Play 1 box"
        )

    result = resolve_cells(sneak_cell, blank)
    trace = (LookupTrace("offense", offense.name, offense.season, Play.ONE, None, roll, cell),)
    conditional_double = call is not None and call.startswith("WC") and not free_wildcard
    return PlayResolution(
        Play.ONE,
        Play.ONE,
        result,
        trace,
        conditional_double=conditional_double,
        qb_sneak=True,
    )


def _advanced_defensive_cell(call: str, play: Play, roll: int) -> NormalizedCell:
    """Return the printed Advanced II value for this play and defensive roll."""
    if call == "RUN" and roll == 1 and play.value <= 5:
        return _rule_cell(ResultKind.YARDS, yards=0, priority=Priority.PARENTHESIZED)
    if call == "PASS" and roll == 1 and play.value >= 7:
        return _rule_cell(ResultKind.INCOMPLETE)
    if call == "NICKEL":
        if roll <= 5 and play.value <= 5:
            return _rule_cell(ResultKind.YARDS, yards=2)
        if roll == 1 and play.value >= 7:
            return _rule_cell(ResultKind.INCOMPLETE)
    return _rule_cell(ResultKind.NO_CHANGE)


def _is_pass_like(play: Play, cell: NormalizedCell) -> bool:
    return play.value >= 6 or cell.kind in {
        ResultKind.QUARTERBACK_RUN,
        ResultKind.QUARTERBACK_TRAPPED,
    }


def resolve_razzle_dazzle_result(
    offense: TeamChart,
    defense: TeamChart,
    play: Play,
    total: int,
    comparison_rolls: tuple[OffensiveRoll, OffensiveRoll],
    formation: Defense,
    dice: DiceSource,
    *,
    advanced_call: str | None,
    free_wildcard: bool,
) -> PlayResolution:
    """Resolve a selected Razzle-Dazzle chart cell using its original comparison roll."""
    if type(play) is not Play or type(formation) is not Defense:
        raise TypeError("Razzle-Dazzle requires a selected play and chart formation")
    if total not in {roll.total for roll in comparison_rolls}:
        raise ValueError("selected Razzle-Dazzle total was not rolled")
    if advanced_call not in {None, "RUN", "PASS", "NICKEL", "REDZONE"} and not (
        advanced_call.startswith("WC") and advanced_call != "WCRZDZ"
    ):
        raise ValueError("unknown Razzle-Dazzle defensive call")

    selected_roll = next(roll for roll in comparison_rolls if roll.total == total)
    off_cell = next(
        record.cell for record in offense.offense if record.play is play and record.roll == total
    )
    trace: list[LookupTrace | AdvancedDefenseTrace | RazzleDazzleTrace] = [
        RazzleDazzleTrace(
            "razzle_dazzle:defense_roll", defense.name, defense.season, comparison_rolls[0]
        ),
        RazzleDazzleTrace(
            "razzle_dazzle:offense_roll", offense.name, offense.season, comparison_rolls[1]
        ),
        LookupTrace("offense", offense.name, offense.season, play, None, selected_roll, off_cell),
    ]

    option_play = {
        ResultKind.SPRINT_OUT_PASS: Play.SEVEN,
        ResultKind.BOOTLEG_PASS: Play.EIGHT,
    }.get(off_cell.kind)
    resolved_play = option_play or play
    defensive_cell = _rule_cell(ResultKind.NO_CHANGE)
    conditional_double = False
    advanced = advanced_call is not None
    wildcard = advanced_call is not None and advanced_call.startswith("WC")

    if advanced_call is None:
        defensive_roll = dice.defensive()
        defensive_cell = next(
            record.cell
            for record in defense.defense
            if record.play is play
            and record.defense is formation
            and record.roll == defensive_roll.total
        )
        trace.append(
            LookupTrace(
                "defense",
                defense.name,
                defense.season,
                play,
                formation,
                defensive_roll,
                defensive_cell,
            )
        )
    elif wildcard:
        # Every ordinary Wild Card guess is wrong against RZDZ, including a
        # selected cell that later matches the guess. WCRZDZ is handled before
        # these rolls are made.
        conditional_double = not free_wildcard
    elif advanced_call in {"RUN", "PASS", "NICKEL"}:
        defensive_roll = dice.defensive()
        pass_like = _is_pass_like(resolved_play, off_cell)
        defensive_cell = _advanced_defensive_cell(
            advanced_call, resolved_play, defensive_roll.total
        )
        trace.append(
            AdvancedDefenseTrace(
                advanced_call,
                defense.name,
                defense.season,
                resolved_play,
                defensive_roll,
                _rule_cell_label(defensive_cell),
            )
        )
        conditional_double = (
            advanced_call in {"RUN", "PASS"}
            and (
                (advanced_call == "RUN" and pass_like)
                or (advanced_call == "PASS" and not pass_like)
            )
            and not free_wildcard
        )

    if advanced and option_play is not None:
        option_roll = dice.offensive()
        option_cell = next(
            record.cell
            for record in offense.offense
            if record.play is option_play and record.roll == option_roll.total
        )
        trace.append(
            LookupTrace(
                "option", offense.name, offense.season, option_play, None, option_roll, option_cell
            )
        )
        off_cell = option_cell
    result = resolve_cells(off_cell, defensive_cell)
    if not advanced and result.operation is Operation.OPTION:
        option_play = Play.SEVEN if result.kind is ResultKind.SPRINT_OUT_PASS else Play.EIGHT
        option_roll = dice.offensive()
        option_cell = next(
            record.cell
            for record in offense.offense
            if record.play is option_play and record.roll == option_roll.total
        )
        trace.append(
            LookupTrace(
                "option", offense.name, offense.season, option_play, None, option_roll, option_cell
            )
        )
        resolved_play = option_play
        result = resolve_cells(option_cell, _blank_like(defensive_cell))

    result = _supplemental_result(offense, result, resolved_play, dice, trace)
    result = _variable_result(result, offense, defense, resolved_play, dice, trace)
    return PlayResolution(
        play,
        resolved_play,
        result,
        tuple(trace),
        conditional_double=conditional_double,
        razzle_dazzle=True,
    )


def _rule_cell_label(cell: NormalizedCell) -> str:
    if cell.kind is ResultKind.YARDS:
        value = str(cell.yards)
        return f"({value})" if cell.priority is Priority.PARENTHESIZED else f"+{value}"
    return "INC" if cell.kind is ResultKind.INCOMPLETE else "blank"


def _category(cell: NormalizedCell, defensive: bool) -> str:
    if not isinstance(cell, NormalizedCell):
        raise TypeError("priority inputs must be normalized cells")
    kind = cell.kind
    if kind is ResultKind.YARDS or kind in _VARIABLES:
        if cell.priority is Priority.BRACKETED and not defensive:
            raise ChartResolutionError("bracketed offense is not a Priority Chart row")
        if not defensive and cell.priority is Priority.PARENTHESIZED:
            if (cell.yards is not None and cell.yards < 0) or (cell.variable_multiplier or 1) < 0:
                raise ChartResolutionError(
                    "parenthesized offensive losses are not a Priority Chart row"
                )
            return "parenthesized"
        negative = (cell.yards is not None and cell.yards < 0) or (
            cell.variable_multiplier or 1
        ) < 0
        sign = "negative" if negative else "positive"
        prefix = {
            Priority.NORMAL: "",
            Priority.PARENTHESIZED: "paren_",
            Priority.BRACKETED: "bracket_",
        }[cell.priority]
        return prefix + sign
    if defensive and kind is ResultKind.BREAKAWAY and cell.priority is Priority.PARENTHESIZED:
        return "paren_breakaway"
    if cell.priority is not Priority.NORMAL and kind is not ResultKind.TOUCHDOWN:
        raise ChartResolutionError("priority decoration is unsupported for this result")
    if kind is ResultKind.TOUCHDOWN:
        if not defensive and cell.priority is not Priority.NORMAL:
            raise ChartResolutionError(
                "decorated offensive touchdowns are not a Priority Chart row"
            )
        return "TD"
    categories = {
        ResultKind.NO_CHANGE: "blank",
        ResultKind.INCOMPLETE: "INC",
        ResultKind.QUARTERBACK_RUN: "QR",
        ResultKind.QUARTERBACK_TRAPPED: "QT",
        ResultKind.INTERCEPTION: "INT",
        ResultKind.FUMBLE: "F",
    }
    if not defensive:
        categories.update(
            {
                ResultKind.BREAKAWAY: "B",
                ResultKind.SPRINT_OUT_PASS: "OPTION",
                ResultKind.BOOTLEG_PASS: "OPTION",
                ResultKind.PENALTY: "PENALTY",
            }
        )
    if kind not in categories:
        raise ChartResolutionError("result has no ordinary Priority Chart coordinate")
    return categories[kind]


def resolve_cells(offense: NormalizedCell, defense: NormalizedCell) -> PriorityResult:
    """Apply printed Priority Chart row × column; consume no dice.

    Unresolved variable distances stay symbolic in the input facts. Supplemental, option,
    penalty, and recovery branches are pending, never silently treated as zero yards.
    """
    row, column = _category(offense, False), _category(defense, True)
    code = _PRIORITY_TABLE[row].split()[_COLUMNS.index(column)]
    if code == "QT":
        operation, source, kind, yards = (
            Operation.QUARTERBACK_TRAPPED,
            Source.CHART,
            ResultKind.QUARTERBACK_TRAPPED,
            None,
        )
        return PriorityResult(operation, source, kind, yards, True, offense, defense, row, column)
    operation = Operation(code)
    source = Source.CHART
    kind: ResultKind | None = None
    yards: int | None = None
    pending = False
    bounds = False
    penalty = None
    depth = None
    if operation in {Operation.OFFENSE, Operation.DEFENSE, Operation.OPTION, Operation.PENALTY}:
        selected = defense if operation is Operation.DEFENSE else offense
        source = Source.DEFENSE if operation is Operation.DEFENSE else Source.OFFENSE
        kind, yards, bounds, penalty = (
            selected.kind,
            selected.yards,
            selected.out_of_bounds,
            selected.penalty,
        )
        pending = kind in _PENDING
    elif operation is Operation.INCOMPLETE:
        kind = ResultKind.INCOMPLETE
    elif operation is Operation.ADD:
        source = Source.BOTH
        bounds = offense.out_of_bounds or defense.out_of_bounds
        pending = offense.kind in _PENDING or defense.kind in _PENDING
        # B/QR is a supplemental reference, not an integer to add to defense.
        if offense.kind in {ResultKind.BREAKAWAY, ResultKind.QUARTERBACK_RUN}:
            kind = offense.kind
        elif offense.kind in _VARIABLES or defense.kind in _VARIABLES:
            kind = None
        else:
            kind = ResultKind.YARDS
            yards = (offense.yards or 0) + (defense.yards or 0)
    else:
        kind = (
            ResultKind.INTERCEPTION
            if operation is Operation.INTERCEPTION_MIN
            else ResultKind.FUMBLE
        )
        source = Source.BOTH
        pending = True
        if operation is Operation.FUMBLE_END_ZONE:
            depth = 1
        elif operation is Operation.FUMBLE_DEFENSE:
            yards = defense.yards
        elif offense.yards is not None and defense.yards is not None:
            yards = min(offense.yards, defense.yards)
    return PriorityResult(
        operation,
        source,
        kind,
        yards,
        pending,
        offense,
        defense,
        row,
        column,
        bounds,
        penalty,
        depth,
    )


# Safety bound only: a valid chart reaches a final result long before this.
MAX_SUPPLEMENTAL_REROLLS = 10


def _supplemental_column(kind: ResultKind) -> SupplementalColumn | None:
    return {
        ResultKind.BREAKAWAY: SupplementalColumn.BREAKAWAY,
        ResultKind.QUARTERBACK_RUN: SupplementalColumn.QUARTERBACK_RUN,
        ResultKind.QUARTERBACK_TRAPPED: SupplementalColumn.QUARTERBACK_TRAPPED,
    }.get(kind)


def _blank_like(cell: NormalizedCell) -> NormalizedCell:
    return NormalizedCell(ResultKind.NO_CHANGE, cell.provenance)


def _supplemental_result(
    offense: TeamChart,
    base: PriorityResult,
    play: Play,
    dice: DiceSource,
    trace: list[LookupTrace | AdvancedDefenseTrace | RazzleDazzleTrace],
) -> PriorityResult:
    """Resolve any B/QR/QT chain while retaining the original defense only for ADD."""
    result = base
    rerolls = 0
    while (column := _supplemental_column(result.kind)) is not None:
        rerolls += 1
        if rerolls > MAX_SUPPLEMENTAL_REROLLS:
            raise ChartResolutionError(
                "supplemental chart exceeded "
                f"{MAX_SUPPLEMENTAL_REROLLS} consecutive B/QR/QT rerolls; chart is invalid"
            )
        roll = dice.offensive()
        cell = next(
            record.cell
            for record in offense.supplemental
            if record.column is column and record.roll == roll.total
        )
        trace.append(
            LookupTrace(
                f"supplemental:{column.value}",
                offense.name,
                offense.season,
                play,
                None,
                roll,
                cell,
            )
        )
        defense = result.defense if result.source is Source.BOTH else _blank_like(result.defense)
        result = resolve_cells(cell, defense)
    return result


def _variable_result(
    result: PriorityResult,
    offense: TeamChart,
    defense: TeamChart,
    play: Play,
    dice: DiceSource,
    trace: list[LookupTrace | AdvancedDefenseTrace | RazzleDazzleTrace],
) -> PriorityResult:
    """Materialize only distances selected by priority, retaining original chart facts."""
    operation = result.operation
    if operation in {Operation.PENALTY, Operation.INCOMPLETE, Operation.FUMBLE_END_ZONE}:
        return result
    use_offense = operation in {
        Operation.OFFENSE,
        Operation.ADD,
        Operation.INTERCEPTION_MIN,
        Operation.FUMBLE_MIN,
    }
    use_defense = operation in {
        Operation.DEFENSE,
        Operation.ADD,
        Operation.INTERCEPTION_MIN,
        Operation.FUMBLE_MIN,
        Operation.FUMBLE_DEFENSE,
    }
    cells = [result.offense, result.defense]
    changed = False
    for index, (needed, chart) in enumerate(((use_offense, offense), (use_defense, defense))):
        cell = cells[index]
        if not needed or cell.variable is None:
            continue
        distance, rolls = roll_variable(cell.variable, cell.variable_multiplier, dice)
        trace.extend(
            LookupTrace(
                "variable:" + ("offense" if index == 0 else "defense"),
                chart.name,
                chart.season,
                play,
                None,
                roll,
                cell,
            )
            for roll in rolls
        )
        cells[index] = replace(
            cell,
            kind=ResultKind.YARDS if cell.kind in _VARIABLES else cell.kind,
            yards=distance,
            variable=None,
            variable_multiplier=None,
        )
        changed = True
    if not changed:
        return result
    resolved = resolve_cells(*cells)
    return replace(
        resolved,
        offense=result.offense,
        defense=result.defense,
        offense_category=result.offense_category,
        defense_category=result.defense_category,
    )


def resolve_play(
    offense: TeamChart, defense: TeamChart, play: Play, formation: Defense, dice: DiceSource
) -> PlayResolution:
    """Resolve ordinary lookup plus mandatory B/QR/QT and SOP/BLP rerolls.

    Initial lookup always consumes offense then defense dice. B/QR/QT consume one or
    more offensive supplemental rolls. SOP/BLP consumes one offensive reroll under
    Play 7/8 after nullifying the original defense. No state, penalty, variable
    yardage, or turnover procedure is executed here.
    """
    if not isinstance(offense, TeamChart) or not isinstance(defense, TeamChart):
        raise TypeError("ordinary lookup requires two TeamChart instances")
    if type(play) is not Play or type(formation) is not Defense:
        raise TypeError("play and formation must be Play and Defense members")
    off_roll = dice.offensive()
    def_roll = dice.defensive()
    off_cell = next(
        record.cell
        for record in offense.offense
        if record.play is play and record.roll == off_roll.total
    )
    def_cell = next(
        record.cell
        for record in defense.defense
        if record.play is play and record.defense is formation and record.roll == def_roll.total
    )
    result = resolve_cells(off_cell, def_cell)
    trace = [
        LookupTrace("offense", offense.name, offense.season, play, None, off_roll, off_cell),
        LookupTrace("defense", defense.name, defense.season, play, formation, def_roll, def_cell),
    ]
    resolved_play = play
    if result.operation is Operation.OPTION:
        resolved_play = Play.SEVEN if result.kind is ResultKind.SPRINT_OUT_PASS else Play.EIGHT
        option_roll = dice.offensive()
        option_cell = next(
            record.cell
            for record in offense.offense
            if record.play is resolved_play and record.roll == option_roll.total
        )
        trace.append(
            LookupTrace(
                "option",
                offense.name,
                offense.season,
                resolved_play,
                None,
                option_roll,
                option_cell,
            )
        )
        result = resolve_cells(option_cell, _blank_like(def_cell))
    result = _supplemental_result(offense, result, resolved_play, dice, trace)
    result = _variable_result(result, offense, defense, resolved_play, dice, trace)
    return PlayResolution(play, resolved_play, result, tuple(trace))
