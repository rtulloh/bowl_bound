"""Basic kick procedures and engine-owned choices (Basic V-4, VI-4–6, VI-10–13)."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum

from .dice import DiceSource, OffensiveRoll
from .game_state import FieldState, Possession, apply_gain, start_drive
from .models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyTeam,
    ResultKind,
    SpecialTeamsColumn,
    TeamChart,
)
from .penalty_yardage import AssessedPenalty, assess_penalty, enforce_penalty
from .variable_yardage import roll_variable

MIN_SUPPORTED_SEASON = 1940
MAX_SUPPORTED_SEASON = 2023
MAX_KICK_CHAIN = 100


class SpecialTeamsOutcome(str, Enum):
    """Engine result labels for kick procedures."""

    KICKOFF_RETURN = "kickoff_return"
    TOUCHBACK = "touchback"
    FIELD_GOAL_GOOD = "field_goal_good"
    FIELD_GOAL_MISSED = "field_goal_missed"
    PUNT_RETURN = "punt_return"
    PUNT_FAIR_CATCH = "punt_fair_catch"
    PUNT_DEAD = "punt_dead"
    RETURN_TOUCHDOWN = "return_touchdown"
    SAFETY = "safety"
    RECOVERY = "kick_recovery"
    PENALTY = "kick_penalty_accepted"
    REPLAY = "kick_replay"
    PENDING = "special_teams_pending"


@dataclass(frozen=True)
class SpecialTeamsTrace:
    """A real roll and the semantic chart fact it consulted."""

    section: str
    team_name: str
    roll: OffensiveRoll
    cell: NormalizedCell | None


@dataclass(frozen=True)
class KickChoice:
    """One enabled decision provided by the engine."""

    id: str
    label: str


@dataclass(frozen=True)
class SpecialTeamsResolution:
    """Immutable result or pending decision; points remain uncommitted while pending."""

    outcome: SpecialTeamsOutcome
    state: FieldState | None
    trace: tuple[SpecialTeamsTrace, ...]
    points: tuple[int, int] = (0, 0)
    chooser: Possession | None = None
    choices: tuple[KickChoice, ...] = ()


def kickoff_spot(home_season: int) -> int:
    """Select the kicking team's own-yard-line spot from the designated home season."""
    _validate_season(home_season)
    if home_season <= 1985:
        return 40
    if home_season <= 2006:
        return 35
    return 30 if home_season <= 2011 else 35


def free_kick_touchback_spot(home_season: int) -> int:
    """Free-kick touchbacks changed from the own 20 to the own 25 in 2012."""
    _validate_season(home_season)
    return 20 if home_season <= 2011 else 25


