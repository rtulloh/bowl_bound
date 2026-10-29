"""Synthetic penalty assessment and accepted-enforcement coverage."""

from itertools import product

import pytest

from bowl_bound.dice import (
    BLACK_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    OffensiveRoll,
    ScriptedDice,
)
from bowl_bound.game_state import FieldState, Possession
from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam, VariableReference
from bowl_bound.penalty_yardage import (
    AssessedPenalty,
    assess_penalty,
    enforce_penalty,
    enforce_return_penalty,
)


def data(team: PenaltyTeam, code: PenaltyCode, yards: int | None = None) -> PenaltyData:
    return PenaltyData(team, code, yards=yards)


def expected(team: PenaltyTeam, code: PenaltyCode, total: int) -> tuple[int, bool, bool, bool]:
    if code is PenaltyCode.S:
        if team is PenaltyTeam.OFFENSE:
            if total <= 19:
                return 5, False, False, False
            if total <= 32:
                return 5, False, False, True
            if total <= 36:
                return 10, False, False, False
            return 15, False, False, False
        if total <= 24 or 30 <= total <= 32:
            return 5, False, False, False
        if total <= 29:
            return 5, False, True, False
        if total == 33:
            return 10, False, False, False
        return 15, True, True, False
    if team is PenaltyTeam.OFFENSE:
        if total <= 19:
            return 5, False, False, False
        if total <= 29:
            return 15, False, False, False
        return 10, False, False, False
    if total <= 19:
        return 10, False, False, False
    if total <= 29:
        return 5, False, True, False
    return 15, True, True, False


@pytest.mark.parametrize("team,code", tuple(product(PenaltyTeam, (PenaltyCode.S, PenaltyCode.R))))
def test_table_assessment_covers_every_physical_offensive_roll(
    team: PenaltyTeam, code: PenaltyCode
) -> None:
    penalty = data(team, code)
    for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        roll = OffensiveRoll(*faces)
        assessed = assess_penalty(penalty, ScriptedDice([roll]))
        actual = (
            assessed.yards,
            assessed.automatic_first_down,
            assessed.from_end_of_gain,
            assessed.pre_snap,
        )
        assert actual == expected(team, code, roll.total)
        assert assessed.roll == roll


def assess(team: PenaltyTeam, code: PenaltyCode, roll: OffensiveRoll) -> AssessedPenalty:
    return assess_penalty(data(team, code), ScriptedDice([roll]))


def test_numeric_table_boundaries_and_fixed_forms() -> None:
    assert assess(PenaltyTeam.OFFENSE, PenaltyCode.S, OffensiveRoll(2, 3, 0)).pre_snap
    assert assess(PenaltyTeam.OFFENSE, PenaltyCode.S, OffensiveRoll(3, 3, 0)).yards == 10
    assert assess(PenaltyTeam.DEFENSE, PenaltyCode.S, OffensiveRoll(3, 3, 0)).yards == 10
    assert assess(PenaltyTeam.DEFENSE, PenaltyCode.S, OffensiveRoll(3, 4, 0)).automatic_first_down

    fixed = data(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 15)
    assert assess_penalty(fixed, ScriptedDice([])) == AssessedPenalty(fixed, 15, True, True)
    for code in (PenaltyCode.FIVE_YARDS, PenaltyCode.FIVE_YARDS_X):
        assessed = assess_penalty(data(PenaltyTeam.DEFENSE, code), ScriptedDice([]))
        assert (assessed.yards, assessed.automatic_first_down, assessed.from_end_of_gain) == (
            5,
            False,
            True,
        )


@pytest.mark.parametrize(
    "reference",
    (VariableReference.DS, VariableReference.X, VariableReference.T1),
)
def test_variable_pass_interference_assesses_every_physical_roll(
    reference: VariableReference,
) -> None:
    penalty = PenaltyData(
        PenaltyTeam.DEFENSE, PenaltyCode.PI, variable=reference, variable_multiplier=1
    )
    for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES):
        roll = OffensiveRoll(*faces)
        assessed = assess_penalty(penalty, ScriptedDice([roll]))
        raw = {
            VariableReference.DS: roll.direct_sum,
            VariableReference.X: 40 - roll.total,
            VariableReference.T1: roll.total,
        }[reference]
        assert assessed.yards == min(15, max(0, raw))
        assert assessed.source is penalty
        assert assessed.roll is None
        assert assessed.distance_rolls == (roll,)


def test_variable_pass_interference_assesses_t2_t3_and_negative_distances() -> None:
    first = OffensiveRoll(1, 0, 0)
    second = OffensiveRoll(2, 0, 0)
    third = OffensiveRoll(3, 0, 0)
    t2 = PenaltyData(
        PenaltyTeam.DEFENSE, PenaltyCode.PI, variable=VariableReference.T2, variable_multiplier=1
    )
    assessed_t2 = assess_penalty(t2, ScriptedDice([first, second]))
    assert assessed_t2.yards == 15
    assert assessed_t2.distance_rolls == (first, second)

    negative_t3 = PenaltyData(
        PenaltyTeam.DEFENSE, PenaltyCode.PI, variable=VariableReference.T3, variable_multiplier=-1
    )
    assessed_t3 = assess_penalty(negative_t3, ScriptedDice([first, second, third]))
    assert assessed_t3.yards == 0
    assert assessed_t3.distance_rolls == (first, second, third)


