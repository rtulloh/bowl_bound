"""Regulation flow over the one-play engine; no presentation-layer football rules."""

from dataclasses import dataclass, fields, replace
from enum import Enum
from random import Random

from .dice import DiceSource, OffensiveRoll, RandomDice, roll_view
from .game_state import Possession
from .models import TeamChart
from .overtime import GameType, OvertimeState, OvertimeView, overtime_profile
from .session import (
    Action,
    Actions,
    InvalidDecisionError,
    PenaltyChoice,
    PendingDecisionError,
    PendingDecisionView,
    PlayReport,
    PlaySession,
    SessionFinishedError,
    SessionView,
)
from .statistics import PlayStatistics
from .timing import BoundsDeclaration, Clock, TimingFacts, duration

TIMEOUT_SECONDS = 10


class RegulationPhase(str, Enum):
    OPENING = "opening_choice"
    KICKOFF = "kickoff"
    LIVE = "live"
    CLOCK = "clock_choice"
    # Retained only to reconstruct and validate pre-M30 save digests.
    HALFTIME = "halftime_choice"
    FINAL = "final"
    OVERTIME_CHOICE = "overtime_choice"
    OVERTIME = "overtime"


@dataclass(frozen=True)
class ClockView:
    quarter: int
    remaining: int
    quarter_label: str
    label: str
    timeouts: tuple[int, int]


@dataclass(frozen=True)
class TimeCharge:
    play_number: int
    quarter: int
    before: int
    seconds: int
    after: int
    method: str


@dataclass(frozen=True)
class RegulationView(SessionView):
    clock: ClockView | None = None
    defense_name: str | None = None
    home_timeouts: int | None = None
    away_timeouts: int | None = None
    can_kneel_out_game: bool = False
    game_actions: tuple[Action, ...] = ()
    toss_rolls: tuple[OffensiveRoll, ...] = ()
    rules_season: int = 0
    opening_kicker: str | None = None
    hurried: bool = False
    untimed_down: bool = False
    timing_log: tuple[TimeCharge, ...] = ()
    clock_optional: bool = False
    clock_modifiers: tuple[PenaltyChoice, ...] = ()
    game_type: str = "regular"
    overtime: OvertimeView | None = None
    overtime_toss_rolls: tuple[OffensiveRoll, ...] = ()
    toss_dice: tuple[dict[str, object], ...] = ()
    overtime_toss_dice: tuple[dict[str, object], ...] = ()
    bounds_declaration: str | None = None
    play_modifiers: tuple[PenaltyChoice, ...] = ()
    armed_timeout: str | None = None
    armed_timeout_label: str | None = None
    clock_timing_label: str | None = None

    def timing_label(self, play_number: int) -> str | None:
        """Describe only recorded timing, or the completed play awaiting a choice."""
        charges = [charge for charge in self.timing_log if charge.play_number == play_number]
        if not charges:
            if self.clock_optional and self.log and self.log[-1].number == play_number:
                return self.clock_timing_label
            return None
        charge = charges[-1]
        timeout_names = {
            "timeout:home": self.home,
            "clock:timeout:home": self.home,
            "timeout:away": self.away,
            "clock:timeout:away": self.away,
        }
        if charge.method in timeout_names:
            return (
                f"{timeout_names[charge.method]} timeout used; "
                f"this play took {charge.seconds} seconds."
            )
        return None


