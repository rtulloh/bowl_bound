"""Exact, bounded FG procedure diagnostics; no historical attempt-credit policy.

The initial ordinary integer/NG census deliberately does not close adaptive
penalties, recovery chains or variable-distance procedures. Their physical mass
remains unsupported, rather than disappearing from a conditional denominator.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from itertools import product
from typing import Any

from bowl_bound.dice import (
    BLACK_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DiceSequenceError,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import NormalizedCell, ResultKind, SpecialTeamsColumn, TeamChart
from bowl_bound.session import PlaySession

from .refine import engine_identity
from .research_inputs import FrozenResearchInputs
from .runtime_identity import require_runtime_identity

_MASS_CATEGORIES = (
    "good_mass",
    "missed_mass",
    "unsupported_mass",
    "illegal_action_mass",
    "engine_error_mass",
    "unexpected_pending_mass",
    "unclassified_terminal_mass",
)


def _ordinary_initial(cell: NormalizedCell) -> bool:
    return (
        cell.kind is ResultKind.YARDS
        and type(cell.yards) is int
        or cell.kind in {ResultKind.NO_CHANGE, ResultKind.NO_GOOD_FIELD_GOAL}
    )


def _location_census(home: TeamChart, away: TeamChart, field: FieldState) -> dict[str, Any]:
    counts = dict.fromkeys(_MASS_CATEGORIES, 0)
    unsupported: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    initial = PlaySession.for_analysis(home, away, field, advanced_ii=False, overtime=False)
    if "field_goal" not in {action.key for action in initial.view().actions.special}:
        counts["illegal_action_mass"] = 216
    else:
        kicking = home if field.possession is Possession.HOME else away
        cells = {
            row.roll: row.cell
            for row in kicking.special_teams
            if row.column is SpecialTeamsColumn.FIELD_GOAL
        }
        for black, white_one, white_two in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
            roll = OffensiveRoll(black, white_one, white_two)
            cell = cells[roll.total]
            if not _ordinary_initial(cell):
                counts["unsupported_mass"] += 1
                unsupported[cell.kind.value] += 1
                continue
            session = PlaySession.for_analysis(home, away, field, advanced_ii=False, overtime=False)
            try:
                report = session.kick("field_goal", dice=ScriptedDice((roll,)))
            except (ValueError, DiceSequenceError) as error:
                counts["engine_error_mass"] += 1
                errors[type(error).__name__] += 1
                continue
            if report.pending:
                counts["unexpected_pending_mass"] += 1
            elif report.outcome == "field_goal_good":
                counts["good_mass"] += 1
            elif report.outcome == "field_goal_missed":
                counts["missed_mass"] += 1
            else:
                counts["unclassified_terminal_mass"] += 1
    accounted = sum(counts.values())
    if accounted != 216:
        raise ValueError("field-goal initial-face accounting differs from 216")
    closed = counts["good_mass"] + counts["missed_mass"]
    return {
        "initial_face_mass": 216,
        **counts,
        "accounted_mass": accounted,
        "unsupported_kinds": dict(sorted(unsupported.items())),
        "engine_error_types": dict(sorted(errors.items())),
        "numeric_conditional_numerator": counts["good_mass"],
        "numeric_conditional_denominator": closed,
        "numeric_conditional_success": counts["good_mass"] / closed if closed else None,
    }


def audit_field_goal_chart(
    kicking: TeamChart,
    receiving: TeamChart,
    *,
    yards_to_goal: Sequence[int],
    possession: Possession = Possession.HOME,
) -> dict[str, Any]:
    """Census actual legal integer/NG FG outcomes over the 216 physical faces.

    This is an isolated no-clock/no-OT procedure diagnostic. It supplies no
    historical source, general charged-FGA, expectation or accuracy authority.
    Complete chart/context facts are detached and checked before reusable return.
    """
    if not isinstance(kicking, TeamChart) or not isinstance(receiving, TeamChart):
        raise TypeError("field-goal audit requires two TeamChart inputs")
    if type(possession) is not Possession:
        raise TypeError("field-goal audit requires a Possession")
    if type(yards_to_goal) not in {list, tuple} or not yards_to_goal:
        raise ValueError("field-goal audit requires a nonempty explicit location list/tuple")
    if any(type(spot) is not int or not 1 <= spot <= 99 for spot in yards_to_goal):
        raise ValueError("field-goal audit locations must be integer LOS within 1..99")
    if len(set(yards_to_goal)) != len(yards_to_goal):
        raise ValueError("field-goal audit locations must be distinct")
    home_identity = "kicking" if possession is Possession.HOME else "receiving"
    away_identity = "receiving" if possession is Possession.HOME else "kicking"
    inputs = FrozenResearchInputs.capture(
        teams={"kicking": (kicking, None), "receiving": (receiving, None)},
        manifest={
            "yards_to_goal": yards_to_goal,
            "possession": possession,
            "advanced_ii": False,
            "overtime": False,
            "regulation_clock": None,
            "command": "field_goal",
            "decision_policy": None,
            "down": 4,
            "yards_to_go": 1,
        },
        catalog={"home": home_identity, "away": away_identity},
        targets={"source_comparability": None, "numerical_criterion": None},
    )
    engine = engine_identity()
    values = inputs.values
    context = values["manifest"]
    seats = values["catalog"]
    home = values["teams"][seats["home"]][0]
    away = values["teams"][seats["away"]][0]
    locations = {}
    try:
        for spot in context["yards_to_goal"]:
            inputs.check("field-goal context before census")
            field = FieldState(context["possession"], spot, 4, 1)
            locations[str(spot)] = _location_census(home, away, field)
    finally:
        inputs.check("field-goal diagnostic final boundary")
    current = engine_identity()
    require_runtime_identity(engine, current)
    inputs.check("field-goal diagnostic after runtime verification")
    return {
        "schema_version": 1,
        "scope": "closed_numeric_ng_only",
        "source_qualification": "unverified",
        "input_identity": inputs.identity,
        "engine": engine,
        "context": {
            **context,
            "possession": context["possession"].value,
            "seats": seats,
            "home_season": home.season,
        },
        "locations": locations,
    }
