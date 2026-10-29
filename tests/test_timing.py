"""Standard Bowl Bound timing: synthetic facts, never prose or UI calculations."""

from dataclasses import FrozenInstanceError

import pytest

from bowl_bound.game_state import Possession
from bowl_bound.timing import Clock, TimingFacts, duration


@pytest.mark.parametrize(
    ("facts", "seconds"),
    [
        (TimingFacts(), 30),
        (TimingFacts(first_down=True), 20),
        (TimingFacts(change_of_possession=True), 10),
        (TimingFacts(penalty=True), 10),
        (TimingFacts(incomplete=True), 10),
        (TimingFacts(scoring=True), 10),
        (TimingFacts(touchback=True), 10),
        (TimingFacts(unreturned_kickoff=True), 0),
        (TimingFacts(conversion=True), 0),
        (TimingFacts(first_down=True, penalty=True), 10),
        (TimingFacts(conversion=True, penalty=True), 0),
    ],
)
def test_standard_chart_uses_shortest_category(facts: TimingFacts, seconds: int) -> None:
    assert duration(facts, Clock()) == seconds


@pytest.mark.parametrize(
    ("quarter", "remaining", "expected"),
    [
        (1, 60, 30),
        (2, 121, 30),
        (2, 120, 10),
        (2, 1, 10),
        (3, 60, 30),
        (4, 301, 30),
        (4, 300, 10),
        (4, 1, 10),
    ],
)
def test_non_kicking_out_of_bounds_windows(quarter: int, remaining: int, expected: int) -> None:
    assert duration(TimingFacts(out_of_bounds=True), Clock(quarter, remaining)) == expected


def test_clock_never_adds_a_two_minute_warning_or_spills_into_next_quarter() -> None:
    assert Clock(2, 130).elapse(30).remaining == 100
    expired = Clock(1, 10).elapse(30)
    assert expired.remaining == 0 and expired.quarter == 1
    advanced = expired.next_quarter()
    assert advanced.quarter == 2 and advanced.remaining == 900


def test_timeouts_are_three_per_team_per_half_with_no_carryover() -> None:
    clock = Clock()
    for remaining in (2, 1, 0):
        clock = clock.timeout(Possession.AWAY)
        assert clock.timeouts == (3, remaining)
    with pytest.raises(ValueError, match="timeout"):
        clock.timeout(Possession.AWAY)
    second_half = Clock(2, 0, clock.timeouts).next_quarter()
    assert second_half.timeouts == (3, 3) and second_half.quarter == 3


def test_clock_view_is_engine_formatted_and_immutable() -> None:
    clock = Clock(4, 65)
    assert clock.label == "1:05" and clock.quarter_label == "Q4"
    with pytest.raises(FrozenInstanceError):
        clock.remaining = 1


@pytest.mark.parametrize(
    ("quarter", "remaining"), [(0, 900), (5, 900), (1, -1), (1, 901), (True, 1)]
)
def test_invalid_clock_state_is_rejected(quarter: int, remaining: int) -> None:
    with pytest.raises(ValueError):
        Clock(quarter, remaining)


def test_no_quarter_advance_while_time_remains_or_after_regulation() -> None:
    with pytest.raises(ValueError):
        Clock().next_quarter()
    with pytest.raises(ValueError):
        Clock(4, 0).next_quarter()
