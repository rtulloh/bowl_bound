"""Engine-owned play sessions, scoring ledgers, and Bowl Bound conversion decisions.

The API/UI transport and display these immutable views without interpreting rules.
Regulation/overtime orchestration composes this session without duplicating play rules.
"""

from dataclasses import dataclass, replace
from enum import Enum
from random import Random

from .dice import DiceSource, RandomDice, roll_view
from .game_state import (
    EndZonePending,
    FieldState,
    Outcome,
    PendingOutcomeError,
    Possession,
    Transition,
    apply_gain,
    apply_result,
    situation_label,
    spot_label,
    start_drive,
)
from .models import Defense, Play, ResultKind, TeamChart
from .penalties import PreparedPlay, prepare_play
from .penalty_yardage import AssessedPenalty, enforce_penalty, enforce_return_penalty
from .resolution import LookupTrace, PlayResolution
from .scoring import ScoreKind, ScoreLedger, resolve_pat
from .special_teams import SpecialTeamsPlay, SpecialTeamsResolution
from .statistics import (
    PlayStatistics,
    StatisticsView,
    StatKind,
    clipped_yards,
    fumble_yards,
    scrimmage_credit,
    summarize,
)
from .team_csv import format_cell
from .timing import TimingFacts
from .turnovers import (
    TurnoverOutcome,
    TurnoverResolution,
    TurnoverTrace,
    decline_return_penalties,
    resolve_end_zone_recovery_return,
    resolve_fumble,
    resolve_interception,
    resolve_turnover_location,
)

DEFAULT_START_YARDS_TO_GOAL = 65  # own 35
PLAY_LABELS = {
    Play.ONE: "Line Plunge",
    Play.TWO: "Counter",
    Play.THREE: "End Reverse",
    Play.FOUR: "Draw",
    Play.FIVE: "Option",
    Play.SIX: "Screen",
    Play.SEVEN: "Sprint Out",
    Play.EIGHT: "Boot-leg",
    Play.NINE: "Drop Back",
}
# Verified six formation-band names in the supported Mays Bowl Bound layout.
DEFENSE_LABELS = {
    Defense.A: "Standard",
    Defense.B: "Short yardage (gaps)",
    Defense.C: "Short yardage (wide)",
    Defense.D: "Pass prevent (short)",
    Defense.E: "Pass prevent (long)",
    Defense.F: "Blitz",
}
_UNSUPPORTED_KINDS = {
    ResultKind.PENALTY: "penalty",
}


class SessionPhase(str, Enum):
    SCRIMMAGE = "scrimmage"
    CONVERSION_CHOICE = "conversion_choice"
    TWO_POINT_TRY = "two_point_try"
    COMPLETE = "complete"


class SessionFinishedError(RuntimeError):
    """The demonstration drive is over; no further snaps are accepted."""


class PendingDecisionError(RuntimeError):
    """A snap or decision was attempted while the session awaits another action."""


class InvalidDecisionError(ValueError):
    """The submitted penalty decision is not one of the enabled choices."""


@dataclass(frozen=True)
class Action:
    key: str
    label: str


@dataclass(frozen=True)
class Actions:
    offense: tuple[Action, ...]
    defense: tuple[Action, ...]
    special: tuple[Action, ...] = ()


@dataclass(frozen=True)
class StateView:
    """Everything the field and scoreboard draw, precomputed by the engine."""

    possession: str
    possession_name: str
    down: int
    yards_to_go: int
    yards_to_goal: int
    spot: str
    situation: str
    attacking: str
    ball_from_left: int
    first_down_from_left: int


@dataclass(frozen=True)
class TraceEntry:
    section: str
    team: str
    play: str
    formation: str | None
    roll: dict[str, object]
    cell: str


@dataclass(frozen=True)
class PlayReport:
    number: int
    supported: bool
    pending: bool
    outcome: str
    yards: int | None
    called_play: str
    resolved_play: str
    defense: str
    state_before: StateView
    state_after: StateView | None
    description: str
    unsupported_reason: str | None
    trace: tuple[TraceEntry, ...]
    timing: TimingFacts = TimingFacts()
    extends_quarter: bool = False
    statistics: PlayStatistics = PlayStatistics()

    @property
    def commentary(self) -> str:
        """Explain recorded turnover facts without changing legacy saved descriptions.

        Recovery trace entries name the fumbler, not the recovering team. Only
        a single recovery without a return can label the final spot a recovery
        spot; chained returns instead show the final ball position.
        """
        fumbles = tuple(e for e in self.trace if e.section == "fumble_recovery")
        intercepted = self.statistics.kind is StatKind.INTERCEPTION
        if not fumbles and not intercepted:
            return self.description
        details = [self.description]
        if intercepted:
            details.append("INTERCEPTED!")
        details.extend(f"Fumble by {entry.team}!" for entry in fumbles)
        after = self.state_after
        if after is not None and not self.pending:
            no_return = not any("return" in entry.section for entry in self.trace)
            if (
                len(fumbles) == 1
                and no_return
                and self.outcome
                in {
                    "offensive_recovery",
                    "defensive_recovery",
                }
            ):
                details.append(f"{after.possession_name} recovers at {after.spot}.")
            else:
                details.append(f"{after.possession_name} ball at {after.spot}.")
            if after.possession != self.state_before.possession:
                details.append("★ TURNOVER!")
        return " ".join(details)


@dataclass(frozen=True)
class PenaltyChoice:
    """One engine-provided choice for a pending penalty or turnover decision."""

    id: str
    label: str
    enabled: bool
    reason: str | None = None


@dataclass(frozen=True)
class PendingDecisionView:
    """The player who decides and the legal, engine-owned choices."""

    chooser: str
    choices: tuple[PenaltyChoice, ...]
    chooser_side: str | None = None


@dataclass(frozen=True)
class ScoreView:
    """Score owned by the engine, in home/away order."""

    home: int
    away: int


@dataclass(frozen=True)
class ScoringEventView:
    number: int
    play_number: int
    team: str
    kind: str
    points: int


@dataclass(frozen=True)
class KickoffPenaltyView:
    team: str
    yards: int
    code: str


@dataclass(frozen=True)
class SessionView:
    home: str
    away: str
    state: StateView | None
    actions: Actions
    finished: bool
    log: tuple[PlayReport, ...]
    pending: PendingDecisionView | None = None
    score: ScoreView = ScoreView(0, 0)
    phase: str = "scrimmage"
    status: str = "Choose an offensive play and defensive formation."
    scoring: tuple[ScoringEventView, ...] = ()
    kickoff_penalties: tuple[KickoffPenaltyView, ...] = ()
    statistics: StatisticsView = StatisticsView()


