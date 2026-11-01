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
from .return_recovery import (
    END_LINE,
    GOAL_LINE,
    MAX_END_ZONE_DEPTH,
    MAX_FIELD_SPOT,
    TOUCHBACK_SPOT,
    ReturnOrigin,
    ReturnStart,
    resolve_recovery,
)
from .variable_yardage import roll_variable

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
    start: ReturnStart
    chart: TeamChart
    opponent: TeamChart | None
    cell: NormalizedCell
    continues_original_play: bool
    chain_depth: int
    hurried: bool
    scrimmage_start: FieldState | None = None


@dataclass(frozen=True)
class EndZoneRecovery:
    """Pending recovery choice facts for a ball recovered in the end zone."""

    possession: Possession
    depth: int

    def __post_init__(self) -> None:
        if type(self.possession) is not Possession:
            raise TypeError("possession must be Possession")
        if type(self.depth) is not int or not 0 <= self.depth <= MAX_END_ZONE_DEPTH:
            raise ValueError("end-zone recovery depth must be from zero through nine")


@dataclass(frozen=True)
class ReturnPenaltyFacts:
    """Numeric return endpoint and all assessed fouls awaiting a decision."""

    start: ReturnStart
    yards: int
    penalties: tuple[AssessedPenalty, ...]
    continues_original_play: bool
    scrimmage_start: FieldState | None

    def __post_init__(self) -> None:
        if type(self.start) is not ReturnStart:
            raise TypeError("return penalty start must be ReturnStart")
        if type(self.yards) is not int:
            raise TypeError("return penalty endpoint must be an integer")
        if type(self.penalties) is not tuple or not self.penalties:
            raise ValueError("return penalty facts require assessed penalties")
        if any(type(penalty) is not AssessedPenalty for penalty in self.penalties):
            raise TypeError("return penalties must be AssessedPenalty values")
        if type(self.continues_original_play) is not bool:
            raise TypeError("continues_original_play must be a boolean")
        if self.scrimmage_start is not None and type(self.scrimmage_start) is not FieldState:
            raise TypeError("scrimmage_start must be FieldState or None")


@dataclass(frozen=True)
class TurnoverResolution:
    """Resolved field state, score delta (home, away), and observed turnover rolls."""

    outcome: TurnoverOutcome
    state: FieldState | None
    trace: tuple[TurnoverTrace, ...]
    points: tuple[int, int] = (0, 0)
    end_zone: EndZoneResult | None = None
    return_facts: ReturnPenaltyFacts | None = None
    end_zone_recovery: EndZoneRecovery | None = None
    continuation: ReturnContinuation | None = None


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
            end_zone_recovery=EndZoneRecovery(
                defender, min(-interception_spot, MAX_END_ZONE_DEPTH)
            ),
        )
    if interception_spot >= END_LINE:
        return _safety(state.possession)
    if interception_spot >= GOAL_LINE:
        return _score(TurnoverOutcome.DEFENSIVE_TOUCHDOWN, defender)
    return _return_from_spot(
        _return_start(start_drive(defender, GOAL_LINE - interception_spot)),
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
    hurried: bool = False,
    new_series: bool = False,
) -> TurnoverResolution:
    """Resolve a recovery; return fumbles retain a new series, not a snap down."""
    return _resolve_fumble(
        state,
        location=location,
        fumbler=fumbler,
        opponent=opponent,
        dice=dice,
        chain_depth=0,
        hurried=hurried,
        new_series=new_series,
    )