class RegulationGame:
    """Own toss, clock choices, period boundaries and post-score scheduling."""

    def __init__(
        self,
        home: TeamChart,
        away: TeamChart,
        seed: int,
        clock: Clock,
        dice: DiceSource | None,
        game_type: str = "regular",
        *,
        advanced_ii: bool = False,
        home_privileges: tuple[str, ...] = (),
        away_privileges: tuple[str, ...] = (),
    ) -> None:
        if not 1940 <= home.season <= 2023:
            raise ValueError("regulation requires a supported home season (1940–2023)")
        self._session = PlaySession.new(
            home,
            away,
            seed=seed,
            advanced_ii=advanced_ii,
            home_privileges=home_privileges,
            away_privileges=away_privileges,
        )
        self._names = {Possession.HOME: home.name, Possession.AWAY: away.name}
        self._season = home.season
        self._game_type = GameType(game_type)
        self._ot_profile = overtime_profile(home.season, self._game_type)
        self._overtime: OvertimeState | None = None
        self._ot_toss_rolls: tuple[OffensiveRoll, ...] = ()
        self._ot_toss_winner: Possession | None = None
        self._clock = clock
        self._dice = RandomDice(Random(seed))
        source = dice or self._dice
        rolls = []
        for _ in range(100):
            first, second = source.offensive(), source.offensive()
            rolls.extend((first, second))
            if first.total != second.total:
                self._toss_winner = (
                    Possession.HOME if first.total > second.total else Possession.AWAY
                )
                break
        else:
            raise ValueError("opening toss tie limit exceeded")
        self._toss_rolls = tuple(rolls)
        self._opening_kicker: Possession | None = None
        self._phase = RegulationPhase.OPENING
        self._hurried = False
        self._bounds_declaration: BoundsDeclaration | None = None
        self._armed_timeout: Possession | None = None
        self._untimed = False
        self._pending_timing_seconds = 0
        self._last_report: PlayReport | None = None
        self._kick_after: tuple[Possession, bool] | None = None
        self._timing_log: tuple[TimeCharge, ...] = ()
        self._legacy_halftime_view: RegulationView | None = None
        self._legacy_halftime_choice_pending = False

    def _consume_legacy_halftime_choice(self, choice: str) -> bool:
        """Replay an old save's choice when it matches the newly fixed kickoff."""
        if not self._legacy_halftime_choice_pending:
            return False
        self._legacy_halftime_choice_pending = False
        if choice not in {"half:receive", "half:kick"} or self._opening_kicker is None:
            return False
        old_chooser = self._toss_winner.other
        old_kicker = old_chooser if choice == "half:kick" else old_chooser.other
        return old_kicker is self._opening_kicker.other

    @classmethod
    def new(
        cls,
        home: TeamChart,
        away: TeamChart,
        *,
        seed: int,
        clock: Clock | None = None,
        dice: DiceSource | None = None,
        game_type: str = "regular",
        advanced_ii: bool = False,
        home_privileges: tuple[str, ...] = (),
        away_privileges: tuple[str, ...] = (),
    ) -> "RegulationGame":
        return cls(
            home,
            away,
            seed,
            clock or Clock(),
            dice,
            game_type,
            advanced_ii=advanced_ii,
            home_privileges=home_privileges,
            away_privileges=away_privileges,
        )

    def _own_pending(self) -> PendingDecisionView | None:
        if self._phase is RegulationPhase.OVERTIME_CHOICE:
            return PendingDecisionView(
                self._names[self._ot_toss_winner],
                (
                    PenaltyChoice("ot:offense", "Play offense first", True),
                    PenaltyChoice("ot:defense", "Play defense first", True),
                ),
                chooser_side=self._ot_toss_winner.value,
            )
        if self._phase in {RegulationPhase.OPENING, RegulationPhase.HALFTIME}:
            opening = self._phase is RegulationPhase.OPENING
            chooser = self._toss_winner if opening else self._toss_winner.other
            prefix = "toss" if opening else "half"
            return PendingDecisionView(
                self._names[chooser],
                (
                    PenaltyChoice(f"{prefix}:receive", "Receive the kickoff", True),
                    PenaltyChoice(f"{prefix}:kick", "Kick off", True),
                ),
                chooser_side=chooser.value,
            )
        if self._phase is RegulationPhase.CLOCK:
            choices = []
            for team, available in zip(Possession, self._clock.timeouts, strict=True):
                if available:
                    choices.append(
                        PenaltyChoice(
                            f"clock:timeout:{team.value}",
                            f"{self._names[team]} timeout; play takes 10 seconds",
                            True,
                        )
                    )
            if self._can_adjust_offense():
                if self._pending_timing_seconds == 30 and self._clock.remaining > 20:
                    choices.append(
                        PenaltyChoice("clock:hurry", "Hurry next snap; play takes 20 seconds", True)
                    )
                if self._pending_timing_seconds == 30 and self._clock.remaining > 30:
                    choices.append(
                        PenaltyChoice(
                            "clock:delay",
                            "Take 5 yards; prior play takes 40 seconds",
                            True,
                        )
                    )
                if self._session.view().state.down < 4 and self._armed_timeout is None:
                    choices.append(
                        PenaltyChoice(
                            "clock:spike", "Spike next; combined plays save 10 seconds", True
                        )
                    )
            if not choices:
                return None
            return PendingDecisionView(
                "Clock management",
                tuple(choices),
                chooser_side=self._session.view().state.possession,
            )
        return None

    def _can_adjust_offense(self) -> bool:
        state = self._session.view().state
        before = self._last_report.state_before if self._last_report else None
        return (
            state is not None
            and before is not None
            and state.possession == before.possession
            and not self._hurried
            and self._last_report.called_play not in {"Kneel", "Spike"}
        )

    def can_kneel_out_game(self) -> bool:
        """Whether the offense can safely end regulation by kneeling.

        The query assumes the opponent uses each available timeout when it
        shortens a pending timing interval to 10 seconds. It checks each
        possible kneel prefix so a later safety cannot be hidden by an earlier
        safe kneel.
        """
        if self._phase not in {RegulationPhase.LIVE, RegulationPhase.CLOCK}:
            return False
        if self._overtime is not None:
            return False

        base = self._session.view()
        state = base.state
        if state is None:
            return False
        possession = Possession(state.possession)
        if possession is Possession.HOME:
            leading = base.score.home > base.score.away
            opponent_timeouts = self._clock.timeouts[1]
        else:
            leading = base.score.away > base.score.home
            opponent_timeouts = self._clock.timeouts[0]
        if not leading or self._clock.quarter != 4:
            return False

        remaining = self._clock.remaining
        if self._phase is RegulationPhase.CLOCK:
            if opponent_timeouts and self._pending_timing_seconds > TIMEOUT_SECONDS:
                remaining -= TIMEOUT_SECONDS
                opponent_timeouts -= 1
            else:
                remaining -= self._pending_timing_seconds
        if remaining <= 0:
            return False

        kneel_seconds = duration(TimingFacts(), self._clock)
        # An armed offensive timeout shortens the first kneel too. Defensive
        # armed timeouts are already counted among the opponent's timeouts.
        if self._armed_timeout is possession:
            opponent_timeouts += 1
        max_kneels = 4 - state.down
        for kneels in range(1, max_kneels + 1):
            if state.yards_to_goal + 2 * kneels > 99:
                break
            elapsed = kneels * kneel_seconds - (kneel_seconds - TIMEOUT_SECONDS) * min(
                kneels, opponent_timeouts
            )
            if remaining <= elapsed:
                return True
        return False

    def view(self) -> RegulationView:
        base = self._session.view()
        pending = self._own_pending() or base.pending
        ot = self._overtime
        if (
            ot
            and base.phase == "conversion_choice"
            and self._ot_profile.mandatory_two(ot.round_number)
        ):
            pending = replace(
                pending,
                choices=tuple(
                    replace(
                        c, enabled=False, reason="This overtime round requires a two-point try."
                    )
                    if c.id == "conversion:kick"
                    else c
                    for c in pending.choices
                ),
            )
        clock_optional = self._phase is RegulationPhase.CLOCK
        normal_timing_ends_period = (
            clock_optional and self._clock.remaining <= self._pending_timing_seconds
        )
        effective_clock = (
            self._clock.elapse(self._pending_timing_seconds)
            if clock_optional and not normal_timing_ends_period
            else self._clock
        )
        finished = self._phase is RegulationPhase.FINAL
        phase = (
            base.phase
            if self._phase in {RegulationPhase.LIVE, RegulationPhase.OVERTIME}
            else self._phase.value
        )
        actions = base.actions
        if (pending and not clock_optional) or finished:
            actions = Actions((), (), ())
        elif self._phase is RegulationPhase.KICKOFF:
            actions = Actions((), (), base.actions.special)
        game_actions = []
        if (
            (not pending or clock_optional)
            and not finished
            and self._phase in {RegulationPhase.LIVE, RegulationPhase.CLOCK}
            and base.state is not None
        ):
            if base.phase == "scrimmage":
                if not normal_timing_ends_period and not self._untimed:
                    for team, available in zip(Possession, self._clock.timeouts, strict=True):
                        if available and self._armed_timeout in {None, team}:
                            label = (
                                f"Cancel {self._names[team]} timeout"
                                if self._armed_timeout is team
                                else f"Use {self._names[team]} timeout on next play"
                            )
                            game_actions.append(
                                Action(
                                    f"timeout:{team.value}",
                                    f"{label} ({available})",
                                )
                            )
                game_actions.append(Action("kneel", "Kneel"))
                game_actions.append(Action("elect_safety", "Elect a safety"))
                if (
                    effective_clock.quarter in {2, 4}
                    and 0 < effective_clock.remaining <= 20
                    and not self._untimed
                ):
                    game_actions.append(Action("hail_mary", "Hail Mary"))
                if not normal_timing_ends_period:
                    game_actions.extend(
                        (
                            Action("bounds:oob", "Declare out of bounds"),
                            Action("bounds:ib", "Declare in bounds"),
                        )
                    )
        status = base.status
        if self._phase is RegulationPhase.OPENING:
            status = (
                f"{self._names[self._toss_winner]} won the opening toss; choose kick or receive."
            )
        elif self._phase is RegulationPhase.KICKOFF:
            status = (
                f"{pending.chooser} chooses how to receive the kickoff."
                if pending is not None and pending.chooser is not None
                else "Kickoff required before scrimmage play."
            )
        elif self._phase is RegulationPhase.CLOCK:
            if normal_timing_ends_period and self._clock.quarter in {1, 3}:
                status = (
                    "Normal timing ends this quarter; the next play starts in the next quarter."
                )
            elif normal_timing_ends_period:
                status = "Normal timing ends this period before another play can run."
            else:
                status = (
                    "Choose the next play; normal timing applies automatically. "
                    "Optional clock modifiers are available."
                )
        elif self._phase is RegulationPhase.HALFTIME:
            status = f"Halftime: {self._names[self._toss_winner.other]} chooses kick or receive."
        elif self._phase is RegulationPhase.FINAL:
            status = "Final: overtime is complete." if ot else "Final: regulation is complete."
        elif self._phase is RegulationPhase.OVERTIME_CHOICE:
            status = (
                f"Regulation tied. {self._names[self._ot_toss_winner]} won the overtime toss; "
                "choose offense or defense first."
            )
        elif self._phase is RegulationPhase.OVERTIME:
            kind = (
                "Paired two-point try"
                if self._ot_profile.paired_tries(ot.round_number)
                else "Possession series"
            )
            status = f"OT{ot.round_number}: {kind} {ot.series_number}/2. {base.status}"
            if pending is None:
                game_actions = [
                    Action(f"timeout:{team.value}", f"{self._names[team]} timeout ({available})")
                    for team, available in zip(Possession, ot.timeouts, strict=True)
                    if available
                ]
                if base.phase == "scrimmage":
                    game_actions.append(Action("kneel", "Kneel"))
                    game_actions.append(Action("elect_safety", "Elect a safety"))
                    game_actions.extend(
                        (
                            Action("bounds:oob", "Declare out of bounds"),
                            Action("bounds:ib", "Declare in bounds"),
                        )
                    )
            if base.phase == "conversion_choice" and self._ot_profile.mandatory_two(
                ot.round_number
            ):
                status = f"OT{ot.round_number}: a two-point conversion is required."
        elif self._untimed:
            status = "Untimed down: the quarter cannot end on an accepted defensive penalty."
        if self._hurried:
            status += " Hurry-up is committed for the next snap."
        labels = {
            "clock:hurry": "Hurry-up",
            "clock:spike": "Spike",
            "clock:delay": "Intentional delay",
        }
        for team, available in zip(Possession, self._clock.timeouts, strict=True):
            labels[f"clock:timeout:{team.value}"] = f"{self._names[team]} timeout ({available})"
        modifiers = (
            tuple(PenaltyChoice(c.id, labels[c.id], c.enabled, c.reason) for c in pending.choices)
            if self._phase is RegulationPhase.CLOCK and pending
            else ()
        )
        values = {field.name: getattr(base, field.name) for field in fields(SessionView)}
        values.update(
            phase=phase,
            status=status,
            pending=None if finished else pending,
            finished=finished,
            actions=actions,
        )
        clock_view = (
            ClockView(
                self._clock.quarter,
                self._clock.remaining,
                self._clock.quarter_label,
                self._clock.label,
                self._clock.timeouts,
            )
            if ot is None
            else ClockView(4, 0, f"OT{ot.round_number}", "Untimed", ot.timeouts)
        )
        defense_name = (
            self._names[Possession(base.state.possession).other] if base.state is not None else None
        )
        return RegulationView(
            **values,
            clock=clock_view,
            defense_name=defense_name,
            home_timeouts=clock_view.timeouts[0],
            away_timeouts=clock_view.timeouts[1],
            can_kneel_out_game=self.can_kneel_out_game(),
            game_actions=tuple(game_actions),
            toss_rolls=self._toss_rolls,
            rules_season=self._season,
            opening_kicker=self._opening_kicker.value if self._opening_kicker else None,
            hurried=self._hurried,
            untimed_down=self._untimed,
            timing_log=self._timing_log,
            clock_optional=clock_optional,
            clock_modifiers=modifiers,
            bounds_declaration=(
                self._bounds_declaration.value if self._bounds_declaration is not None else None
            ),
            play_modifiers=(
                (
                    PenaltyChoice("bounds:oob", "Out of bounds", True),
                    PenaltyChoice("bounds:ib", "In bounds", True),
                )
                if any(a.key.startswith("bounds:") for a in game_actions)
                else ()
            ),
            game_type=self._game_type.value,
            armed_timeout=self._armed_timeout.value if self._armed_timeout else None,
            armed_timeout_label=(
                f"{self._names[self._armed_timeout]} timeout selected for this play; "
                "it will take 10 seconds after the required decision is complete."
                if self._armed_timeout and base.pending and not clock_optional
                else f"{self._names[self._armed_timeout]} timeout selected for the next play; "
                "that play takes 10 seconds."
                if self._armed_timeout
                else None
            ),
            clock_timing_label=(
                "Previous play timing is pending: normal timing is "
                f"{self._pending_timing_seconds} seconds. Clock options adjust that play; "
                "selecting a play applies its normal timing first."
                if clock_optional
                else None
            ),
            overtime=(
                OvertimeView(
                    ot.round_number,
                    ot.series_number,
                    ot.first.value,
                    ot.offense.value,
                    self._ot_profile.paired_tries(ot.round_number),
                    self._ot_profile.mandatory_two(ot.round_number),
                )
                if ot
                else None
            ),
            overtime_toss_rolls=self._ot_toss_rolls,
            toss_dice=tuple(roll_view(roll) for roll in self._toss_rolls),
            overtime_toss_dice=tuple(roll_view(roll) for roll in self._ot_toss_rolls),
        )

    def _guard(self) -> None:
        if self.view().finished:
            raise SessionFinishedError("regulation has ended")
        if self._own_pending() is not None:
            raise PendingDecisionError("resolve the pending regulation choice first")

    def _commit_pending_timing(self) -> PlayReport | None:
        """Commit prior-play timing; Q1/Q3 transitions continue with the selected play."""
        if self._phase is not RegulationPhase.CLOCK:
            return None
        quarter = self._clock.quarter
        self._phase = RegulationPhase.LIVE
        self._charge(self._pending_timing_seconds, "standard")
        self._advance()
        if self._clock.quarter != quarter and quarter in {1, 3}:
            return None
        if self._clock.quarter != quarter or self._phase is not RegulationPhase.LIVE:
            report = self._last_report
            if report is None:
                return None
            return replace(
                report,
                outcome="period_boundary",
                called_play="Period end",
                resolved_play="Period end",
                defense="No formation",
                yards=None,
                trace=(),
                state_before=report.state_after or report.state_before,
                state_after=self._session.view().state,
                description=(
                    "The prior play's normal timing ended this period; no new play was run. "
                    f"{self.view().status}"
                ),
                timing=TimingFacts(),
                statistics=PlayStatistics(),
                extends_quarter=False,
            )
        return None

    def snap(self, play: str, formation: str, *, dice: DiceSource | None = None) -> PlayReport:
        self._legacy_halftime_choice_pending = False
        if self._phase is RegulationPhase.CLOCK:
            actions = self._session.view().actions
            if play not in {a.key for a in actions.offense} or formation not in {
                a.key for a in actions.defense
            }:
                raise InvalidDecisionError("choose a legal play and defense before continuing")
            stopped = self._commit_pending_timing()
            if stopped is not None:
                return stopped
        self._guard()
        if self._phase is RegulationPhase.KICKOFF:
            raise PendingDecisionError("the kickoff must be completed first")
        before = self._session.view()
        report = self._session.snap(
            play,
            formation,
            dice=dice or self._dice,
            hurried=self._hurried,
            bounds_declaration=self._bounds_declaration,
        )
        if report.supported:
            self._hurried = False
        return self._after(before, report)

    def kick(self, action: str, *, dice: DiceSource | None = None) -> PlayReport:
        self._legacy_halftime_choice_pending = False
        if self._phase is RegulationPhase.CLOCK:
            if action not in {a.key for a in self._session.view().actions.special}:
                raise InvalidDecisionError("that special-teams action is unavailable")
            stopped = self._commit_pending_timing()
            if stopped is not None:
                return stopped
        self._guard()
        if self._phase is RegulationPhase.OVERTIME and action not in {
            a.key for a in self.view().actions.special
        }:
            raise InvalidDecisionError("that special-teams action is unavailable in overtime")
        before = self._session.view()
        report = self._session.kick(action, dice=dice or self._dice, hurried=self._hurried)
        if report.supported:
            self._hurried = False
            self._bounds_declaration = None
        return self._after(before, report)

    def decide(self, choice: str, *, dice: DiceSource | None = None) -> PlayReport | None:
        self._legacy_halftime_choice_pending = False
        if self.view().finished:
            raise SessionFinishedError("regulation has ended")
        if self._phase is RegulationPhase.CLOCK and choice == "clock:runoff":
            # Keep replay compatibility for older saves; this is no longer an
            # offered game action. Normal timing commits when the next action is submitted.
            self._phase = RegulationPhase.LIVE
            self._charge(self._pending_timing_seconds, "standard")
            self._advance()
            return self._last_report
        if self._phase is RegulationPhase.OVERTIME and choice == "conversion:kick":
            if self._ot_profile.mandatory_two(self._overtime.round_number):
                raise InvalidDecisionError("this overtime round requires a two-point try")
        pending = self._own_pending()
        if pending is not None:
            if choice not in {c.id for c in pending.choices if c.enabled}:
                raise InvalidDecisionError("unknown or unavailable regulation choice")
            if self._phase is RegulationPhase.OVERTIME_CHOICE:
                first = (
                    self._ot_toss_winner if choice == "ot:offense" else self._ot_toss_winner.other
                )
                self._overtime = OvertimeState(first)
                self._phase = RegulationPhase.OVERTIME
                self._start_ot_series()
                return self._last_report
            if self._phase in {RegulationPhase.OPENING, RegulationPhase.HALFTIME}:
                opening = self._phase is RegulationPhase.OPENING
                chooser = self._toss_winner if opening else self._toss_winner.other
                kicker = chooser if choice.endswith(":kick") else chooser.other
                if opening:
                    self._opening_kicker = kicker
                else:
                    self._clock = self._clock.next_quarter()
                self._session.prepare_kickoff(kicker)
                self._phase = RegulationPhase.KICKOFF
                return self._last_report
            seconds = self._pending_timing_seconds
            if choice.startswith("clock:timeout:"):
                self._clock = self._clock.timeout(Possession(choice.split(":")[-1]))
                if self._armed_timeout is not None:
                    index = 0 if self._armed_timeout is Possession.HOME else 1
                    if not self._clock.timeouts[index]:
                        self._armed_timeout = None
                seconds = TIMEOUT_SECONDS
            elif choice == "clock:hurry":
                self._hurried = True
                seconds = 20
            elif choice == "clock:spike":
                seconds -= 10
                self._last_report = self._session.automatic("spike")
                if self._last_report.timing.change_of_possession:
                    seconds = min(seconds, 10)
            elif choice == "clock:delay":
                self._phase = RegulationPhase.LIVE
                self._pending_timing_seconds = 0
                self._charge(40, choice)
                if self._clock.remaining > 0:
                    self._last_report = self._session.intentional_delay()
                self._advance()
                return self._last_report
            self._phase = RegulationPhase.LIVE
            self._charge(seconds, choice)
            self._advance()
            return self._last_report
        before = self._session.view()
        report = self._session.decide(choice, dice=dice or self._dice)
        return self._after(before, report)

    def action(self, action: str, *, dice: DiceSource | None = None) -> PlayReport | None:
        self._legacy_halftime_choice_pending = False
        if action.startswith("timeout:") and self._phase is not RegulationPhase.OVERTIME:
            if self.view().finished:
                raise SessionFinishedError("regulation has ended")
            if action not in {a.key for a in self.view().game_actions}:
                raise InvalidDecisionError("that game action is unavailable")
            team = Possession(action.split(":")[1])
            self._armed_timeout = None if self._armed_timeout is team else team
            return None
        if self._phase is RegulationPhase.CLOCK:
            if action not in {a.key for a in self.view().game_actions}:
                raise InvalidDecisionError("that game action is unavailable")
            stopped = self._commit_pending_timing()
            if stopped is not None:
                return stopped
        self._guard()
        if action not in {a.key for a in self.view().game_actions}:
            raise InvalidDecisionError("that game action is unavailable")
        if action in {"bounds:oob", "bounds:ib"}:
            requested = (
                BoundsDeclaration.OUT_OF_BOUNDS
                if action == "bounds:oob"
                else BoundsDeclaration.IN_BOUNDS
            )
            self._bounds_declaration = None if self._bounds_declaration is requested else requested
            return None
        if self._phase is RegulationPhase.OVERTIME and action.startswith("timeout:"):
            team = Possession(action.split(":")[1])
            self._overtime = self._overtime.timeout(team)
            return self._last_report
        before = self._session.view()
        report = (
            self._session.automatic("kneel")
            if action == "kneel"
            else self._session.elect_safety()
            if action == "elect_safety"
            else self._session.snap(
                "8",
                "A",
                dice=dice or self._dice,
                hurried=self._hurried,
                hail_mary=True,
                bounds_declaration=self._bounds_declaration,
            )
        )
        if report.supported:
            self._hurried = False
        return self._after(before, report)

    def _after(self, before: SessionView, report: PlayReport) -> PlayReport:
        self._last_report = report
        current = self._session.view()
        if report.pending or not report.supported or len(current.log) == len(before.log):
            return report
        self._bounds_declaration = None
        if self._phase is RegulationPhase.OVERTIME:
            self._after_overtime(before, current, report)
            return report
        if current.scoring and current.scoring[-1].play_number == report.number:
            event = current.scoring[-1]
            if event.kind in {"touchdown", "field_goal", "safety"}:
                scorer = (
                    Possession.HOME if current.score.home > before.score.home else Possession.AWAY
                )
                self._kick_after = (
                    (scorer.other, True) if event.kind == "safety" else (scorer, False)
                )
        conversion = before.phase in {"conversion_choice", "two_point_try"}
        seconds = 0 if conversion or self._untimed else duration(report.timing, self._clock)
        timeout = self._armed_timeout
        self._armed_timeout = None
        if report.timing.no_elapsed_time:
            timeout = None
        if timeout is not None:
            self._clock = self._clock.timeout(timeout)
            seconds = TIMEOUT_SECONDS
        self._untimed = False
        if self._phase is RegulationPhase.KICKOFF:
            self._phase = RegulationPhase.LIVE
        if seconds > 10 and not conversion:
            self._pending_timing_seconds = seconds
            self._phase = RegulationPhase.CLOCK
        else:
            self._charge(seconds, f"timeout:{timeout.value}" if timeout else "standard")
            self._untimed = report.extends_quarter and not conversion and self._clock.remaining == 0
            self._advance()
        return report

    def _charge(self, seconds: int, method: str) -> None:
        before = self._clock
        self._clock = before.elapse(seconds)
        self._timing_log = (
            *self._timing_log,
            TimeCharge(
                self._last_report.number,
                before.quarter,
                before.remaining,
                seconds,
                self._clock.remaining,
                method,
            ),
        )

    def _advance(self) -> None:
        base = self._session.view()
        if base.phase in {"conversion_choice", "two_point_try"}:
            return
        if self._clock.remaining == 0:
            if self._untimed:
                return
            self._hurried = False
            self._armed_timeout = None
            if self._clock.quarter == 2:
                self._phase = RegulationPhase.HALFTIME
                self._kick_after = None
                self._legacy_halftime_view = self.view()
                if self._opening_kicker is None:
                    raise RuntimeError("halftime reached before the opening kickoff")
                self._clock = self._clock.next_quarter()
                self._session.prepare_kickoff(self._opening_kicker.other)
                self._phase = RegulationPhase.KICKOFF
                self._legacy_halftime_choice_pending = True
                self._pending_timing_seconds = 0
                return
            if self._clock.quarter == 4:
                tied = base.score.home == base.score.away
                if tied and self._ot_profile.enabled:
                    self._begin_overtime()
                else:
                    self._phase = RegulationPhase.FINAL
                self._kick_after = None
                return
            self._clock = self._clock.next_quarter()
        if self._kick_after is not None:
            team, safety = self._kick_after
            self._session.prepare_kickoff(team, safety=safety)
            self._kick_after = None
            self._phase = RegulationPhase.KICKOFF

    def _begin_overtime(self) -> None:
        """Use a fresh, recorded Bowl Bound dice toss; do not reuse the opening winner."""
        rolls = []
        for _ in range(100):
            home, away = self._dice.offensive(), self._dice.offensive()
            rolls.extend((home, away))
            if home.total != away.total:
                self._ot_toss_winner = (
                    Possession.HOME if home.total > away.total else Possession.AWAY
                )
                break
        else:
            raise ValueError("overtime toss tie limit exceeded")
        self._ot_toss_rolls = tuple(rolls)
        self._phase = RegulationPhase.OVERTIME_CHOICE
        self._hurried = False
        self._untimed = False
        self._pending_timing_seconds = 0

    def _start_ot_series(self) -> None:
        ot = self._overtime
        assert ot is not None
        self._session.prepare_series(
            ot.offense, try_only=self._ot_profile.paired_tries(ot.round_number)
        )

    def _after_overtime(
        self, before: SessionView, current: SessionView, report: PlayReport
    ) -> None:
        """Finish the live return/try before advancing the alternating series."""
        ot = self._overtime
        assert ot is not None
        conversion = before.phase in {"conversion_choice", "two_point_try"}
        events = current.scoring[len(before.scoring) :]
        if not conversion:
            if any(e.team != self._names[ot.offense] for e in events):
                self._phase = RegulationPhase.FINAL
                return
            totals = (current.score.home, current.score.away)
            index = 0 if ot.offense is Possession.HOME else 1
            if ot.series_number == 2 and totals[index] > totals[1 - index]:
                self._phase = RegulationPhase.FINAL
                return
        if current.phase == "conversion_choice" or (
            current.phase == "two_point_try" and not current.finished
        ):
            return
        ended = (
            current.finished
            or report.timing.change_of_possession
            or current.state is not None
            and current.state.possession != ot.offense.value
        )
        if not ended:
            return
        if ot.series_number == 2 and current.score.home != current.score.away:
            self._phase = RegulationPhase.FINAL
            return
        self._overtime = ot.next_series()
        self._start_ot_series()
