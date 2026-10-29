"""Turnover and return resolution (Basic VI-9, VI-10 and VI-13).

This module owns field-relative turnover mechanics. It consumes only rolls that the
rulebook calls for and returns structured trace facts; callers render those facts.
"""

from dataclasses import dataclass, replace
from enum import Enum

from .dice import DiceSource, OffensiveRoll
from .game_state import FieldState, Possession, apply_gain, start_drive
from .models import (
    NormalizedCell,
    ResultKind,
    SpecialTeamsColumn,
    TeamChart,
)
from .penalty_yardage import AssessedPenalty, assess_penalty
from .variable_yardage import roll_variable

GOAL_LINE = 100
END_LINE = 110
MAX_TURNOVER_CHAIN = 100


class TurnoverOutcome(str, Enum):
    """Terminal or possession results of one turnover sequence."""

    OFFENSIVE_RECOVERY = "offensive_recovery"
    DEFENSIVE_RECOVERY = "defensive_recovery"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    DECLINED_INTERCEPTION = "declined_interception"
    DEFENSIVE_TOUCHDOWN = "defensive_touchdown"
    OFFENSIVE_TOUCHDOWN = "offensive_touchdown"
    TOUCHBACK = "touchback"
    SAFETY = "safety"
    END_ZONE_RETURN_PENDING = "end_zone_return_pending"


class EndZoneResult(str, Enum):
    """End-zone result that must be visible separately from ordinary possession."""

    TOUCHDOWN = "touchdown"
    TOUCHBACK = "touchback"
    SAFETY = "safety"


@dataclass(frozen=True)
class TurnoverTrace:
    """One real offensive roll consulted during a turnover sequence."""

    section: str
    team_name: str
    roll: OffensiveRoll
    cell: NormalizedCell | None = None


@dataclass(frozen=True)
class TurnoverLocation:
    """A fixed turnover location and every roll needed to resolve it."""

    location: int
    trace: tuple[TurnoverTrace, ...]


@dataclass(frozen=True)
class ReturnContinuation:
    state: FieldState
    chart: TeamChart
    opponent: TeamChart | None
    cell: NormalizedCell
    continues_original_play: bool
    depth: int
    hurried: bool
    origin: int | None = None
    scrimmage_start: FieldState | None = None


@dataclass(frozen=True)
class TurnoverResolution:
    """Resolved field state, score delta (home, away), and observed turnover rolls."""

    outcome: TurnoverOutcome
    state: FieldState | None
    trace: tuple[TurnoverTrace, ...]
    points: tuple[int, int] = (0, 0)
    end_zone: EndZoneResult | None = None
    return_penalty: AssessedPenalty | None = None
    return_start: FieldState | None = None
    return_yards: int | None = None
    end_zone_recovery: bool = False
    return_penalties: tuple[AssessedPenalty, ...] = ()
    continuation: ReturnContinuation | None = None
    recovery_possession: Possession | None = None
    end_zone_depth: int = 0
    return_origin: int | None = None
    continues_original_play: bool = False
    scrimmage_start: FieldState | None = None


def resolve_interception(
    state: FieldState,
    *,
    location: int,
    interceptor: TeamChart,
    choice: str,
    dice: DiceSource,
    opponent: TeamChart | None = None,
    hurried: bool = False,
) -> TurnoverResolution:
    """Resolve an interception after the defender chooses a return or incompletion."""
    _validate_turnover_inputs(state, location, interceptor, dice)
    if choice not in {"decline", "return"}:
        raise ValueError("interception choice must be 'decline' or 'return'")
    if choice == "decline":
        transition = apply_gain(state, 0)
        return TurnoverResolution(TurnoverOutcome.DECLINED_INTERCEPTION, transition.state, ())

    interception_spot = state.yards_to_goal - location
    defender = state.possession.other
    if interception_spot <= 0:
        return TurnoverResolution(
            TurnoverOutcome.END_ZONE_RETURN_PENDING,
            None,
            (),
            end_zone=EndZoneResult.TOUCHBACK,
            end_zone_recovery=True,
            recovery_possession=defender,
            end_zone_depth=min(-interception_spot, 9),
        )
    if interception_spot >= END_LINE:
        return _safety(state.possession)
    if interception_spot >= GOAL_LINE:
        return _score(TurnoverOutcome.DEFENSIVE_TOUCHDOWN, defender)
    return _return_from_spot(
        start_drive(defender, GOAL_LINE - interception_spot),
        interceptor,
        dice,
        outcome=TurnoverOutcome.DEFENSIVE_RECOVERY,
        opponent=opponent,
        hurried=hurried,
    )


