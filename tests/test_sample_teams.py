"""Original selectable samples must work without historical data or test helpers."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from bowl_bound.sample_teams import SOURCE_HASH, install_samples, sample_teams
from bowl_bound.team_csv import load_team


def test_samples_are_complete_distinct_original_and_round_trip(tmp_path: Path) -> None:
    charts = sample_teams()
    assert len(charts) == 2 and charts[0].name != charts[1].name
    assert charts[0].offense != charts[1].offense
    ids = install_samples(tmp_path)
    for chart, team_id in zip(charts, ids, strict=True):
        season, slug = team_id.split("/")
        restored, meta = load_team(tmp_path / season, slug)
        assert restored == chart
        assert len(restored.offense) == 270
        assert len(restored.defense) == 270
        assert len(restored.supplemental) == 90
        assert len(restored.special_teams) == 180
        assert "Original fictional" in meta.defense_label
        assert all(r.cell.provenance.filename == "sample-teams-v2" for r in chart.offense)
        assert len({r.cell.yards for r in chart.offense}) > 8
    client = TestClient(create_app(tmp_path))
    assert [t["id"] for t in client.get("/api/teams").json()["teams"]] == sorted(ids)
    for home, away in (ids, ids[::-1]):
        response = client.post(
            "/api/games", json={"home": home, "away": away, "seed": 17, "mode": "regulation"}
        )
        assert response.status_code == 200
        assert response.json()["view"]["pending"] is not None


def test_install_is_idempotent_but_never_overwrites_edits(tmp_path: Path) -> None:
    ids = install_samples(tmp_path)
    assert install_samples(tmp_path) == ids
    path = tmp_path / ids[0] / "offense.csv"
    path.write_text("owner edit", encoding="utf-8")
    with pytest.raises(FileExistsError, match="existing"):
        install_samples(tmp_path)
    assert path.read_text() == "owner edit"


def test_samples_cover_ordinary_football_events_without_being_exhaustive_stress_fixtures() -> None:
    from bowl_bound.models import PenaltyCode, PenaltyTeam, Play, ResultKind

    for chart in sample_teams():
        offense = [r.cell for r in chart.offense]
        defense = [r.cell for r in chart.defense]
        assert {
            ResultKind.YARDS,
            ResultKind.INCOMPLETE,
            ResultKind.INTERCEPTION,
            ResultKind.FUMBLE,
            ResultKind.BREAKAWAY,
            ResultKind.PENALTY,
            ResultKind.QUARTERBACK_RUN,
            ResultKind.SPRINT_OUT_PASS,
            ResultKind.BOOTLEG_PASS,
        } <= {c.kind for c in offense}
        assert {
            ResultKind.YARDS,
            ResultKind.INCOMPLETE,
            ResultKind.INTERCEPTION,
            ResultKind.FUMBLE,
            ResultKind.QUARTERBACK_TRAPPED,
        } <= {c.kind for c in defense}
        assert {PenaltyCode.FIXED, PenaltyCode.PI} == {c.penalty.code for c in offense if c.penalty}
        assert set(PenaltyTeam) == {c.penalty.team for c in offense if c.penalty}
        assert not any(c.penalty or c.kind is ResultKind.BREAKAWAY for c in defense)
        assert {ResultKind.SPRINT_OUT_PASS, ResultKind.BOOTLEG_PASS} <= {
            r.cell.kind for r in chart.offense if r.play is Play.FIVE
        }
        assert all(c.variable is None for c in (*offense, *defense))
        # All other families/priority coordinates remain covered by test_priority_matrix
        # and dedicated synthetic turnover/variable-yardage suites, not selectable teams.


@pytest.mark.parametrize("reverse", [False, True])
def test_original_samples_complete_games_and_save_continuation(reverse: bool) -> None:
    from bowl_bound.save_game import SavedGame, dumps_game, loads_game
    from bowl_bound.statistics import summarize

    teams = sample_teams()[::-1] if reverse else sample_teams()
    game = SavedGame.new(
        *teams, home_id="2007/home", away_id="2007/away", seed=39, mode="regulation"
    )
    restored = loads_game(
        dumps_game(game), lambda key: teams[0] if key.endswith("home") else teams[1]
    )
    phases = set()
    for step in range(1200):
        view = game.view()
        phases.add(view.phase)
        assert restored.view() == view
        if view.finished:
            assert "halftime_choice" in phases
            assert view.statistics == summarize(r.statistics for r in view.log)
            assert view.score.home == sum(e.points for e in view.scoring if e.team == view.home)
            assert view.score.away == sum(e.points for e in view.scoring if e.team == view.away)
            assert all(
                c.before - c.after == min(c.before, c.seconds) and c.after >= 0
                for c in view.timing_log
            )
            for quarter in range(1, 5):
                assert (
                    sum(c.before - c.after for c in view.timing_log if c.quarter == quarter) == 900
                )
            assert all(r.supported and not r.pending for r in view.log)
            return
        if view.pending and not view.clock_optional:
            choices = [c.id for c in view.pending.choices if c.enabled]
            assert choices
            choice = next(
                (
                    c
                    for c in (
                        "clock:runoff",
                        "half:receive",
                        "ot:offense",
                        "conversion:kick",
                        "kick:touchback",
                    )
                    if c in choices
                ),
                choices[0],
            )
            assert game.decide(choice) == restored.decide(choice)
        elif view.phase == "kickoff":
            assert game.kick("kickoff") == restored.kick("kickoff")
        else:
            play = str(step % 9 + 1)
            formation = "ABCDEF"[step % 6]
            report = game.snap(play, formation)
            assert report.supported, report.unsupported_reason
            assert restored.snap(play, formation) == report
        if step == 40:
            restored = loads_game(
                dumps_game(restored), lambda key: teams[0] if key.endswith("home") else teams[1]
            )
    pytest.fail("original samples failed to complete a legal game")


def test_every_sample_cell_has_a_real_priority_coordinate() -> None:
    from bowl_bound.resolution import _COLUMNS, _PRIORITY_TABLE, resolve_cells
    from bowl_bound.team_csv import parse_cell
    from tests.test_models import provenance

    for chart in sample_teams():
        blank = parse_cell("", provenance())
        rows = {resolve_cells(row.cell, blank).offense_category for row in chart.offense}
        columns = {resolve_cells(blank, row.cell).defense_category for row in chart.defense}
        assert rows <= set(_PRIORITY_TABLE)
        assert columns <= set(_COLUMNS)


def test_public_chart_bundles_match_original_recipe_and_load(tmp_path: Path) -> None:
    public = Path(__file__).resolve().parents[1] / "seasons"
    assert public.is_dir(), "Public samples must include actual chart bundles, not only a generator"
    install_samples(tmp_path)
    generated = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file())
    # Check only the explicitly public sample paths; never inspect historical folders.
    assert len(generated) == 10
    for relative in generated:
        assert (public / relative).read_bytes() == (tmp_path / relative).read_bytes()
    for chart in sample_teams():
        loaded, metadata = load_team(public / "2007", chart.name.lower().replace(" ", "-"))
        assert loaded == chart
        assert metadata.source_sha256 == SOURCE_HASH