@dataclass(frozen=True)
class _PendingDecision:
    prepared: PreparedPlay
    called: Play
    defensive: Defense
    field: FieldState
    before: StateView
    trace: tuple[TraceEntry, ...]
    prefix: str
    view: PendingDecisionView
    dice: DiceSource | None = None
    turnover: bool = False
    turnover_resolution: TurnoverResolution | None = None
    turnover_location: int | None = None


class PlaySession:
    """A seeded, in-memory drive that resolves one real engine play per snap."""

    def __init__(
        self, home: TeamChart, away: TeamChart, seed: int, start_yards_to_goal: int
    ) -> None:
        self._charts = {Possession.HOME: home, Possession.AWAY: away}
        self._dice: DiceSource = RandomDice(Random(seed))
        self._field: FieldState | None = start_drive(Possession.HOME, start_yards_to_goal)
        self._log: list[PlayReport] = []
        self._pending: _PendingDecision | None = None
        self._special: tuple[SpecialTeamsPlay, StateView] | None = None
        self._ledger = ScoreLedger()
        self._phase = SessionPhase.SCRIMMAGE
        self._conversion_team: Possession | None = None
        self._kickoff_penalties: tuple[KickoffPenaltyView, ...] = ()
        self._scheduled_kickoff = False
        self._safety_free_kick = False
        self._hail_mary = False
        self._overtime = False

    @classmethod
    def new(
        cls,
        home: TeamChart,
        away: TeamChart,
        *,
        seed: int,
        start_yards_to_goal: int = DEFAULT_START_YARDS_TO_GOAL,
    ) -> "PlaySession":
        if not isinstance(home, TeamChart) or not isinstance(away, TeamChart):
            raise TypeError("a session needs two TeamChart instances")
        if type(seed) is not int:
            raise TypeError("seed must be an integer")
        return cls(home, away, seed, start_yards_to_goal)

    @classmethod
    def for_analysis(
        cls,
        home: TeamChart,
        away: TeamChart,
        field: FieldState,
        *,
        overtime: bool = False,
        phase: SessionPhase = SessionPhase.SCRIMMAGE,
    ) -> "PlaySession":
        """Build an isolated one-play sandbox from explicit public field facts.

        This is not a game clone or save loader. It starts with an empty ledger
        and log; evaluators supply independent hypothetical dice on every action.
        No existing session, pending decision or live random state is copied.
        """
        if not isinstance(field, FieldState) or type(overtime) is not bool:
            raise TypeError("analysis requires a FieldState and boolean overtime flag")
        if not isinstance(phase, SessionPhase):
            raise TypeError("analysis phase must be a SessionPhase")
        if phase not in {SessionPhase.SCRIMMAGE, SessionPhase.TWO_POINT_TRY}:
            raise ValueError("analysis supports scrimmage or two-point try phases only")
        if phase is SessionPhase.TWO_POINT_TRY and (
            field.down != 1 or field.yards_to_goal != 2 or field.yards_to_go != 2
        ):
            raise ValueError("a try analysis must begin first-and-goal at the two")
        session = cls.new(home, away, seed=0, start_yards_to_goal=field.yards_to_goal)
        session._field = field
        session._overtime = overtime
        session._phase = phase
        if phase is SessionPhase.TWO_POINT_TRY:
            session._conversion_team = field.possession
        return session

    @property
    def possession(self) -> Possession:
        if self._field is None:
            raise SessionFinishedError("the drive is over")
        return self._field.possession

    def view(self) -> SessionView:
        state = None if self._field is None else self._state_view(self._field)
        return SessionView(
            self._charts[Possession.HOME].name,
            self._charts[Possession.AWAY].name,
            state,
            replace(_actions(), special=self._special_actions()),
            self._phase is SessionPhase.COMPLETE,
            tuple(self._log),
            self._pending_view(),
            ScoreView(*self._ledger.totals),
            self._phase.value,
            self._status(),
            tuple(
                ScoringEventView(
                    e.number, e.play_number, self._charts[e.scorer].name, e.kind.value, e.points
                )
                for e in self._ledger.events
            ),
            self._kickoff_penalties,
            summarize(report.statistics for report in self._log),
        )

    def prepare_series(self, team: Possession, *, try_only: bool = False) -> None:
        """Start an overtime series/paired try, preserving the ledger and observed history."""
        if self._pending is not None or self._special is not None:
            raise PendingDecisionError("finish the live procedure before starting a series")
        self._overtime = True
        spot = 2 if try_only else 25
        for penalty in self._kickoff_penalties:
            if penalty.team == self._charts[team].name:
                spot += min(penalty.yards, (100 - spot) // 2)
            else:
                spot -= min(penalty.yards, spot // 2)
        self._kickoff_penalties = ()
        self._field = start_drive(team, spot)
        self._phase = SessionPhase.TWO_POINT_TRY if try_only else SessionPhase.SCRIMMAGE
        self._conversion_team = team if try_only else None
        self._scheduled_kickoff = False
        self._safety_free_kick = False
        self._hail_mary = False

    def prepare_kickoff(self, team: Possession, *, safety: bool = False) -> None:
        """Schedule a regulation free kick without discarding scores or play history."""
        from .special_teams import kickoff_spot

        if self._pending is not None or self._special is not None:
            raise PendingDecisionError("finish the live procedure before scheduling a kickoff")
        self._overtime = False
        own = 20 if safety else kickoff_spot(self._charts[Possession.HOME].season)
        for penalty in self._kickoff_penalties:
            # Carried try fouls were committed by the receiving team.
            own += min(penalty.yards, (100 - own) // 2)
        self._kickoff_penalties = ()
        self._field = start_drive(team, 100 - own)
        self._phase = SessionPhase.SCRIMMAGE
        self._scheduled_kickoff = True
        self._safety_free_kick = safety

    def automatic(self, action: str) -> PlayReport:
        """Apply an engine automatic kneel/spike; regulation owns action eligibility."""
        if action not in {"kneel", "spike"}:
            raise InvalidDecisionError("unknown automatic play")
        if self._pending_view() is not None:
            raise PendingDecisionError("finish the pending decision")
        if self._field is None:
            raise SessionFinishedError("the drive is over")
        field = self._field
        before = self._state_view(field)
        yards = -2 if action == "kneel" else 0
        outcome = "safety"
        try:
            transition = apply_gain(field, yards)
            self._field = transition.state
            outcome = transition.outcome.value
        except EndZonePending:
            self._field = None
            self._add_score(field.possession.other, 2)
        after = self._state_view(self._field) if self._field is not None else None
        label = "Kneel" if action == "kneel" else "Spike"
        report = PlayReport(
            len(self._log) + 1,
            True,
            False,
            outcome,
            yards,
            label,
            label,
            "No formation",
            before,
            after,
            f"{self._charts[field.possession].name}: {label}; {yards} yards.",
            None,
            (),
            TimingFacts(
                incomplete=action == "spike",
                scoring=outcome == "safety",
                change_of_possession=after is not None and after.possession != before.possession,
            ),
        )
        if self._phase is not SessionPhase.TWO_POINT_TRY:
            report = replace(
                report,
                statistics=PlayStatistics(
                    StatKind.RUSH if action == "kneel" else StatKind.INCOMPLETE,
                    field.possession,
                    clipped_yards(yards, field.yards_to_goal),
                ),
            )
        report = self._finish_report(report)
        self._log.append(report)
        return report

    def _special_actions(self) -> tuple[Action, ...]:
        if self._scheduled_kickoff:
            return (Action("kickoff", "Safety free kick" if self._safety_free_kick else "Kickoff"),)
        if self._phase is SessionPhase.TWO_POINT_TRY:
            return ()
        if self._field is None or self._pending is not None or self._special is not None:
            return ()
        actions = [Action("punt", "Punt")]
        if self._field.yards_to_goal < 93:
            actions.append(Action("field_goal", "Field goal attempt"))
        season = self._charts[Possession.HOME].season
        if not self._log and 1940 <= season <= 2023:
            actions.insert(0, Action("kickoff", "Opening kickoff"))
        return tuple(actions)

    def _pending_view(self) -> PendingDecisionView | None:
        if self._phase is SessionPhase.CONVERSION_CHOICE:
            return PendingDecisionView(
                self._charts[self._conversion_team].name,
                (
                    PenaltyChoice("conversion:kick", "Kick a one-point PAT", True),
                    PenaltyChoice("conversion:two", "Attempt a two-point conversion", True),
                ),
                chooser_side=self._conversion_team.value,
            )
        if self._special is not None:
            result = self._special[0].result
            if result is not None and result.choices and result.chooser is not None:
                return PendingDecisionView(
                    self._charts[result.chooser].name,
                    tuple(PenaltyChoice(c.id, c.label, True) for c in result.choices),
                    chooser_side=result.chooser.value,
                )
        return None if self._pending is None else self._pending.view

    def kick(
        self, action: str, *, dice: DiceSource | None = None, hurried: bool = False
    ) -> PlayReport:
        """Start one legal engine-owned kick action without a defensive dice roll."""
        if self._phase is SessionPhase.CONVERSION_CHOICE:
            raise PendingDecisionError("choose the touchdown conversion first")
        if self._field is None:
            raise SessionFinishedError("the drive is over")
        if self._pending is not None or self._special is not None:
            raise PendingDecisionError("an engine decision is required before another action")
        if action not in {item.key for item in self._special_actions()}:
            raise InvalidDecisionError("that special-teams action is unavailable")
        field = self._field
        procedure = SpecialTeamsPlay(
            action,
            field,
            self._charts[field.possession],
            self._charts[field.possession.other],
            dice or self._dice,
            home_season=self._charts[Possession.HOME].season,
            safety_free_kick=self._safety_free_kick,
            hurried=hurried,
        )
        if self._scheduled_kickoff:
            procedure.start = field
        before = self._state_view(field)
        result = procedure.begin()
        return self._apply_special(procedure, result, before)

    def _apply_special(
        self,
        procedure: SpecialTeamsPlay,
        result: SpecialTeamsResolution,
        before: StateView,
    ) -> PlayReport:
        labels = {"punt": "Punt", "kickoff": "Kickoff", "field_goal": "Field goal attempt"}
        label = labels[procedure.action]
        pending = bool(result.choices)
        trace = tuple(
            TraceEntry(
                entry.section,
                entry.team_name,
                label,
                None,
                roll_view(entry.roll),
                "recovery" if entry.cell is None else format_cell(entry.cell),
            )
            for entry in result.trace
        )
        if pending:
            self._special = (procedure, before)
            after = before
        else:
            self._special = None
            self._field = result.state
            self._scheduled_kickoff = False
            self._safety_free_kick = False
            self._award_delta(result.points)
            after = None if result.state is None else self._state_view(result.state)
        outcome = result.outcome.value
        description = " ".join(procedure.descriptions)
        if pending:
            description += f" {self._charts[result.chooser].name}: choose the next action."
        else:
            description += f" {outcome.replace('_', ' ')}."
            if after is not None:
                description += f" {after.possession_name} ball at {after.spot}."
        report = PlayReport(
            len(self._log) + 1,
            True,
            pending,
            outcome,
            None,
            label,
            label,
            "No formation",
            before,
            after,
            description.strip(),
            None,
            trace,
            TimingFacts(
                penalty=any(
                    e.cell is not None and e.cell.kind is ResultKind.PENALTY for e in result.trace
                ),
                change_of_possession=after is not None and before.possession != after.possession,
                scoring=any(result.points),
                touchback=outcome == "touchback",
                unreturned_kickoff=procedure.free_kick
                and not any(
                    e.section in {"kickoff_return", "turnover_return"} for e in result.trace
                ),
                no_elapsed_time=procedure.no_elapsed_time,
            ),
            extends_quarter=procedure.extends_quarter,
        )
        if not pending:
            report = self._finish_report(report)
            self._log.append(report)
        return report

    def snap(
        self,
        play: str,
        formation: str,
        *,
        dice: DiceSource | None = None,
        hurried: bool = False,
        hail_mary: bool = False,
    ) -> PlayReport:
        """Prepare one snap; penalty choices are resolved separately by :meth:`decide`."""
        called = _parse_play(play)
        defensive = _parse_formation(formation)
        if self._phase is SessionPhase.CONVERSION_CHOICE:
            raise PendingDecisionError("choose the touchdown conversion first")
        if self._pending is not None or self._special is not None:
            raise PendingDecisionError("a penalty decision is required before the next snap")
        if self._field is None:
            raise SessionFinishedError("the drive is over")
        field = self._field
        offense = self._charts[field.possession]
        defense = self._charts[field.possession.other]
        source = dice or self._dice
        self._hail_mary = hail_mary
        self._hurried_play = hurried
        prepared = prepare_play(
            offense, defense, called, defensive, source, hurried=hurried, hail_mary=hail_mary
        )
        resolution = prepared.resolution
        before = self._state_view(field)
        prefix = (
            f"{offense.name}: Hail Mary vs blank defense"
            if hail_mary
            else f"{offense.name}: {PLAY_LABELS[called]} vs {_formation_label(defensive)}"
        )
        trace = tuple(_trace_entry(entry) for entry in resolution.trace)
        if prepared.offsetting:
            return self._record(
                resolution,
                called,
                defensive,
                before,
                before,
                trace,
                None,
                f"{prefix} - offsetting penalties; replay the down.",
                outcome="offsetting",
                yards=0,
                extends_quarter=True,
            )
        if prepared.pre_snap:
            pre_snap = next(p for p in prepared.penalties if p.pre_snap)
            state = enforce_penalty(field, pre_snap)
            self._field = state
            return self._record(
                resolution,
                called,
                defensive,
                before,
                self._state_view(state),
                trace,
                None,
                f"{prefix} - pre-snap penalty enforced; replay the down.",
                outcome="pre_snap",
                yards=0,
                no_elapsed_time=prepared.no_elapsed_time,
            )
        if prepared.penalties:
            pending_view = _pending_view(
                prepared.penalties, resolution, field, offense.name, defense.name
            )
            if self._phase is SessionPhase.TWO_POINT_TRY and (
                resolution.result.kind is ResultKind.TOUCHDOWN
                or (
                    resolution.result.kind is ResultKind.YARDS
                    and _gain(resolution) >= field.yards_to_goal
                )
            ):
                destination = "next overtime series" if self._overtime else "kickoff"
                carry = tuple(
                    PenaltyChoice(
                        f"accept:{index}:kickoff",
                        f"Keep the two points; carry {penalty.yards} yards to the {destination}",
                        True,
                    )
                    for index, penalty in enumerate(prepared.penalties)
                    if penalty.from_end_of_gain and penalty.source.team.value == "defense"
                )
                pending_view = replace(pending_view, choices=(*pending_view.choices, *carry))
            self._pending = _PendingDecision(
                prepared, called, defensive, field, before, trace, prefix, pending_view, dice=source
            )
            return PlayReport(
                len(self._log) + 1,
                True,
                True,
                "penalty_pending",
                _gain(resolution),
                PLAY_LABELS[resolution.called_play],
                PLAY_LABELS[resolution.resolved_play],
                _formation_label(defensive),
                before,
                before,
                f"{prefix} - penalty decision required.",
                None,
                trace,
            )
        return self._apply_live_result(
            prepared, called, defensive, field, before, trace, prefix, source
        )

    def _apply_live_result(
        self,
        prepared: PreparedPlay,
        called: Play,
        defensive: Defense,
        field: FieldState,
        before: StateView,
        trace: tuple[TraceEntry, ...],
        prefix: str,
        source: DiceSource,
    ) -> PlayReport:
        """Continue an already prepared play; never repeat lookup after a decline."""
        resolution = prepared.resolution
        offense, defense = self._charts[field.possession], self._charts[field.possession.other]
        hurried = self._hurried_play
        if resolution.result.defensive_end_zone_depth is not None:
            resolution = replace(
                resolution,
                result=replace(
                    resolution.result,
                    yards=field.yards_to_goal + resolution.result.defensive_end_zone_depth,
                ),
            )
        if resolution.result.kind is ResultKind.INTERCEPTION:
            location, location_trace = _resolved_turnover_location(
                resolution, offense, defense, source
            )
            pending_view = PendingDecisionView(
                defense.name,
                (
                    PenaltyChoice("interception:return", "Return the interception", True),
                    PenaltyChoice("interception:decline", "Declare the pass incomplete", True),
                ),
                chooser_side=field.possession.other.value,
            )
            full_trace = (*trace, *(_turnover_trace_entry(entry) for entry in location_trace))
            self._pending = _PendingDecision(
                prepared,
                called,
                defensive,
                field,
                before,
                full_trace,
                prefix,
                pending_view,
                source,
                True,
                turnover_location=location,
            )
            return PlayReport(
                len(self._log) + 1,
                True,
                True,
                "interception_pending",
                location,
                PLAY_LABELS[resolution.called_play],
                PLAY_LABELS[resolution.resolved_play],
                _formation_label(defensive),
                before,
                before,
                f"{prefix} - interception decision required.",
                None,
                full_trace,
            )
        if resolution.result.kind is ResultKind.FUMBLE:
            location, location_trace = _resolved_turnover_location(
                resolution, offense, defense, source
            )
            turnover = resolve_fumble(
                field,
                location=location,
                fumbler=offense,
                opponent=defense,
                dice=source,
                hurried=hurried,
            )
            resolution = replace(resolution, result=replace(resolution.result, yards=location))
            turnover = replace(turnover, trace=(*location_trace, *turnover.trace))
            return self._apply_turnover(
                turnover, resolution, called, defensive, before, trace, prefix, dice=source
            )
        return self._apply_prepared(resolution, called, defensive, field, before, trace, prefix)

    def decide(self, choice: str, *, dice: DiceSource | None = None) -> PlayReport:
        """Apply exactly one enabled choice from the current penalty decision."""
        if self._phase is SessionPhase.CONVERSION_CHOICE:
            return self._choose_conversion(choice, dice or self._dice)
        if self._special is not None:
            procedure, before = self._special
            if procedure.result is None or choice not in {c.id for c in procedure.result.choices}:
                raise InvalidDecisionError("unknown special-teams decision")
            result = procedure.decide(choice)
            return self._apply_special(procedure, result, before)
        pending = self._pending
        if pending is None:
            raise PendingDecisionError("there is no penalty decision to make")
        selected = next((item for item in pending.view.choices if item.id == choice), None)
        if selected is None:
            raise InvalidDecisionError("unknown penalty decision")
        if not selected.enabled:
            raise InvalidDecisionError(selected.reason or "penalty decision cannot be selected")
        if pending.turnover and pending.turnover_resolution is not None:
            turnover = pending.turnover_resolution
            if turnover.end_zone_recovery:
                if pending.dice is None:
                    raise RuntimeError("end-zone recovery decision is missing its dice source")
                self._pending = None
                recovery_possession = turnover.recovery_possession or pending.field.possession.other
                if choice == "end_zone:touchback":
                    turnover = replace(
                        turnover,
                        outcome=TurnoverOutcome.TOUCHBACK,
                        state=start_drive(recovery_possession, 80),
                        end_zone_recovery=False,
                    )
                else:
                    returned = resolve_end_zone_recovery_return(
                        self._charts[recovery_possession],
                        self._charts[recovery_possession.other],
                        recovery_possession,
                        pending.dice,
                        end_zone_depth=turnover.end_zone_depth,
                        hurried=self._hurried_play,
                    )
                    turnover = replace(returned, trace=(*turnover.trace, *returned.trace))
                return self._apply_turnover(
                    turnover,
                    pending.prepared.resolution,
                    pending.called,
                    pending.defensive,
                    pending.before,
                    pending.trace,
                    pending.prefix,
                    dice=pending.dice,
                )
            penalty = turnover.return_penalty
            if penalty is None or turnover.return_start is None or turnover.return_yards is None:
                raise RuntimeError("return penalty decision is incomplete")
            self._pending = None
            accepted = choice == "return:accept" or choice.startswith("return:accept:")
            return_credit = None
            if accepted:
                index = int(choice.rsplit(":", 1)[-1]) if choice.startswith("return:accept:") else 0
                penalty = turnover.return_penalties[index] if turnover.return_penalties else penalty
                state = enforce_return_penalty(
                    turnover.return_start,
                    penalty,
                    return_yards=turnover.return_yards,
                    origin=turnover.return_origin,
                    continues_original_play=turnover.continues_original_play,
                    scrimmage_start=turnover.scrimmage_start,
                )
                # Ask the same enforcement policy for its legal-advance base,
                # without including stepped-off foul yardage in offensive credit.
                base = enforce_return_penalty(
                    turnover.return_start,
                    replace(penalty, yards=0),
                    return_yards=turnover.return_yards,
                    origin=turnover.return_origin,
                )
                return_credit = turnover.return_start.yards_to_goal - base.yards_to_goal
                turnover = replace(
                    turnover,
                    state=state,
                    points=(0, 0),
                    end_zone=None,
                    outcome=(
                        TurnoverOutcome.OFFENSIVE_RECOVERY
                        if turnover.continues_original_play
                        else TurnoverOutcome.DEFENSIVE_RECOVERY
                    ),
                    return_penalty=None,
                    return_penalties=(),
                    continuation=None,
                )
            else:
                if pending.dice is None:
                    raise RuntimeError("return continuation is missing its dice source")
                turnover = decline_return_penalties(turnover, pending.dice)
            return self._apply_turnover(
                turnover,
                pending.prepared.resolution,
                pending.called,
                pending.defensive,
                pending.before,
                pending.trace,
                pending.prefix,
                dice=pending.dice,
                return_credit=return_credit,
            )
        if pending.turnover:
            if pending.dice is None:
                raise RuntimeError("turnover decision is missing its dice source")
            location = pending.turnover_location
            if location is None:
                raise RuntimeError("interception decision is missing its location")
            turnover = resolve_interception(
                pending.field,
                location=location,
                interceptor=self._charts[pending.field.possession.other],
                opponent=self._charts[pending.field.possession],
                choice=choice.removeprefix("interception:"),
                dice=pending.dice,
                hurried=self._hurried_play,
            )
            self._pending = None
            return self._apply_turnover(
                turnover,
                pending.prepared.resolution,
                pending.called,
                pending.defensive,
                pending.before,
                pending.trace,
                pending.prefix,
                dice=pending.dice,
            )
        if choice == "decline":
            self._pending = None
            return self._apply_live_result(
                pending.prepared,
                pending.called,
                pending.defensive,
                pending.field,
                pending.before,
                pending.trace,
                pending.prefix,
                pending.dice or self._dice,
            )
        _, index_text, spot = choice.split(":")
        penalty = pending.prepared.penalties[int(index_text)]
        gain = _gain(pending.prepared.resolution)
        if spot == "kickoff":
            self._pending = None
            self._kickoff_penalties = (
                *self._kickoff_penalties,
                KickoffPenaltyView(
                    self._charts[pending.field.possession.other].name,
                    penalty.yards,
                    penalty.source.code.value,
                ),
            )
            report = self._apply_prepared(
                pending.prepared.resolution,
                pending.called,
                pending.defensive,
                pending.field,
                pending.before,
                pending.trace,
                pending.prefix,
            )
            destination = "next overtime series" if self._overtime else "following kickoff"
            report = replace(
                report,
                description=report.description
                + f" {penalty.yards}-yard defensive penalty carried to the {destination}.",
            )
            self._log[-1] = report
            return report
        state = enforce_penalty(pending.field, penalty, gain=gain, from_end=spot == "end")
        self._pending = None
        self._field = state
        where = "end of gain" if spot == "end" else "previous spot"
        description = (
            f"{pending.prefix} - accepted {penalty.source.team.value} "
            f"{penalty.source.code.value} penalty for {penalty.yards} yards from {where}."
        )
        return self._record(
            pending.prepared.resolution,
            pending.called,
            pending.defensive,
            pending.before,
            self._state_view(state),
            pending.trace,
            None,
            description,
            outcome="penalty_accepted",
            yards=gain,
            extends_quarter=penalty.source.team.value == "defense",
            count_penalty_result=spot == "end",
        )

    def _apply_prepared(
        self,
        resolution: PlayResolution,
        called: Play,
        defensive: Defense,
        field: FieldState,
        before: StateView,
        trace: tuple[TraceEntry, ...],
        prefix: str,
    ) -> PlayReport:
        try:
            transition = apply_result(field, resolution.result)
        except PendingOutcomeError:
            reason = _unsupported_reason(resolution)
            return self._record(
                resolution,
                called,
                defensive,
                before,
                None,
                trace,
                reason,
                f"{prefix} - {reason} result is not yet supported; the play was not applied.",
            )
        except EndZonePending:
            self._field = None
            self._add_score(field.possession.other, 2)
            return self._record(
                resolution,
                called,
                defensive,
                before,
                None,
                trace,
                None,
                f"{prefix} - safety for {self._charts[field.possession.other].name}.",
                outcome="safety",
                yards=_gain(resolution),
            )
        return self._apply(resolution, called, defensive, field, before, transition, trace, prefix)

    def _apply(
        self,
        resolution: PlayResolution,
        called: Play,
        defensive: Defense,
        field: FieldState,
        before: StateView,
        transition: Transition,
        trace: tuple[TraceEntry, ...],
        prefix: str,
    ) -> PlayReport:
        self._field = transition.state
        if transition.outcome is Outcome.TOUCHDOWN:
            self._add_score(field.possession, 6)
        after = None if transition.state is None else self._state_view(transition.state)
        yards = _gain(resolution)
        sentence = f"{prefix} - {_gain_text(resolution.result.kind, yards)}"
        extra = self._outcome_text(transition, field)
        description = f"{sentence}. {extra}" if extra else sentence
        return self._record(
            resolution,
            called,
            defensive,
            before,
            after,
            trace,
            None,
            description,
            outcome=transition.outcome.value,
            yards=yards,
        )

    def _apply_turnover(
        self,
        turnover: TurnoverResolution,
        resolution: PlayResolution,
        called: Play,
        defensive: Defense,
        before: StateView,
        trace: tuple[TraceEntry, ...],
        prefix: str,
        *,
        dice: DiceSource | None = None,
        return_credit: int | None = None,
    ) -> PlayReport:
        """Record one completed turnover sequence without presentation-layer rules."""
        if turnover.end_zone_recovery:
            if dice is None:
                raise RuntimeError("end-zone recovery needs its original dice source")
            field = FieldState(
                Possession(before.possession), before.yards_to_goal, before.down, before.yards_to_go
            )
            recovery_possession = turnover.recovery_possession or field.possession.other
            can_return = True
            view = PendingDecisionView(
                self._charts[recovery_possession].name,
                (
                    PenaltyChoice(
                        "end_zone:return",
                        "Return the recovered ball",
                        can_return,
                        None,
                    ),
                    PenaltyChoice("end_zone:touchback", "Take a touchback", True),
                ),
                chooser_side=recovery_possession.value,
            )
            self._pending = _PendingDecision(
                PreparedPlay(resolution),
                called,
                defensive,
                field,
                before,
                trace,
                prefix,
                view,
                dice=dice,
                turnover=True,
                turnover_resolution=turnover,
            )
            return PlayReport(
                len(self._log) + 1,
                True,
                True,
                "end_zone_recovery_pending",
                None,
                PLAY_LABELS[resolution.called_play],
                PLAY_LABELS[resolution.resolved_play],
                _formation_label(defensive),
                before,
                before,
                f"{prefix} - end-zone recovery decision required.",
                None,
                (*trace, *(_turnover_trace_entry(entry) for entry in turnover.trace)),
            )
        if turnover.return_penalty is not None:
            chooser_side = (
                turnover.return_start.possession
                if turnover.return_penalty.source.team.value == "defense"
                else turnover.return_start.possession.other
            )
            chooser = self._charts[chooser_side].name
            view = PendingDecisionView(
                chooser,
                (
                    *tuple(
                        _return_penalty_choice(index, p, turnover)
                        for index, p in enumerate(
                            turnover.return_penalties or (turnover.return_penalty,)
                        )
                    ),
                    PenaltyChoice("return:decline", "Decline return penalties", True),
                ),
                chooser_side=chooser_side.value,
            )
            self._pending = _PendingDecision(
                PreparedPlay(resolution),
                called,
                defensive,
                turnover.return_start,
                before,
                trace,
                prefix,
                view,
                dice=dice,
                turnover=True,
                turnover_resolution=turnover,
            )
            return PlayReport(
                len(self._log) + 1,
                True,
                True,
                "return_penalty_pending",
                None,
                PLAY_LABELS[resolution.called_play],
                PLAY_LABELS[resolution.resolved_play],
                _formation_label(defensive),
                before,
                before,
                f"{prefix} - return penalty decision required.",
                None,
                (*trace, *(_turnover_trace_entry(entry) for entry in turnover.trace)),
            )
        self._field = turnover.state
        self._award_delta(turnover.points)
        after = None if turnover.state is None else self._state_view(turnover.state)
        turnover_trace = tuple(_turnover_trace_entry(entry) for entry in turnover.trace)
        outcome = turnover.outcome.value
        description = f"{prefix} - {outcome.replace('_', ' ')}."
        return self._record(
            resolution,
            called,
            defensive,
            before,
            after,
            (*trace, *turnover_trace),
            None,
            description,
            outcome=outcome,
            yards=resolution.result.yards,
            statistics_yards=(
                fumble_yards(
                    resolution.result.yards or 0,
                    before.yards_to_goal,
                    turnover.trace,
                    self._charts[Possession(before.possession)].recovery_range,
                    return_credit=return_credit,
                )
                if resolution.result.kind is ResultKind.FUMBLE
                else None
            ),
            credit_touchdown=not any(
                e.section == "fumble_recovery"
                and e.roll.total not in self._charts[Possession(before.possession)].recovery_range
                for e in turnover.trace
            ),
            return_penalty_seen=any(
                e.cell is not None and e.cell.kind is ResultKind.PENALTY for e in turnover.trace
            ),
        )

    def _award_kind(self, scorer: Possession, kind: ScoreKind) -> None:
        self._ledger = self._ledger.award(scorer, kind, play_number=len(self._log) + 1)

    def _add_score(self, scorer: Possession, points: int) -> None:
        """Translate finalized engine awards into regulation or conversion scoring."""
        if self._phase is SessionPhase.TWO_POINT_TRY:
            if points == 6:
                kind = (
                    ScoreKind.TWO_POINT
                    if scorer is self._conversion_team
                    else ScoreKind.CONVERSION_RETURN
                )
                self._award_kind(scorer, kind)
            return
        kind = {6: ScoreKind.TOUCHDOWN, 3: ScoreKind.FIELD_GOAL, 2: ScoreKind.SAFETY}[points]
        self._award_kind(scorer, kind)
        if kind is ScoreKind.TOUCHDOWN:
            self._conversion_team = scorer
            self._phase = SessionPhase.CONVERSION_CHOICE

    def _award_delta(self, points: tuple[int, int]) -> None:
        for scorer, value in zip(Possession, points, strict=True):
            if value:
                self._add_score(scorer, value)

    def _finish_report(self, report: PlayReport) -> PlayReport:
        if not report.supported or report.pending:
            return report
        if self._phase is SessionPhase.TWO_POINT_TRY:
            if report.outcome in {"offsetting", "pre_snap", "penalty_accepted"}:
                return report
            event = next((e for e in self._ledger.events if e.play_number == report.number), None)
            outcome = (
                (
                    "conversion_return"
                    if event.kind is ScoreKind.CONVERSION_RETURN
                    else "two_point_good"
                )
                if event
                else "two_point_failed"
            )
            text = {
                "conversion_return": "defensive conversion return scores two points",
                "two_point_good": "two-point conversion good",
                "two_point_failed": "two-point conversion no good",
            }[outcome]
            report = replace(
                report,
                outcome=outcome,
                state_after=None,
                description=f"{report.called_play} - {text}.",
            )
            self._field = None
            self._phase = SessionPhase.COMPLETE
        elif self._field is None and self._phase is not SessionPhase.CONVERSION_CHOICE:
            self._phase = SessionPhase.COMPLETE
        return report

    def _choose_conversion(self, choice: str, dice: DiceSource) -> PlayReport:
        if choice not in {"conversion:kick", "conversion:two"}:
            raise InvalidDecisionError("choose a PAT kick or two-point conversion")
        scorer = self._conversion_team
        assert scorer is not None
        before = self._state_view(start_drive(scorer, 2))
        if choice == "conversion:two":
            self._phase = SessionPhase.TWO_POINT_TRY
            self._field = start_drive(scorer, 2)
            return PlayReport(
                len(self._log) + 1,
                True,
                False,
                "conversion_ready",
                None,
                "Two-point conversion",
                "Two-point conversion",
                "No formation",
                before,
                before,
                self._status(),
                None,
                (),
            )
        pat = resolve_pat(self._charts[scorer], dice)
        if pat.good:
            self._award_kind(scorer, ScoreKind.PAT)
        self._phase = SessionPhase.COMPLETE
        self._field = None
        label = "PAT kick"
        trace = (
            TraceEntry(
                "pat",
                self._charts[scorer].name,
                label,
                None,
                roll_view(pat.roll),
                "GOOD" if pat.good else "NO GOOD",
            ),
        )
        report = PlayReport(
            len(self._log) + 1,
            True,
            False,
            "pat_good" if pat.good else "pat_missed",
            None,
            label,
            label,
            "No formation",
            before,
            None,
            f"{self._charts[scorer].name}: PAT {'good' if pat.good else 'no good'}.",
            None,
            trace,
        )
        self._log.append(report)
        return report

    def _status(self) -> str:
        if self._phase is SessionPhase.CONVERSION_CHOICE:
            team = self._charts[self._conversion_team].name
            return f"{team}: choose a one-point kick or two-point try."
        if self._phase is SessionPhase.TWO_POINT_TRY:
            team = self._charts[self._conversion_team].name
            return f"{team}: select a play and defense for the two-point try."
        if self._phase is SessionPhase.COMPLETE:
            return "Scoring demo complete. Post-score kickoff flow is not yet available."
        return "Choose an offensive play and defensive formation."

    def _outcome_text(self, transition: Transition, field: FieldState) -> str:
        offense_name = self._charts[field.possession].name
        if transition.outcome is Outcome.TOUCHDOWN:
            return f"Touchdown for {offense_name}"
        if transition.outcome is Outcome.FIRST_DOWN:
            return "First down."
        if transition.outcome is Outcome.TURNOVER_ON_DOWNS:
            return f"Turnover on downs; {self._charts[field.possession.other].name} takes over."
        return ""

    def _record(
        self,
        resolution: PlayResolution,
        called: Play,
        defensive: Defense,
        before: StateView,
        after: StateView | None,
        trace: tuple[TraceEntry, ...],
        reason: str | None,
        description: str,
        *,
        outcome: str = "unsupported",
        yards: int | None = None,
        extends_quarter: bool = False,
        no_elapsed_time: bool = False,
        return_penalty_seen: bool = False,
        statistics_yards: int | None = None,
        count_penalty_result: bool = False,
        credit_touchdown: bool = True,
    ) -> PlayReport:
        report = PlayReport(
            number=len(self._log) + 1,
            supported=reason is None,
            pending=reason is not None,
            outcome=outcome,
            yards=yards,
            called_play="Hail Mary" if self._hail_mary else PLAY_LABELS[resolution.called_play],
            resolved_play="Hail Mary" if self._hail_mary else PLAY_LABELS[resolution.resolved_play],
            defense="Blank defense" if self._hail_mary else _formation_label(defensive),
            state_before=before,
            state_after=after,
            description=description,
            unsupported_reason=reason,
            trace=trace,
            timing=TimingFacts(
                first_down=outcome == "first_down"
                or (
                    after is not None
                    and after.possession == before.possession
                    and before.yards_to_goal - after.yards_to_goal >= before.yards_to_go
                ),
                change_of_possession=after is not None and after.possession != before.possession,
                penalty=return_penalty_seen
                or any(e.cell.kind is ResultKind.PENALTY for e in resolution.trace),
                incomplete=resolution.result.kind is ResultKind.INCOMPLETE
                or outcome == "declined_interception",
                scoring=any(e.play_number == len(self._log) + 1 for e in self._ledger.events),
                touchback=outcome == "touchback",
                out_of_bounds=resolution.result.out_of_bounds,
                conversion=self._phase is SessionPhase.TWO_POINT_TRY,
                no_elapsed_time=no_elapsed_time,
            ),
            extends_quarter=extends_quarter,
        )
        if (
            reason is None
            and self._phase is not SessionPhase.TWO_POINT_TRY
            and outcome not in {"pre_snap", "offsetting"}
            and (outcome != "penalty_accepted" or count_penalty_result)
        ):
            gain = (
                statistics_yards
                if statistics_yards is not None
                else (
                    before.yards_to_goal
                    if resolution.result.kind is ResultKind.TOUCHDOWN
                    else _gain(resolution)
                )
            )
            team = Possession(before.possession)
            report = replace(
                report,
                statistics=scrimmage_credit(
                    resolution,
                    team,
                    clipped_yards(gain, before.yards_to_goal),
                    incomplete=outcome == "declined_interception",
                    touchdown=credit_touchdown
                    and any(
                        e.play_number == report.number
                        and e.scorer is team
                        and e.kind is ScoreKind.TOUCHDOWN
                        for e in self._ledger.events
                    ),
                ),
            )
        report = self._finish_report(report)
        self._log.append(report)
        return report

    def _state_view(self, field: FieldState) -> StateView:
        home = field.possession is Possession.HOME
        # Fixed orientation for this one-drive demo: the home goal is on the left.
        ball = 100 - field.yards_to_goal if home else field.yards_to_goal
        first_down = ball + field.yards_to_go if home else ball - field.yards_to_go
        return StateView(
            possession=field.possession.value,
            possession_name=self._charts[field.possession].name,
            down=field.down,
            yards_to_go=field.yards_to_go,
            yards_to_goal=field.yards_to_goal,
            spot=spot_label(field),
            situation=situation_label(field),
            attacking="right" if home else "left",
            ball_from_left=ball,
            first_down_from_left=first_down,
        )


def _actions() -> Actions:
    return Actions(
        tuple(Action(str(play.value), PLAY_LABELS[play]) for play in Play),
        tuple(Action(d.value, DEFENSE_LABELS[d]) for d in Defense),
    )


def _pending_view(
    penalties: tuple[AssessedPenalty, ...],
    resolution: PlayResolution,
    field: FieldState,
    offense_name: str,
    defense_name: str,
) -> PendingDecisionView:
    """Expose alternatives without attempting an unsupported result transition."""
    first = penalties[0]
    chooser = offense_name if first.source.team.value == "defense" else defense_name
    gain = _gain(resolution)
    infield_end = (
        resolution.result.kind is ResultKind.YARDS
        and gain > 0
        and 1 <= field.yards_to_goal - gain <= 99
    )
    choices: list[PenaltyChoice] = []
    for index, penalty in enumerate(penalties):
        choices.append(
            PenaltyChoice(
                f"accept:{index}:previous",
                f"Accept {penalty.yards}-yard penalty from previous spot",
                True,
            )
        )
        end_enabled = penalty.from_end_of_gain and infield_end
        choices.append(
            PenaltyChoice(
                f"accept:{index}:end",
                f"Accept {penalty.yards}-yard penalty from end of gain",
                end_enabled,
                None if end_enabled else "end-of-gain enforcement is unavailable for this result",
            )
        )
    decline_reason = _decline_blocker(field, resolution)
    decline_enabled = decline_reason is None
    choices.append(
        PenaltyChoice(
            "decline",
            f"Decline penalties: {_penalty_result_text(resolution, field)}",
            decline_enabled,
            decline_reason,
        )
    )
    side = field.possession if first.source.team.value == "defense" else field.possession.other
    return PendingDecisionView(chooser, tuple(choices), chooser_side=side.value)


def _penalty_result_text(resolution: PlayResolution, field: FieldState) -> str:
    """Describe only prepared facts; do not resolve turnovers or consume dice."""
    result = resolution.result
    if result.kind in {ResultKind.INTERCEPTION, ResultKind.FUMBLE}:
        name = result.kind.value
        if result.yards is None:
            location = " (location still to be resolved)"
        elif result.yards < 0:
            location = f" {abs(result.yards)} yards behind the line"
        else:
            location = f" {result.yards} yards downfield"
        next_step = (
            "interception decision next"
            if result.kind is ResultKind.INTERCEPTION
            else "recovery still to be resolved"
        )
        return f"{name}{location}; {next_step}"
    if result.pending:
        return "unresolved chart result (see unavailable reason)"
    if result.kind is ResultKind.YARDS and result.yards is not None:
        if result.yards >= field.yards_to_goal:
            return "touchdown"
        if field.yards_to_goal - result.yards >= 100:
            return "safety"
    return _gain_text(result.kind, _gain(resolution))


def _decline_blocker(field: FieldState, resolution: PlayResolution) -> str | None:
    """Why declining cannot be applied, or None. Uses the real transition, so it cannot drift."""
    if resolution.result.kind in {ResultKind.INTERCEPTION, ResultKind.FUMBLE}:
        return None
    if resolution.result.pending:
        return "the prepared result is pending and cannot be declined"
    try:
        apply_result(field, resolution.result)
    except PendingOutcomeError:
        return "the prepared result is not yet supported and cannot be declined"
    except EndZonePending:
        return None  # Milestone 14 resolves the safety rather than blocking decline.
    return None


def _parse_play(play: object) -> Play:
    if type(play) is not str or play not in {str(p.value) for p in Play}:
        raise ValueError("play must be one of '1' through '9'")
    return Play(int(play))


def _parse_formation(formation: object) -> Defense:
    if type(formation) is not str or formation not in {d.value for d in Defense}:
        raise ValueError("formation must be one of 'A' through 'F'")
    return Defense(formation)


def _formation_label(defense: Defense) -> str:
    return f"{defense.value} {DEFENSE_LABELS[defense]}"


def _resolved_turnover_location(
    resolution: PlayResolution, offense: TeamChart, defense: TeamChart, dice: DiceSource
) -> tuple[int, tuple[TurnoverTrace, ...]]:
    """Resolve a location from the selected chart fact and retain its trace rolls."""
    result = resolution.result
    if result.yards is not None:
        return result.yards, ()
    matches = [
        (cell, chart)
        for cell, chart in ((result.offense, offense), (result.defense, defense))
        if cell.kind is result.kind
    ]
    if not matches:
        raise ValueError("turnover result is missing its source location")
    locations = [resolve_turnover_location(cell, chart, dice) for cell, chart in matches]
    return min(location.location for location in locations), tuple(
        entry for location in locations for entry in location.trace
    )


def _gain(resolution: PlayResolution) -> int:
    return resolution.result.yards or 0


def _gain_text(kind: ResultKind | None, yards: int) -> str:
    if kind is ResultKind.INCOMPLETE:
        return "incomplete pass"
    if kind is ResultKind.TOUCHDOWN:
        return "touchdown play"
    if yards == 0:
        return "no gain"
    unit = "yard" if abs(yards) == 1 else "yards"
    return f"gain of {yards} {unit}" if yards > 0 else f"loss of {-yards} {unit}"


def _turnover_trace_entry(entry: TurnoverTrace) -> TraceEntry:
    """Adapt a turnover roll into the browser's engine-owned trace shape."""
    roll = entry.roll
    cell = "recovery" if entry.cell is None else format_cell(entry.cell)
    return TraceEntry(
        section=entry.section,
        team=entry.team_name,
        play="Turnover return",
        formation=None,
        roll=roll_view(roll),
        cell=cell,
    )


def _unsupported_reason(resolution: PlayResolution) -> str:
    kind = resolution.result.kind
    if kind in _UNSUPPORTED_KINDS:
        return _UNSUPPORTED_KINDS[kind]
    if kind is None:
        return "variable yardage"
    return kind.value


def _trace_entry(entry: LookupTrace) -> TraceEntry:
    roll = entry.roll
    shown = roll_view(roll)
    return TraceEntry(
        section=entry.section,
        team=entry.team_name,
        play=PLAY_LABELS[entry.play],
        formation=None if entry.formation is None else f"Formation {entry.formation.value}",
        roll=shown,
        cell=format_cell(entry.cell),
    )


def _return_penalty_choice(
    index: int, penalty: AssessedPenalty, turnover: TurnoverResolution
) -> PenaltyChoice:
    """Expose unsupported end-zone enforcement honestly, before any state mutation."""
    key = "return:accept" if index == 0 else f"return:accept:{index}"
    label = f"Accept {penalty.yards}-yard return penalty"
    if turnover.return_start is None or turnover.return_yards is None:
        return PenaltyChoice(key, label, False, "Return enforcement has no numeric endpoint.")
    try:
        enforce_return_penalty(
            turnover.return_start,
            penalty,
            return_yards=turnover.return_yards,
            origin=turnover.return_origin,
            continues_original_play=turnover.continues_original_play,
            scrimmage_start=turnover.scrimmage_start,
        )
    except ValueError:
        return PenaltyChoice(
            key,
            label,
            False,
            "End-zone return-penalty enforcement is not yet supported; decline remains available.",
        )
    return PenaltyChoice(key, label, True)