def test_fixed_pass_interference_and_invalid_five_yard_form() -> None:
    fixed_pi = data(PenaltyTeam.DEFENSE, PenaltyCode.PI, 20)
    assert assess_penalty(fixed_pi, ScriptedDice([])).yards == 15

    with pytest.raises(ValueError, match="offensive"):
        assess_penalty(data(PenaltyTeam.OFFENSE, PenaltyCode.FIVE_YARDS), ScriptedDice([]))


def test_enforcement_replays_down_preserves_line_to_gain_and_awards_first_down() -> None:
    state = FieldState(Possession.HOME, 60, 3, 7)
    ordinary = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 5), 5)
    assert enforce_penalty(state, ordinary) == FieldState(Possession.HOME, 55, 3, 2)

    automatic = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 15), 15, True, True)
    assert enforce_penalty(state, automatic) == FieldState(Possession.HOME, 45, 1, 10)


def test_enforcement_uses_end_of_gain_half_distance_and_pi_goal_rule() -> None:
    state = FieldState(Possession.AWAY, 20, 2, 8)
    end_gain = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.S), 5, from_end_of_gain=True)
    assert enforce_penalty(state, end_gain, gain=4, from_end=True) == FieldState(
        Possession.AWAY, 11, 1, 10
    )

    defense_15 = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 15), 15)
    assert enforce_penalty(FieldState(Possession.AWAY, 5, 2, 3), defense_15) == FieldState(
        Possession.AWAY, 3, 2, 1
    )

    pi = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.PI, 15), 15, True)
    assert enforce_penalty(FieldState(Possession.AWAY, 10, 2, 8), pi) == FieldState(
        Possession.AWAY, 2, 1, 2
    )
    assert enforce_penalty(FieldState(Possession.AWAY, 2, 2, 2), pi) == FieldState(
        Possession.AWAY, 1, 1, 1
    )


def test_converted_pass_interference_uses_defense_ten_yard_enforcement() -> None:
    source = data(PenaltyTeam.DEFENSE, PenaltyCode.PI, 15)
    normal = AssessedPenalty(source, 15, automatic_first_down=True)
    converted = AssessedPenalty(source, 10, pi_as_def10=True)
    state = FieldState(Possession.HOME, 10, 2, 8)

    assert enforce_penalty(state, normal) == FieldState(Possession.HOME, 2, 1, 2)
    assert enforce_penalty(state, converted) == FieldState(Possession.HOME, 5, 2, 3)


def test_end_of_gain_enforcement_rejects_a_scoring_gain() -> None:
    penalty = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.S), 5, from_end_of_gain=True)
    with pytest.raises(ValueError, match="touchdown"):
        enforce_penalty(FieldState(Possession.HOME, 4, 1, 4), penalty, gain=4, from_end=True)


def test_a_loss_is_never_marked_from_the_end_of_the_gain() -> None:
    penalty = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.S), 5, from_end_of_gain=True)
    state = FieldState(Possession.HOME, 95, 1, 10)
    assert enforce_penalty(state, penalty, gain=-5, from_end=True) == enforce_penalty(
        state, penalty
    )


def test_previous_spot_enforcement_ignores_a_cancelled_scoring_or_safety_gain() -> None:
    """Accepting a penalty cancels the play, so a touchdown or safety gain no longer matters."""
    defense = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.S), 5, from_end_of_gain=True)
    assert enforce_penalty(FieldState(Possession.HOME, 20, 2, 7), defense, gain=40) == (
        FieldState(Possession.HOME, 15, 2, 2)
    )
    offense = AssessedPenalty(data(PenaltyTeam.OFFENSE, PenaltyCode.S), 5)
    assert enforce_penalty(FieldState(Possession.HOME, 90, 2, 7), offense, gain=-30) == (
        FieldState(Possession.HOME, 95, 2, 12)
    )


def test_half_distance_applies_even_when_full_penalty_would_stay_in_field() -> None:
    from bowl_bound.game_state import FieldState, Possession
    from bowl_bound.models import PenaltyCode, PenaltyData, PenaltyTeam
    from bowl_bound.penalty_yardage import AssessedPenalty, enforce_penalty

    defense = AssessedPenalty(PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 5), 5)
    offense = AssessedPenalty(PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5), 5)
    assert enforce_penalty(FieldState(Possession.HOME, 7, 3, 5), defense) == FieldState(
        Possession.HOME, 4, 3, 2
    )
    assert enforce_penalty(FieldState(Possession.HOME, 93, 3, 5), offense) == FieldState(
        Possession.HOME, 96, 3, 8
    )


def test_return_penalties_mark_from_the_end_or_halfway_point() -> None:
    defensive = AssessedPenalty(data(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 15), 15)
    assert enforce_return_penalty(
        FieldState(Possession.AWAY, 80, 1, 10), defensive, return_yards=20
    ) == FieldState(Possession.AWAY, 45, 1, 10)

    offensive = AssessedPenalty(data(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 10), 10)
    # Basic VI-4(C)(vi): a 52-yard return from own 13 is marked from halfway.
    assert enforce_return_penalty(
        FieldState(Possession.AWAY, 87, 1, 10), offensive, return_yards=52
    ) == FieldState(Possession.AWAY, 54, 1, 10)
