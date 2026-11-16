"""Engine-owned rules summaries stay aligned with the gameplay boundaries."""

import pytest

from bowl_bound.rules_summary import rules_summary


@pytest.mark.parametrize(
    ("season", "game_type", "kickoff", "touchback", "overtime"),
    [
        (1985, "regular", "Kickoffs from the 40", "touchback to the 20", "No overtime"),
        (2002, "regular", "Kickoffs from the 35", "touchback to the 20", "tries from OT3"),
        (2007, "regular", "Kickoffs from the 30", "touchback to the 20", "tries from OT3"),
        (2012, "regular", "Kickoffs from the 35", "touchback to the 25", "tries from OT3"),
        (2021, "regular", "Kickoffs from the 35", "touchback to the 25", "paired tries from OT3"),
    ],
)
def test_summary_matches_engine_boundaries(
    season: int, game_type: str, kickoff: str, touchback: str, overtime: str
) -> None:
    summary = rules_summary(season, game_type)
    assert summary.supported
    assert summary.summary == f"{season} home-season rules govern this game."
    assert kickoff in summary.details
    assert any(touchback in detail for detail in summary.details)
    assert any(overtime in detail for detail in summary.details)


def test_unsupported_season_is_explicit() -> None:
    summary = rules_summary(2024, "regular")
    assert not summary.supported
    assert summary.details == ()
    # The message must name the season and the supported range so the player
    # knows why Start is unavailable.
    assert "2024" in summary.summary
    assert "1940" in summary.summary and "2023" in summary.summary


def test_unknown_game_type_is_unsupported() -> None:
    summary = rules_summary(2007, "exhibition")
    assert not summary.supported
    assert "exhibition" in summary.summary