def resolve_fumble(
    state: FieldState,
    *,
    location: int,
    fumbler: TeamChart,
    opponent: TeamChart,
    dice: DiceSource,
    _depth: int = 0,
    hurried: bool = False,
    new_series: bool = False,
) -> TurnoverResolution:
    """Resolve a recovery; return fumbles retain a new series, not a snap down."""
    if type(new_series) is not bool:
        raise TypeError("new_series must be a boolean")
    _validate_turnover_inputs(state, location, fumbler, dice)
    if not isinstance(opponent, TeamChart):
        raise TypeError("opponent must be a TeamChart")
    if _depth >= MAX_TURNOVER_CHAIN:
        raise ValueError("turnover return-fumble limit exceeded; inspect the chart")

    spot = state.yards_to_goal - location
    if spot >= END_LINE:
        return _safety(state.possession)
    depth_trace: tuple[TurnoverTrace, ...] = ()
    if spot <= -10:
        depth_roll = dice.offensive()
        spot = -(depth_roll.white_one + depth_roll.white_two)
        depth_trace = (TurnoverTrace("end_zone_depth", fumbler.name, depth_roll),)
    recovery_roll = dice.offensive()
    recovered_by_fumbler = recovery_roll.total in fumbler.recovery_range
    recovery_team = fumbler if recovered_by_fumbler else opponent
    trace = (*depth_trace, TurnoverTrace("fumble_recovery", fumbler.name, recovery_roll))

    if spot <= 0:
        if recovered_by_fumbler:
            return _score(
                TurnoverOutcome.DEFENSIVE_TOUCHDOWN
                if new_series
                else TurnoverOutcome.OFFENSIVE_TOUCHDOWN,
                state.possession,
                trace,
            )
        return TurnoverResolution(
            TurnoverOutcome.END_ZONE_RETURN_PENDING,
            None,
            trace,
            end_zone=EndZoneResult.TOUCHBACK,
            end_zone_recovery=True,
            recovery_possession=state.possession.other,
            end_zone_depth=-spot,
        )
    if spot >= GOAL_LINE:
        return (
            _safety(state.possession, trace)
            if recovered_by_fumbler
            else _score(TurnoverOutcome.DEFENSIVE_TOUCHDOWN, state.possession.other, trace)
        )

    return_allowed = (recovered_by_fumbler and recovery_roll.total in {17, 18, 19}) or (
        not recovered_by_fumbler and recovery_roll.total in {37, 38, 39}
    )
    if recovered_by_fumbler:
        if not return_allowed:
            if new_series:
                return TurnoverResolution(
                    TurnoverOutcome.DEFENSIVE_RECOVERY, start_drive(state.possession, spot), trace
                )
            transition = apply_gain(state, location)
            outcome = (
                TurnoverOutcome.TURNOVER_ON_DOWNS
                if transition.state.possession is not state.possession
                else TurnoverOutcome.OFFENSIVE_RECOVERY
            )
            return TurnoverResolution(outcome, transition.state, trace)
        continuation = (
            start_drive(state.possession, spot)
            if new_series
            else _state_at_own_fumble(state, spot, location)
        )
        return _return_from_spot(
            continuation,
            recovery_team,
            dice,
            outcome=(
                TurnoverOutcome.DEFENSIVE_RECOVERY
                if new_series
                else TurnoverOutcome.OFFENSIVE_RECOVERY
            ),
            opponent=opponent,
            base_trace=trace,
            continues_original_play=not new_series,
            scrimmage_start=None if new_series else state,
            _depth=_depth,
            hurried=hurried,
        )

    recovered_state = start_drive(state.possession.other, GOAL_LINE - spot)
    if not return_allowed:
        return TurnoverResolution(TurnoverOutcome.DEFENSIVE_RECOVERY, recovered_state, trace)
    return _return_from_spot(
        recovered_state,
        recovery_team,
        dice,
        outcome=TurnoverOutcome.DEFENSIVE_RECOVERY,
        opponent=fumbler,
        base_trace=trace,
        _depth=_depth,
        hurried=hurried,
    )


def resolve_end_zone_recovery_return(
    recovery_team: TeamChart,
    opponent: TeamChart,
    possession: Possession,
    dice: DiceSource,
    *,
    end_zone_depth: int = 0,
    hurried: bool = False,
) -> TurnoverResolution:
    """Return from the actual end-zone spot using the ordinary return procedure."""
    if type(end_zone_depth) is not int or not 0 <= end_zone_depth <= 9:
        raise ValueError("end-zone recovery depth must be from zero through nine")
    # FieldState describes scrimmage spots only; origin retains the live return spot.
    result = _return_from_spot(
        start_drive(possession, 99),
        recovery_team,
        dice,
        outcome=TurnoverOutcome.DEFENSIVE_RECOVERY,
        opponent=opponent,
        origin=GOAL_LINE + end_zone_depth,
        hurried=hurried,
    )
    return replace(
        result,
        trace=tuple(
            replace(entry, section="end_zone_recovery_return")
            if entry.section == "turnover_return"
            else entry
            for entry in result.trace
        ),
    )


