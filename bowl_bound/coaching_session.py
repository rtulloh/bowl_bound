"""Coordinate simultaneous human/computer calls without exposing either hidden call."""

from dataclasses import dataclass, replace

from .coaching import BaselineCoach, CoachChoice, CoachObservation, safe_choice
from .regulation import RegulationView
from .session import Action, Actions, PendingDecisionView, SessionView

GameView = SessionView | RegulationView


@dataclass(frozen=True)
class CoachingTurn:
    """Public controls only; no seed, observation, private plan or computer selection."""

    human_side: str
    human_role: str
    automatic: bool
    status: str
    actions: Actions = Actions((), (), ())
    game_actions: tuple[Action, ...] = ()
    pending: PendingDecisionView | None = None


@dataclass(frozen=True)
class _Plan:
    """Server-only plan. Serialize turn, never this object, to a browser."""

    turn: CoachingTurn
    operation: str | None = None
    arguments: tuple[str | None, ...] = ()
    human_legal: tuple[str, ...] = ()
    computer_choice: CoachChoice | None = None


def observe_game(view: GameView, side: str) -> CoachObservation:
    """Build the public coaching allowlist without charts, live dice or hidden calls."""
    state = view.state
    clock = getattr(view, "clock", None)
    difference = view.score.home - view.score.away
    return CoachObservation(
        side=side,
        possession=state.possession if state else "",
        down=state.down if state else 0,
        distance=state.yards_to_go if state else 0,
        yards_to_goal=state.yards_to_goal if state else 0,
        quarter=clock.quarter if clock else 1,
        remaining=clock.remaining if clock else 900,
        score_difference=difference if side == "home" else -difference,
        play_number=len(view.log),
        overtime=getattr(view, "overtime", None) is not None,
        hurried=getattr(view, "hurried", False),
        phase=view.phase,
        offense=tuple(a.key for a in view.actions.offense),
        defense=tuple(a.key for a in view.actions.defense),
        special=tuple(a.key for a in view.actions.special),
        game_actions=tuple(
            a.key
            for a in getattr(view, "game_actions", ())
            if not a.key.startswith("timeout:") or a.key == f"timeout:{side}"
        ),
        choices=tuple(
            c.id
            for c in view.pending.choices
            if c.enabled
            and (not c.id.startswith("clock:timeout:") or c.id == f"clock:timeout:{side}")
        )
        if view.pending
        else (),
    )


# Compatibility for original test/integration imports; production uses the public name.
_observation = observe_game


def _selection(coach: BaselineCoach, candidate: str, legal: tuple[str, ...]) -> CoachChoice:
    choice = safe_choice(candidate, legal)
    return replace(choice, fallback=choice.fallback or coach.analysis_fallback)


def plan_turn(view: GameView, human_side: str, coach: BaselineCoach) -> _Plan:
    """Plan from public facts alone; no parameter accepts the human selected call."""
    if human_side not in {"home", "away"}:
        raise ValueError("human side must be home or away")
    cpu = "away" if human_side == "home" else "home"
    if view.finished:
        return _Plan(CoachingTurn(human_side, "final", False, view.status))
    pending = view.pending
    if pending is not None:
        if pending.chooser_side not in {"home", "away"}:
            raise ValueError("engine decision is missing explicit side ownership")
        if view.phase == "clock_choice":
            observation = observe_game(view, cpu)
            legal = observation.choices + ("clock:standard",)
            if pending.chooser_side == human_side:
                # A computer defender can use only its own timeout, not offensive
                # hurry-up or spike. Normal timing is the implicit default.
                legal = tuple(key for key in observation.choices if key == f"clock:timeout:{cpu}")
                legal += ("clock:standard",)
            choice = _selection(coach, coach.decision(replace(observation, choices=legal)), legal)
            if choice.key != "clock:standard":
                return _Plan(
                    CoachingTurn(human_side, "computer", True, "Computer is deciding."),
                    "decide",
                    (choice.key,),
                    computer_choice=choice,
                )
            allowed = observe_game(view, human_side).choices
            if pending.chooser_side != human_side:
                allowed = tuple(key for key in allowed if key == f"clock:timeout:{human_side}")
            pending = replace(
                pending,
                chooser_side=human_side,
                choices=tuple(c for c in pending.choices if c.id in allowed),
            )
            if not pending.choices:
                pending = None
        else:
            if pending.chooser_side == cpu:
                observation = observe_game(view, cpu)
                choice = _selection(coach, coach.decision(observation), observation.choices)
                return _Plan(
                    CoachingTurn(human_side, "computer", True, "Computer is deciding."),
                    "decide",
                    (choice.key,),
                    computer_choice=choice,
                )
            return _Plan(CoachingTurn(human_side, "decision", False, view.status, pending=pending))
        if not getattr(view, "clock_optional", False):
            return _Plan(CoachingTurn(human_side, "decision", False, view.status, pending=pending))
    if view.state is None:
        raise ValueError("engine offered no state or required decision")
    human_actions = tuple(
        a
        for a in getattr(view, "game_actions", ())
        if a.key == f"timeout:{human_side}"
        or (view.state.possession == human_side and not a.key.startswith("timeout:"))
    )
    if view.state.possession == human_side:
        turn = CoachingTurn(
            human_side,
            "offense",
            False,
            "Choose your offensive play; the computer defense stays hidden.",
            Actions(view.actions.offense, (), view.actions.special),
            human_actions,
            pending,
        )
        if not view.actions.offense:
            return _Plan(turn)  # A human kickoff needs no defensive call.
        observation = observe_game(view, cpu)
        choice = _selection(coach, coach.defense(observation), observation.defense)
        return _Plan(
            turn, "snap", (None, choice.key), tuple(a.key for a in view.actions.offense), choice
        )
    observation = observe_game(view, cpu)
    legal = observation.offense + observation.special + observation.game_actions
    choice = _selection(coach, coach.offense(observation), legal)
    if choice.key in observation.offense:
        return _Plan(
            CoachingTurn(
                human_side,
                "defense",
                False,
                "Choose your defensive formation; the computer offense stays hidden.",
                Actions((), view.actions.defense),
                human_actions,
                pending,
            ),
            "snap",
            (choice.key, None),
            observation.defense,
            choice,
        )
    operation = "kick" if choice.key in observation.special else "action"
    return _Plan(
        CoachingTurn(human_side, "computer", True, "Computer is playing."),
        operation,
        (choice.key,),
        computer_choice=choice,
    )


def recommend_call(view: GameView, turn: CoachingTurn | None) -> Action | None:
    """Suggest a legal human scrimmage call from public down/distance, without RNG.

    This conservative convenience policy is separate from the computer opponent:
    first downs favor balanced calls; short yardage favors the line/gaps; later
    passing downs favor screen/short prevent or drop back/long prevent. Never
    default a required decision, kickoff, or two-sided manual submission.
    """
    if view.finished or view.state is None or turn is None or turn.automatic:
        return None
    if view.pending and not getattr(view, "clock_optional", False):
        return None
    state = view.state
    if turn.human_role == "offense":
        calls = turn.actions.offense
        preferred = (
            "1"
            if state.down == 1 or state.yards_to_go <= 3
            else ("9" if state.yards_to_go > 7 else "6")
        )
    elif turn.human_role == "defense":
        calls = turn.actions.defense
        preferred = (
            "B"
            if state.yards_to_go <= 3
            else (
                "E"
                if state.down >= 3 and state.yards_to_go > 7
                else ("D" if state.down >= 2 else "A")
            )
        )
    else:
        return None
    return next((call for call in calls if call.key == preferred), calls[0] if calls else None)
