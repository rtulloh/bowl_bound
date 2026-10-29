"""Exact published dice odds and deterministic roll-source contracts."""

from collections import Counter
from itertools import product
from random import Random

import pytest

from bowl_bound.dice import (
    BLACK_FACES,
    GREEN_FACES,
    RED_FACES,
    WHITE_ONE_FACES,
    WHITE_TWO_FACES,
    DefensiveRoll,
    DiceSequenceError,
    OffensiveRoll,
    RandomDice,
    ScriptedDice,
)


def test_offensive_faces_and_all_216_combinations() -> None:
    assert Counter(BLACK_FACES) == {1: 1, 2: 2, 3: 3}
    assert Counter(WHITE_ONE_FACES) == {0: 2, 1: 1, 2: 1, 3: 1, 4: 1}
    assert Counter(WHITE_TWO_FACES) == dict.fromkeys(range(6), 1)
    counts = Counter(
        OffensiveRoll(*faces).total
        for faces in product(BLACK_FACES, WHITE_ONE_FACES, WHITE_TWO_FACES)
    )
    # Rulebook IV-1(A) table, not derived from the implementation constants.
    ones_counts = (2, 3, 4, 5, 6, 6, 4, 3, 2, 1)
    expected = {
        10 * tens + ones: count * tens
        for tens in (1, 2, 3)
        for ones, count in enumerate(ones_counts)
    }
    assert counts == expected
    assert sum(counts.values()) == 216


def test_defensive_faces_and_all_36_combinations() -> None:
    assert Counter(RED_FACES) == {1: 3, 2: 2, 3: 1}
    assert Counter(GREEN_FACES) == {0: 4, 1: 1, 2: 1}
    counts = Counter(DefensiveRoll(*faces).total for faces in product(RED_FACES, GREEN_FACES))
    assert counts == {1: 12, 2: 11, 3: 9, 4: 3, 5: 1}
    assert sum(counts.values()) == 36


def test_offensive_roll_preserves_faces_for_direct_sum() -> None:
    roll = OffensiveRoll(3, 2, 5)
    assert roll.total == 37
    assert roll.direct_sum == 10
    assert (roll.black, roll.white_one, roll.white_two) == (3, 2, 5)


@pytest.mark.parametrize(
    "faces",
    [(0, 0, 0), (4, 0, 0), (1, 5, 0), (1, 0, 6), (True, 0, 0), (1, 0.0, 0), (1, 0, "1")],
)
def test_offensive_roll_rejects_invalid_faces(faces: tuple[object, ...]) -> None:
    with pytest.raises(ValueError, match="face"):
        OffensiveRoll(*faces)


@pytest.mark.parametrize("faces", [(0, 0), (4, 0), (1, -1), (1, 3), (True, 0), (1, 1.0)])
def test_defensive_roll_rejects_invalid_faces(faces: tuple[object, ...]) -> None:
    with pytest.raises(ValueError, match="face"):
        DefensiveRoll(*faces)


def test_seeded_random_sources_are_repeatable_and_use_actual_faces() -> None:
    left, right = RandomDice(Random(73)), RandomDice(Random(73))
    for _ in range(300):
        offense = left.offensive()
        assert offense == right.offensive()
        assert offense.black in BLACK_FACES
        assert offense.white_one in WHITE_ONE_FACES
        assert offense.white_two in WHITE_TWO_FACES
        defense = left.defensive()
        assert defense == right.defensive()
        assert defense.red in RED_FACES
        assert defense.green in GREEN_FACES


def test_random_source_samples_six_face_positions_not_uniform_totals() -> None:
    rng = Random(91)
    expected_rng = Random(91)
    source = RandomDice(rng)
    for _ in range(50):
        assert source.offensive() == OffensiveRoll(
            expected_rng.choice(BLACK_FACES),
            expected_rng.choice(WHITE_ONE_FACES),
            expected_rng.choice(WHITE_TWO_FACES),
        )
        assert source.defensive() == DefensiveRoll(
            expected_rng.choice(RED_FACES), expected_rng.choice(GREEN_FACES)
        )


def test_scripted_source_checks_order_and_does_not_consume_on_wrong_kind() -> None:
    offense, defense = OffensiveRoll(1, 0, 0), DefensiveRoll(3, 2)
    source = ScriptedDice((offense, defense, offense))
    with pytest.raises(DiceSequenceError, match="offensive"):
        source.defensive()
    assert source.offensive() is offense
    assert source.defensive() is defense
    assert source.offensive() is offense
    with pytest.raises(DiceSequenceError, match="exhausted"):
        source.offensive()
    with pytest.raises(DiceSequenceError, match="exhausted"):
        source.defensive()


def test_empty_script_fails_instead_of_fabricating_a_roll() -> None:
    with pytest.raises(DiceSequenceError, match="exhausted"):
        ScriptedDice(()).offensive()


def test_script_rejects_non_roll_entries() -> None:
    with pytest.raises(ValueError, match="roll"):
        ScriptedDice((12,))


def test_script_copies_input_instead_of_retaining_mutable_list() -> None:
    roll = OffensiveRoll(2, 0, 1)
    entries = [roll]
    source = ScriptedDice(entries)
    entries.clear()
    assert source.offensive() is roll
    with pytest.raises(DiceSequenceError, match="exhausted"):
        source.offensive()


def test_rolls_are_immutable() -> None:
    from dataclasses import FrozenInstanceError

    offense = OffensiveRoll(1, 0, 0)
    defense = DefensiveRoll(1, 0)
    with pytest.raises(FrozenInstanceError):
        offense.black = 3
    with pytest.raises(FrozenInstanceError):
        defense.red = 3