def _return_from_spot(
    state: FieldState,
    chart: TeamChart,
    dice: DiceSource,
    *,
    outcome: TurnoverOutcome,
    opponent: TeamChart | None,
    base_trace: tuple[TurnoverTrace, ...] = (),
    continues_original_play: bool = False,
    _depth: int = 0,
    hurried: bool = False,
    origin: int | None = None,
    scrimmage_start: FieldState | None = None,
) -> TurnoverResolution:
    trace = list(base_trace)
    penalties: list[AssessedPenalty] = []
    for index in range(MAX_TURNOVER_CHAIN):
        roll = dice.offensive()
        cell = _return_cell(chart, roll)
        trace.append(
            TurnoverTrace(
                "turnover_return" if index == 0 else "turnover_return_reroll",
                chart.name,
                roll,
                cell,
            )
        )
        if cell.kind is not ResultKind.PENALTY:
            break
        if cell.penalty is None:
            raise ValueError("return penalty is missing penalty data")
        penalty = assess_penalty(cell.penalty, dice, hurried=hurried)
        for assessment in ((penalty.roll,) if penalty.roll else ()) + penalty.distance_rolls:
            trace.append(TurnoverTrace("return_penalty_yardage", chart.name, assessment, cell))
        if not penalty.no_foul:
            penalties.append(penalty)
        if len({p.source.team for p in penalties}) > 1:
            # Offsetting return fouls cancel this return attempt, not the interception.
            if _depth >= MAX_TURNOVER_CHAIN:
                raise ValueError("turnover return-fumble limit exceeded; inspect the chart")
            return _return_from_spot(
                state,
                chart,
                dice,
                outcome=outcome,
                opponent=opponent,
                base_trace=tuple(trace),
                continues_original_play=continues_original_play,
                _depth=_depth + 1,
                hurried=hurried,
                origin=origin,
                scrimmage_start=scrimmage_start,
            )
    else:
        raise ValueError("return penalty reroll limit exceeded; inspect the chart")
    continuation = ReturnContinuation(
        state,
        chart,
        opponent,
        cell,
        continues_original_play,
        _depth,
        hurried,
        origin,
        scrimmage_start,
    )
    if penalties and cell.kind is ResultKind.FUMBLE:
        resolved = TurnoverResolution(outcome, state, tuple(trace), continuation=continuation)
    else:
        resolved = _resolve_return_cell(continuation, outcome, tuple(trace), dice)
    if not penalties:
        return resolved
    distance = (
        (origin if origin is not None else state.yards_to_goal)
        if cell.kind is ResultKind.TOUCHDOWN
        else 0
        if cell.kind is ResultKind.NO_CHANGE
        else cell.yards
    )
    return replace(
        resolved,
        return_penalty=penalties[0],
        return_penalties=tuple(penalties),
        return_start=state,
        return_yards=distance,
        return_origin=origin,
        continues_original_play=continues_original_play,
        scrimmage_start=scrimmage_start,
    )


def decline_return_penalties(result: TurnoverResolution, dice: DiceSource) -> TurnoverResolution:
    """Finish a previously rolled return fumble only after its fouls are declined."""
    if result.continuation is not None:
        return _resolve_return_cell(result.continuation, result.outcome, result.trace, dice)
    return replace(result, return_penalty=None, return_penalties=())


def _resolve_return_cell(
    context: ReturnContinuation,
    outcome: TurnoverOutcome,
    trace: tuple[TurnoverTrace, ...],
    dice: DiceSource,
) -> TurnoverResolution:
    state, cell = context.state, context.cell
    if cell.kind is ResultKind.TOUCHDOWN:
        return _score(
            TurnoverOutcome.OFFENSIVE_TOUCHDOWN
            if context.continues_original_play
            else TurnoverOutcome.DEFENSIVE_TOUCHDOWN,
            state.possession,
            trace,
        )
    if cell.kind is ResultKind.NO_CHANGE or (
        cell.kind is ResultKind.YARDS and cell.yards is not None
    ):
        return _apply_return_yards(
            state,
            0 if cell.kind is ResultKind.NO_CHANGE else cell.yards,
            outcome,
            trace,
            continues_original_play=context.continues_original_play,
            origin=context.origin,
            scrimmage_start=context.scrimmage_start,
        )
    if cell.kind is ResultKind.FUMBLE:
        if context.opponent is None:
            raise ValueError("return fumble handling requires the opposing chart")
        if cell.yards is None:
            raise ValueError("return fumble is missing its location")
        chained = resolve_fumble(
            state,
            location=cell.yards - ((context.origin or state.yards_to_goal) - state.yards_to_goal),
            fumbler=context.chart,
            opponent=context.opponent,
            dice=dice,
            _depth=context.depth + 1,
            hurried=context.hurried,
            new_series=not context.continues_original_play,
        )
        return replace(chained, trace=(*trace, *chained.trace))
    raise ValueError(f"unsupported interception-return result: {cell.kind.value}")


