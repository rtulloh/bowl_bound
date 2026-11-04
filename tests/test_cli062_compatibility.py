"""An authentic pre-fix save using only invented teams and chart cells."""

from dataclasses import replace
from pathlib import Path

from bowl_bound.models import NormalizedCell, Play, ResultKind, TeamChart
from bowl_bound.save_game import SavedGame, _view_digest, dumps_game, loads_game
from bowl_bound.team_csv import format_cell
from tests.synthetic_teams import default_teams
from tests.test_models import provenance


def test_pre_fix_pending_zero_choice_save_replays_with_original_chart_facts() -> None:
    home, away = (replace(chart, season=2002) for chart in default_teams())
    cell = NormalizedCell(ResultKind.NO_CHANGE, provenance(), out_of_bounds=True)
    home = replace(
        home,
        offense=tuple(
            replace(row, cell=cell) if row.play is Play.TWO else row for row in home.offense
        ),
    )

    def loader(key: str) -> TeamChart:
        return home if key.endswith("alpha-tech") else away

    raw = (Path(__file__).parent / "fixtures" / "cli062-pending-razzle.json").read_text()
    restored = loads_game(raw, loader)
    decision = restored.view().pending
    choice = next(item for item in decision.choices if item.id.startswith("razzle:2:"))
    assert choice.label.endswith(": 0")
    assert choice.presentation_value == "0"
    assert format_cell(cell) == "*"

    # Legal decision IDs and enabled state still participate in the save digest.
    view = restored.view()
    for changed in (replace(choice, id="razzle:invalid"), replace(choice, enabled=False)):
        pending = replace(
            decision,
            choices=tuple(changed if item.id == choice.id else item for item in decision.choices),
        )
        assert _view_digest(replace(view, pending=pending)) != _view_digest(view)

    reference = SavedGame.new(
        home, away, home_id="2002/alpha-tech", away_id="2002/beta-state", seed=7, coach_seed=31
    )
    reference.execute_with_view("snap", ["RZDZ", "A"])
    restored.execute_with_view("decide", [choice.id])
    reference.execute_with_view("decide", [choice.id])
    assert restored.view() == reference.view()
    assert loads_game(dumps_game(restored), loader).view() == restored.view()
    assert any(entry.cell == "*" for entry in restored.view().log[-1].trace)