class SpecialTeamsPlay:
    """An isolated kick procedure; no session state changes until its result is final.

    Pending handlers retain the rolled kick, so choosing a return never rerolls it.
    The engine owns all choices, chart interpretation, scoring, and enforcement.
    """

    def __init__(
        self,
        action: str,
        state: FieldState,
        kicking: TeamChart,
        receiving: TeamChart,
        dice: DiceSource,
        *,
        home_season: int,
        safety_free_kick: bool = False,
        hurried: bool = False,
    ) -> None:
        if action not in {"kickoff", "punt", "field_goal"}:
            raise ValueError("kick action must be kickoff, punt, or field_goal")
        if not isinstance(state, FieldState):
            raise TypeError("kick needs a FieldState")
        if not isinstance(kicking, TeamChart) or not isinstance(receiving, TeamChart):
            raise TypeError("kick needs two TeamChart instances")
        if type(safety_free_kick) is not bool:
            raise TypeError("safety_free_kick must be a bool")
        if safety_free_kick and action == "field_goal":
            raise ValueError("a safety free kick cannot be a field goal")
        if action == "kickoff" or safety_free_kick:
            _validate_season(home_season)
        self.action = action
        self.charts = {state.possession: kicking, state.possession.other: receiving}
        self.dice = dice
        self.season = home_season
        self.free_kick = action == "kickoff" or safety_free_kick
        self.hurried = hurried
        self.no_elapsed_time = False
        self.extends_quarter = False
        if self.free_kick:
            own_spot = 20 if safety_free_kick else kickoff_spot(home_season)
            state = start_drive(state.possession, 100 - own_spot)
        self.start = state
        self.chain_depth = 0
        self.trace: list[SpecialTeamsTrace] = []
        self.handlers: dict[str, Callable[[], SpecialTeamsResolution]] = {}
        self.result: SpecialTeamsResolution | None = None
        self.descriptions: list[str] = []

    def begin(self) -> SpecialTeamsResolution:
        """Roll the announced kick once; starting the same procedure twice is refused."""
        if self.result is not None:
            raise ValueError("kick procedure has already started")
        column = SpecialTeamsColumn(self.action)
        self.result = self._column(
            self.start, column, lambda cell: self._kick(cell), is_return=False
        )
        return self.result

    def decide(self, choice: str) -> SpecialTeamsResolution:
        """Apply exactly one current legal choice without repeating prior dice."""
        if choice not in self.handlers:
            raise ValueError("unknown or stale special-teams decision")
        handler = self.handlers[choice]
        self.handlers = {}
        self.result = handler()
        return self.result

    def _finish(
        self,
        outcome: SpecialTeamsOutcome,
        state: FieldState | None,
        points: tuple[int, int] = (0, 0),
    ) -> SpecialTeamsResolution:
        return SpecialTeamsResolution(outcome, state, tuple(self.trace), points)

    def _choice(
        self,
        chooser: Possession,
        alternatives: list[tuple[str, str, Callable[[], SpecialTeamsResolution]]],
    ) -> SpecialTeamsResolution:
        self.handlers = {key: handler for key, _, handler in alternatives}
        return SpecialTeamsResolution(
            SpecialTeamsOutcome.PENDING,
            self.start,
            tuple(self.trace),
            chooser=chooser,
            choices=tuple(KickChoice(key, label) for key, label, _ in alternatives),
        )

    def _roll(self, possession: Possession, column: SpecialTeamsColumn) -> NormalizedCell:
        chart = self.charts[possession]
        roll = self.dice.offensive()
        cell = next(
            record.cell
            for record in chart.special_teams
            if record.column is column and record.roll == roll.total
        )
        self.trace.append(SpecialTeamsTrace(column.value, chart.name, roll, cell))
        return cell

    def _column(
        self,
        state: FieldState,
        column: SpecialTeamsColumn,
        continuation: Callable[[NormalizedCell], SpecialTeamsResolution],
        *,
        is_return: bool,
        return_origin: int | None = None,
    ) -> SpecialTeamsResolution:
        penalties: list[AssessedPenalty] = []
        for _ in range(MAX_KICK_CHAIN):
            cell = self._roll(state.possession, column)
            if cell.kind is not ResultKind.PENALTY:
                break
            assert cell.penalty is not None
            penalty = assess_penalty(cell.penalty, self.dice, hurried=self.hurried)
            for roll in (
                (penalty.roll,) if penalty.roll is not None else ()
            ) + penalty.distance_rolls:
                self.trace.append(
                    SpecialTeamsTrace(
                        "kick_penalty_yardage", self.charts[state.possession].name, roll, cell
                    )
                )
            if penalty.no_foul:
                continue
            if penalty.bad_snap:
                return self._recovery(state, -13 if self.action == "punt" else -7)
            if penalty.no_elapsed_time:
                self.no_elapsed_time = True
                return self._finish(SpecialTeamsOutcome.PENALTY, enforce_penalty(state, penalty))
            if (
                self.action == "kickoff"
                and not is_return
                and penalty.source.team is PenaltyTeam.OFFENSE
                and penalty.source.code is PenaltyCode.S
                and penalty.roll is not None
                and penalty.roll.total <= 32
            ):
                return self._choice(
                    state.possession.other,
                    [
                        (
                            "kick:out_of_bounds:spot",
                            "Take possession at own 35",
                            lambda: self._finish(
                                SpecialTeamsOutcome.PENALTY, start_drive(state.possession.other, 65)
                            ),
                        ),
                        (
                            "kick:out_of_bounds:rekick",
                            "Require a re-kick after five yards",
                            lambda p=penalty: self._restart(enforce_penalty(state, p)),
                        ),
                    ],
                )
            if penalty.pre_snap and not is_return:
                return self._finish(SpecialTeamsOutcome.PENALTY, enforce_penalty(state, penalty))
            penalties.append(penalty)
        else:
            raise ValueError("kick penalty reroll limit exceeded")
        if len({p.source.team for p in penalties}) > 1:
            if self.free_kick:
                return self._restart(self.start)
            self.extends_quarter = True
            return self._finish(SpecialTeamsOutcome.REPLAY, self.start)
        if cell.variable is not None:
            distance = self._distance(cell, state.possession)
            kind = (
                cell.kind
                if cell.kind in {ResultKind.FUMBLE, ResultKind.BLOCKED_KICK}
                else ResultKind.YARDS
            )
            cell = replace(cell, kind=kind, yards=distance, variable=None, variable_multiplier=None)
        if not penalties:
            return continuation(cell)
        chooser = (
            state.possession.other
            if penalties[0].source.team is PenaltyTeam.OFFENSE
            else state.possession
        )
        alternatives: list[tuple[str, str, Callable[[], SpecialTeamsResolution]]] = []
        for index, penalty in enumerate(penalties):

            def handler(p: AssessedPenalty = penalty) -> SpecialTeamsResolution:
                if is_return:
                    return self._accepted_return(
                        state,
                        cell,
                        p,
                        return_origin,
                        free_touchback=self.free_kick
                        and column is not SpecialTeamsColumn.INTERCEPTION_RETURN,
                    )
                self.extends_quarter = p.source.team is PenaltyTeam.DEFENSE
                marked = enforce_penalty(state, p)
                if self.free_kick:
                    return self._restart(marked)
                return self._finish(SpecialTeamsOutcome.PENALTY, marked)

            alternatives.append(
                (f"kick:accept:{index}", f"Accept {penalty.yards}-yard penalty", handler)
            )
        alternatives.append(
            (
                "kick:decline",
                f"Decline penalties: {_penalty_result_text(cell, column, is_return=is_return)}",
                lambda: continuation(cell),
            )
        )
        return self._choice(chooser, alternatives)

    def _restart(self, state: FieldState) -> SpecialTeamsResolution:
        self.chain_depth += 1
        if self.chain_depth > MAX_KICK_CHAIN:
            raise ValueError("kick replay limit exceeded")
        self.start = state
        return self._column(state, SpecialTeamsColumn(self.action), self._kick, is_return=False)

    def _distance(self, cell: NormalizedCell, possession: Possession) -> int:
        if cell.yards is not None:
            return cell.yards
        if cell.kind is ResultKind.NO_CHANGE:
            return 0
        if cell.variable is None or cell.variable_multiplier is None:
            raise ValueError(f"kick result has no yardage: {cell.kind.value}")
        distance, rolls = roll_variable(cell.variable, cell.variable_multiplier, self.dice)
        self.trace.extend(
            SpecialTeamsTrace("kick_distance", self.charts[possession].name, r, cell) for r in rolls
        )
        return distance

    def _kick(
        self, cell: NormalizedCell, *, redirected: int = 0, no_return: bool = False
    ) -> SpecialTeamsResolution:
        if cell.kind in {ResultKind.FIELD_GOAL_REFERENCE, ResultKind.KICKOFF_REFERENCE}:
            if redirected >= MAX_KICK_CHAIN:
                raise ValueError("punt redirect limit exceeded")
            column = (
                SpecialTeamsColumn.FIELD_GOAL
                if cell.kind is ResultKind.FIELD_GOAL_REFERENCE
                else SpecialTeamsColumn.KICKOFF
            )
            return self._column(
                self.start,
                column,
                lambda redirected_cell: self._kick(
                    redirected_cell,
                    redirected=redirected + 1,
                    no_return=no_return or cell.out_of_bounds,
                ),
                is_return=False,
            )
        if cell.kind in {ResultKind.FUMBLE, ResultKind.BLOCKED_KICK}:
            return self._recovery(
                self.start,
                self._distance(cell, self.start.possession),
                blocked=cell.kind is ResultKind.BLOCKED_KICK,
                snap=not self.free_kick,
            )
        if self.action == "field_goal":
            distance = (
                None
                if cell.kind is ResultKind.NO_GOOD_FIELD_GOAL
                else self._distance(cell, self.start.possession)
            )
            range_text = "no good" if distance is None else f"chart range {distance} yards"
            self.descriptions.append(
                f"{self.charts[self.start.possession].name} field goal from "
                f"{_location(self.start.yards_to_goal)}: {range_text}."
            )
            if distance is not None and distance >= self.start.yards_to_goal:
                return self._score(self.start.possession, 3, SpecialTeamsOutcome.FIELD_GOAL_GOOD)
            spot = min(80, 100 - self.start.yards_to_goal - 7)
            if spot <= 0:
                raise ValueError("field goal hold is outside the field")
            return self._finish(
                SpecialTeamsOutcome.FIELD_GOAL_MISSED,
                start_drive(self.start.possession.other, spot),
            )
        distance = self._distance(cell, self.start.possession)
        landing = 100 - self.start.yards_to_goal + distance
        receiver = self.start.possession.other
        kicker = self.charts[self.start.possession].name
        receiving = self.charts[receiver].name
        self.descriptions.append(
            f"{kicker} {self.action} from {_location(self.start.yards_to_goal)}: "
            f"{distance} yards; lands at {receiving} {_location(landing)}."
        )
        if landing >= 110:
            return self._touchback(receiver)
        if landing >= 100 and self.action == "punt" and (no_return or cell.out_of_bounds):
            return self._touchback(receiver)
        if landing >= 100:
            return self._choice(
                receiver,
                [
                    ("kick:touchback", "Take a touchback", lambda: self._touchback(receiver)),
                    (
                        "kick:return",
                        "Return from the end zone",
                        lambda: self._return(receiver, landing),
                    ),
                ],
            )
        if not 1 <= landing <= 99:
            raise ValueError("kick landing must be within the field or receiving end zone")
        if self.action == "punt" and (no_return or cell.out_of_bounds):
            return self._finish(SpecialTeamsOutcome.PUNT_DEAD, start_drive(receiver, landing))
        if self.action == "punt":
            return self._choice(
                receiver,
                [
                    (
                        "kick:fair_catch",
                        "Fair catch the punt",
                        lambda: self._finish(
                            SpecialTeamsOutcome.PUNT_FAIR_CATCH, start_drive(receiver, landing)
                        ),
                    ),
                    ("kick:return", "Return the punt", lambda: self._return(receiver, landing)),
                ],
            )
        return self._return(receiver, landing)

    def _touchback(self, receiver: Possession) -> SpecialTeamsResolution:
        own = free_kick_touchback_spot(self.season) if self.free_kick else 20
        return self._finish(SpecialTeamsOutcome.TOUCHBACK, start_drive(receiver, 100 - own))

    def _return(self, possession: Possession, landing: int) -> SpecialTeamsResolution:
        # FieldState cannot represent an end zone; landing stays a separate live-ball fact.
        state = start_drive(possession, min(99, landing))
        column = (
            SpecialTeamsColumn.KICKOFF_RETURN
            if self.action == "kickoff"
            else SpecialTeamsColumn.PUNT_RETURN
        )
        return self._column(
            state,
            column,
            lambda cell: self._return_cell(possession, landing, cell),
            is_return=True,
            return_origin=landing,
        )

    def _return_cell(
        self,
        possession: Possession,
        landing: int,
        cell: NormalizedCell,
        *,
        snap_state: FieldState | None = None,
        miscellaneous: bool = False,
    ) -> SpecialTeamsResolution:
        if cell.kind is ResultKind.TOUCHDOWN:
            return self._score(possession, 6, SpecialTeamsOutcome.RETURN_TOUCHDOWN)
        distance = self._distance(cell, possession)
        self.descriptions.append(
            f"{self.charts[possession].name} returns {distance} yards from {_location(landing)}."
        )
        if cell.kind is ResultKind.FUMBLE:
            return self._recovery(
                start_drive(possession, min(99, landing)),
                distance,
                origin=landing,
                snap=False,
                snap_state=snap_state,
            )
        endpoint = landing - distance
        if endpoint <= 0:
            return self._score(possession, 6, SpecialTeamsOutcome.RETURN_TOUCHDOWN)
        if endpoint >= 100:
            if landing >= 100:
                return self._finish(
                    SpecialTeamsOutcome.TOUCHBACK,
                    start_drive(
                        possession,
                        100
                        - (
                            free_kick_touchback_spot(self.season)
                            if self.free_kick and not miscellaneous
                            else 20
                        ),
                    ),
                )
            return self._score(possession.other, 2, SpecialTeamsOutcome.SAFETY)
        outcome = (
            SpecialTeamsOutcome.KICKOFF_RETURN
            if self.action == "kickoff"
            else SpecialTeamsOutcome.PUNT_RETURN
        )
        if snap_state is not None:
            transition = apply_gain(snap_state, snap_state.yards_to_goal - endpoint)
            return self._finish(SpecialTeamsOutcome.RECOVERY, transition.state)
        return self._finish(outcome, start_drive(possession, endpoint))

    def _accepted_return(
        self,
        state: FieldState,
        cell: NormalizedCell,
        penalty: AssessedPenalty,
        origin: int | None = None,
        *,
        free_touchback: bool = False,
    ) -> SpecialTeamsResolution:
        start = state.yards_to_goal if origin is None else origin
        distance = (
            start if cell.kind is ResultKind.TOUCHDOWN else self._distance(cell, state.possession)
        )
        spot = start - distance
        if penalty.source.team is PenaltyTeam.OFFENSE and 2 * distance > start:
            spot = (start + 1) // 2
        if spot >= 100:
            if penalty.source.team is PenaltyTeam.DEFENSE:
                # Mark from the real end-zone coordinate, never a fabricated own-one spot.
                spot -= min(penalty.yards, spot // 2)
                if spot < 100:
                    return self._finish(
                        SpecialTeamsOutcome.PENALTY, start_drive(state.possession, spot)
                    )
            if start >= 100:
                own = free_kick_touchback_spot(self.season) if free_touchback else 20
                return self._finish(
                    SpecialTeamsOutcome.TOUCHBACK, start_drive(state.possession, 100 - own)
                )
            return self._score(state.possession.other, 2, SpecialTeamsOutcome.SAFETY)
        spot = max(1, spot)
        # Acceptance cancels the result; no recovery/return-fumble rolls are invented.
        marked = enforce_penalty(start_drive(state.possession, spot), penalty)
        return self._finish(
            SpecialTeamsOutcome.PENALTY, start_drive(state.possession, marked.yards_to_goal)
        )

    def _score(
        self, possession: Possession, points: int, outcome: SpecialTeamsOutcome
    ) -> SpecialTeamsResolution:
        delta = (points, 0) if possession is Possession.HOME else (0, points)
        return self._finish(outcome, None, delta)

    def _recovery(
        self,
        state: FieldState,
        location: int,
        *,
        blocked: bool = False,
        origin: int | None = None,
        snap: bool = True,
        snap_state: FieldState | None = None,
    ) -> SpecialTeamsResolution:
        self.chain_depth += 1
        if self.chain_depth > MAX_KICK_CHAIN:
            raise ValueError("kick recovery chain limit exceeded")
        scrimmage = snap_state if snap_state is not None else state if snap else None
        chart = self.charts[state.possession]
        spot = (state.yards_to_goal if origin is None else origin) - location
        if spot >= 110:
            return self._score(state.possession.other, 2, SpecialTeamsOutcome.SAFETY)
        if spot <= -10:
            depth_roll = self.dice.offensive()
            self.trace.append(
                SpecialTeamsTrace("recovery_end_zone_depth", chart.name, depth_roll, None)
            )
            spot = -(depth_roll.white_one + depth_roll.white_two)
        roll = self.dice.offensive()
        self.trace.append(
            SpecialTeamsTrace(
                "blocked_kick_recovery" if blocked else "fumble_recovery", chart.name, roll, None
            )
        )
        retained = roll.total in chart.recovery_range
        receiver = state.possession if retained else state.possession.other
        if spot <= 0:
            if retained:
                return self._score(receiver, 6, SpecialTeamsOutcome.RETURN_TOUCHDOWN)
            return self._end_zone_choice(receiver, 100 - spot)
        if spot >= 100:
            scorer = state.possession.other
            outcome = (
                SpecialTeamsOutcome.SAFETY if retained else SpecialTeamsOutcome.RETURN_TOUCHDOWN
            )
            return self._score(scorer, 2 if retained else 6, outcome)
        landing = spot if retained else 100 - spot
        if blocked and not retained and roll.total == 39:
            return self._score(receiver, 6, SpecialTeamsOutcome.RETURN_TOUCHDOWN)
        allowed = (retained and roll.total in {17, 18, 19} and (not blocked or location <= 0)) or (
            not retained and (blocked or roll.total in {37, 38, 39})
        )
        if allowed:
            return self._misc_return(receiver, landing, scrimmage if retained else None)
        if retained and scrimmage is not None:
            transition = apply_gain(scrimmage, scrimmage.yards_to_goal - spot)
            return self._finish(SpecialTeamsOutcome.RECOVERY, transition.state)
        return self._finish(SpecialTeamsOutcome.RECOVERY, start_drive(receiver, landing))

    def _end_zone_choice(self, possession: Possession, landing: int) -> SpecialTeamsResolution:
        # A live recovered ball allows an explicit touchback or return election.
        return self._choice(
            possession,
            [
                (
                    "kick:touchback",
                    "Take a touchback",
                    lambda: self._finish(
                        SpecialTeamsOutcome.TOUCHBACK, start_drive(possession, 80)
                    ),
                ),
                (
                    "kick:return",
                    "Return the recovered ball",
                    lambda: self._misc_return(possession, landing),
                ),
            ],
        )

    def _misc_return(
        self,
        possession: Possession,
        landing: int,
        snap_state: FieldState | None = None,
    ) -> SpecialTeamsResolution:
        state = start_drive(possession, min(99, landing))
        return self._column(
            state,
            SpecialTeamsColumn.INTERCEPTION_RETURN,
            lambda cell: self._return_cell(
                possession, landing, cell, snap_state=snap_state, miscellaneous=True
            ),
            is_return=True,
            return_origin=landing,
        )


def resolve_kickoff(
    kicking: TeamChart,
    receiving: TeamChart,
    *,
    home_season: int,
    dice: DiceSource,
) -> SpecialTeamsResolution:
    """Convenience resolver: automatically take the explicitly selected touchback policy."""
    procedure = SpecialTeamsPlay(
        "kickoff",
        start_drive(Possession.HOME, 65),
        kicking,
        receiving,
        dice,
        home_season=home_season,
    )
    result = procedure.begin()
    if any(c.id == "kick:touchback" for c in result.choices):
        return procedure.decide("kick:touchback")
    return result


def resolve_punt(
    state: FieldState,
    kicking: TeamChart,
    receiving: TeamChart,
    *,
    choice: str,
    dice: DiceSource,
) -> SpecialTeamsResolution:
    """Convenience resolver with an explicit preselected punt reception choice."""
    if choice not in {"fair_catch", "return"}:
        raise ValueError("punt choice must be fair_catch or return")
    procedure = SpecialTeamsPlay(
        "punt", state, kicking, receiving, dice, home_season=kicking.season
    )
    result = procedure.begin()
    key = "kick:fair_catch" if choice == "fair_catch" else "kick:return"
    if any(c.id == key for c in result.choices):
        return procedure.decide(key)
    if any(c.id == "kick:touchback" for c in result.choices):
        return procedure.decide("kick:touchback")
    return result


def resolve_field_goal(
    state: FieldState, kicking: TeamChart, dice: DiceSource, *, receiving: TeamChart
) -> SpecialTeamsResolution:
    """Resolve a field goal against LOS-to-goal, never statistical kick length."""
    return SpecialTeamsPlay(
        "field_goal", state, kicking, receiving, dice, home_season=kicking.season
    ).begin()


def _validate_season(home_season: int) -> None:
    if type(home_season) is not int:
        raise TypeError("home_season must be an integer")
    if not MIN_SUPPORTED_SEASON <= home_season <= MAX_SUPPORTED_SEASON:
        raise ValueError(
            f"home_season must be within {MIN_SUPPORTED_SEASON}..{MAX_SUPPORTED_SEASON}"
        )


def _penalty_result_text(
    cell: NormalizedCell, column: SpecialTeamsColumn, *, is_return: bool
) -> str:
    """Describe the prepared kick/return cell without invoking its continuation."""
    if cell.kind in {ResultKind.FUMBLE, ResultKind.BLOCKED_KICK}:
        distance = f" at {cell.yards:+d} yards" if cell.yards is not None else ""
        name = cell.kind.value.replace("_", " ")
        return f"{name}{distance}; recovery still to be resolved"
    if cell.kind is ResultKind.TOUCHDOWN:
        return "touchdown"
    if cell.kind is ResultKind.NO_GOOD_FIELD_GOAL:
        return "missed field goal"
    redirects = {
        ResultKind.FIELD_GOAL_REFERENCE: "field-goal chart lookup next",
        ResultKind.KICKOFF_REFERENCE: "kickoff chart lookup next",
    }
    if cell.kind in redirects:
        return redirects[cell.kind]
    if cell.kind is ResultKind.NO_CHANGE:
        distance = 0
    elif cell.yards is not None:
        distance = cell.yards
    else:
        return f"{cell.kind.value} chart result (distance still to be resolved)"
    if is_return:
        unit = "yard" if abs(distance) == 1 else "yards"
        if distance < 0:
            return f"return loss of {abs(distance)} {unit}"
        return f"return of {distance} {unit}" if distance else "no gain on the return"
    if column is SpecialTeamsColumn.FIELD_GOAL:
        return f"field-goal chart range of {distance} yards"
    name = column.value.replace("_", " ")
    if cell.out_of_bounds:
        return f"{distance}-yard {name} out of bounds"
    return f"{distance}-yard {name}; reception still to be resolved"


def _location(yards_to_goal: int) -> str:
    """Describe a live spot from the named team's perspective, including end zones."""
    if yards_to_goal >= 110:
        return "beyond the end line"
    if yards_to_goal >= 100:
        return f"{yards_to_goal - 100} yards deep in the end zone"
    if yards_to_goal <= 0:
        return "the opponents' end zone"
    if yards_to_goal == 50:
        return "midfield"
    return f"own {100 - yards_to_goal}" if yards_to_goal > 50 else f"opponents' {yards_to_goal}"