def resolve_turnover_location(
    cell: NormalizedCell, chart: TeamChart, dice: DiceSource
) -> TurnoverLocation:
    """Resolve a fixed or DS/X/T turnover location without hiding its rolls."""
    if cell.kind not in {ResultKind.FUMBLE, ResultKind.INTERCEPTION}:
        raise ValueError("turnover location needs a fumble or interception cell")
    if not isinstance(chart, TeamChart):
        raise TypeError("chart must be a TeamChart")
    if cell.yards is not None:
        return TurnoverLocation(cell.yards, ())
    if cell.variable is None or cell.variable_multiplier is None:
        raise ValueError("turnover cell is missing a location")
    distance, rolls = roll_variable(cell.variable, cell.variable_multiplier, dice)
    trace = tuple(TurnoverTrace("turnover_location", chart.name, roll, cell) for roll in rolls)
    return TurnoverLocation(distance, trace)


def _return_cell(chart: TeamChart, roll: OffensiveRoll) -> NormalizedCell:
    return next(
        record.cell
        for record in chart.special_teams
        if record.column is SpecialTeamsColumn.INTERCEPTION_RETURN and record.roll == roll.total
    )


def _apply_return_yards(
    state: FieldState,
    yards: int,
    outcome: TurnoverOutcome,
    trace: tuple[TurnoverTrace, ...],
    *,
    continues_original_play: bool,
    origin: int | None = None,
    scrimmage_start: FieldState | None = None,
) -> TurnoverResolution:
    new_spot = (origin if origin is not None else state.yards_to_goal) - yards
    if new_spot <= 0:
        return _score(
            TurnoverOutcome.OFFENSIVE_TOUCHDOWN
            if continues_original_play
            else TurnoverOutcome.DEFENSIVE_TOUCHDOWN,
            state.possession,
            trace,
        )
    if new_spot >= GOAL_LINE:
        if continues_original_play or origin is None:
            return _safety(state.possession, trace)
        return TurnoverResolution(
            TurnoverOutcome.TOUCHBACK,
            start_drive(state.possession, 80),
            trace,
            end_zone=EndZoneResult.TOUCHBACK,
        )
    if continues_original_play:
        original = scrimmage_start or state
        transition = apply_gain(original, original.yards_to_goal - new_spot)
        if transition.state.possession is not original.possession:
            outcome = TurnoverOutcome.TURNOVER_ON_DOWNS
        return TurnoverResolution(outcome, transition.state, trace)
    return TurnoverResolution(outcome, start_drive(state.possession, new_spot), trace)


def _score(
    outcome: TurnoverOutcome,
    scorer: Possession,
    trace: tuple[TurnoverTrace, ...] = (),
) -> TurnoverResolution:
    points = (6, 0) if scorer is Possession.HOME else (0, 6)
    return TurnoverResolution(outcome, None, trace, points, EndZoneResult.TOUCHDOWN)


def _safety(victim: Possession, trace: tuple[TurnoverTrace, ...] = ()) -> TurnoverResolution:
    points = (0, 2) if victim is Possession.HOME else (2, 0)
    return TurnoverResolution(TurnoverOutcome.SAFETY, None, trace, points, EndZoneResult.SAFETY)


def _state_at_own_fumble(state: FieldState, spot: int, location: int) -> FieldState:
    """Represent the live-ball spot without consuming the down a second time."""
    if location >= state.yards_to_go:
        return start_drive(state.possession, spot)
    return FieldState(state.possession, spot, state.down, min(state.yards_to_go - location, spot))


def _validate_turnover_inputs(
    state: FieldState, location: int, chart: TeamChart, dice: DiceSource
) -> None:
    if not isinstance(state, FieldState):
        raise TypeError("state must be a FieldState")
    if type(location) is not int:
        raise TypeError("location must be an integer")
    if not isinstance(chart, TeamChart):
        raise TypeError("chart must be a TeamChart")
    if not callable(getattr(dice, "offensive", None)):
        raise TypeError("dice must provide an offensive() method")