def _resolve_fumble(
    state: FieldState,
    *,
    location: int,
    fumbler: TeamChart,
    opponent: TeamChart,
    dice: DiceSource,
    chain_depth: int,
    hurried: bool,
    new_series: bool,
) -> TurnoverResolution:
    """Resolve a fumble with private recursion state for chained return fumbles."""
    if type(new_series) is not bool:
        raise TypeError("new_series must be a boolean")
    _validate_turnover_inputs(state, location, fumbler, dice)
    if not isinstance(opponent, TeamChart):
        raise TypeError("opponent must be a TeamChart")
    if type(chain_depth) is not int or not 0 <= chain_depth <= MAX_TURNOVER_CHAIN:
        raise ValueError("turnover return-fumble chain depth is invalid")
    if chain_depth >= MAX_TURNOVER_CHAIN:
        raise ValueError("turnover return-fumble limit exceeded; inspect the chart")

    recovery = resolve_recovery(
        ReturnOrigin(state.yards_to_goal), location, fumbler.recovery_range, dice
    )
    if recovery.safety:
        return _safety(state.possession)
    depth_trace: tuple[TurnoverTrace, ...] = ()
    if recovery.depth_roll is not None:
        depth_trace = (TurnoverTrace("end_zone_depth", fumbler.name, recovery.depth_roll),)
    recovery_roll = recovery.recovery_roll
    assert recovery_roll is not None and recovery.retained is not None
    spot = recovery.spot
    recovered_by_fumbler = recovery.retained
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
            end_zone_recovery=EndZoneRecovery(state.possession.other, -spot),
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
            _return_start(continuation),
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
            chain_depth=chain_depth,
            hurried=hurried,
        )

    recovered_state = start_drive(state.possession.other, GOAL_LINE - spot)
    if not return_allowed:
        return TurnoverResolution(TurnoverOutcome.DEFENSIVE_RECOVERY, recovered_state, trace)
    return _return_from_spot(
        _return_start(recovered_state),
        recovery_team,
        dice,
        outcome=TurnoverOutcome.DEFENSIVE_RECOVERY,
        opponent=fumbler,
        base_trace=trace,
        chain_depth=chain_depth,
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
    if type(end_zone_depth) is not int or not 0 <= end_zone_depth <= MAX_END_ZONE_DEPTH:
        raise ValueError("end-zone recovery depth must be from zero through nine")
    # FieldState describes scrimmage spots only; ReturnStart retains the live return spot.
    result = _return_from_spot(
        ReturnStart(
            start_drive(possession, MAX_FIELD_SPOT),
            ReturnOrigin(GOAL_LINE + end_zone_depth),
        ),
        recovery_team,
        dice,
        outcome=TurnoverOutcome.DEFENSIVE_RECOVERY,
        opponent=opponent,
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
    start: ReturnStart,
    chart: TeamChart,
    dice: DiceSource,
    *,
    outcome: TurnoverOutcome,
    opponent: TeamChart | None,
    base_trace: tuple[TurnoverTrace, ...] = (),
    continues_original_play: bool = False,
    chain_depth: int = 0,
    hurried: bool = False,
    scrimmage_start: FieldState | None = None,
) -> TurnoverResolution:
    state = start.state
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
            if chain_depth >= MAX_TURNOVER_CHAIN:
                raise ValueError("turnover return-fumble limit exceeded; inspect the chart")
            return _return_from_spot(
                start,
                chart,
                dice,
                outcome=outcome,
                opponent=opponent,
                base_trace=tuple(trace),
                continues_original_play=continues_original_play,
                chain_depth=chain_depth + 1,
                hurried=hurried,
                scrimmage_start=scrimmage_start,
            )
    else:
        raise ValueError("return penalty reroll limit exceeded; inspect the chart")
    continuation = ReturnContinuation(
        start,
        chart,
        opponent,
        cell,
        continues_original_play,
        chain_depth,
        hurried,
        scrimmage_start,
    )
    if penalties and cell.kind is ResultKind.FUMBLE:
        resolved = TurnoverResolution(outcome, state, tuple(trace), continuation=continuation)
    else:
        resolved = _resolve_return_cell(continuation, outcome, tuple(trace), dice)
    if not penalties:
        return resolved
    distance = (
        start.origin.yards_to_goal
        if cell.kind is ResultKind.TOUCHDOWN
        else 0
        if cell.kind is ResultKind.NO_CHANGE
        else cell.yards
    )
    if type(distance) is not int:
        raise ValueError("return penalty has no numeric endpoint")
    return replace(
        resolved,
        return_facts=ReturnPenaltyFacts(
            start,
            distance,
            tuple(penalties),
            continues_original_play,
            scrimmage_start,
        ),
    )


def decline_return_penalties(result: TurnoverResolution, dice: DiceSource) -> TurnoverResolution:
    """Finish a previously rolled return fumble only after its fouls are declined."""
    if result.continuation is not None:
        return _resolve_return_cell(result.continuation, result.outcome, result.trace, dice)
    return replace(result, return_facts=None)


def _resolve_return_cell(
    context: ReturnContinuation,
    outcome: TurnoverOutcome,
    trace: tuple[TurnoverTrace, ...],
    dice: DiceSource,
) -> TurnoverResolution:
    start, cell = context.start, context.cell
    state = start.state
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
            start,
            0 if cell.kind is ResultKind.NO_CHANGE else cell.yards,
            outcome,
            trace,
            continues_original_play=context.continues_original_play,
            scrimmage_start=context.scrimmage_start,
        )
    if cell.kind is ResultKind.FUMBLE:
        if context.opponent is None:
            raise ValueError("return fumble handling requires the opposing chart")
        if cell.yards is None:
            raise ValueError("return fumble is missing its location")
        chained = _resolve_fumble(
            state,
            location=cell.yards - (start.origin.yards_to_goal - state.yards_to_goal),
            fumbler=context.chart,
            opponent=context.opponent,
            dice=dice,
            chain_depth=context.chain_depth + 1,
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


def _return_start(state: FieldState) -> ReturnStart:
    """Pair an ordinary field return spot with its field-relative coordinate."""
    return ReturnStart(state, ReturnOrigin(state.yards_to_goal))


def _apply_return_yards(
    start: ReturnStart,
    yards: int,
    outcome: TurnoverOutcome,
    trace: tuple[TurnoverTrace, ...],
    *,
    continues_original_play: bool,
    scrimmage_start: FieldState | None = None,
) -> TurnoverResolution:
    state = start.state
    new_spot = start.origin.yards_to_goal - yards
    if new_spot <= 0:
        return _score(
            TurnoverOutcome.OFFENSIVE_TOUCHDOWN
            if continues_original_play
            else TurnoverOutcome.DEFENSIVE_TOUCHDOWN,
            state.possession,
            trace,
        )
    if new_spot >= END_LINE:
        return _safety(state.possession, trace)
    if new_spot >= GOAL_LINE:
        if continues_original_play or start.origin.yards_to_goal < GOAL_LINE:
            return _safety(state.possession, trace)
        return TurnoverResolution(
            TurnoverOutcome.TOUCHBACK,
            start_drive(state.possession, TOUCHBACK_SPOT),
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
