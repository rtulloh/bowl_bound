"""Visible, context-safe terminal shortcuts over unchanged public engine controls."""

import io
from dataclasses import replace

import pytest

from bowl_bound.cli import TerminalGame
from bowl_bound.models import TeamChart
from bowl_bound.save_game import SavedGame, dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.synthetic_teams import team_chart, yards
from tests.test_cli import new_game, saved_facts, terminal
from tests.test_special_teams import special_chart


def regulation(clock: Clock | None = None, *, seed: int = 7) -> TerminalGame:
    teams = tuple(
        replace(
            team_chart(name, season=2002, offense=3, defense=0),
            special_teams=special_chart(name, kickoff=yards(70)).special_teams,
        )
        for name in ("Home", "Away")
    )

    def loader(key: str) -> TeamChart:
        return teams[key.endswith("away")]

    game = SavedGame.new(
        *teams,
        home_id="2002/home",
        away_id="2002/away",
        seed=seed,
        coach_seed=31,
        mode="regulation",
        clock=clock,
    )
    return TerminalGame(
        game,
        loader,
        human_side=game.view().pending.chooser_side,
        output=io.StringIO(),
        compact=True,
    )


def live(app: TerminalGame) -> None:
    # Engine-only setup spans both teams; no two-sided terminal mode is needed.
    for operation, arguments in (
        ("decide", ["toss:receive"]),
        ("kick", ["kickoff"]),
        ("decide", ["kick:touchback"]),
    ):
        app.game.execute_with_view(operation, arguments)
    app.human_side = app.game.view().state.possession


@pytest.mark.parametrize("human,keys", [("home", "123456789"), ("away", "ABCDEF")])
def test_help_lists_every_legal_play_shortcut_and_hides_opponent(human: str, keys: str) -> None:
    app = terminal(new_game(), human, compact=True)
    before = saved_facts(app.game)
    app.automatic_paused = True
    for command in ("?", "help", "?"):
        assert not app.command(command)
    output = app.output.getvalue()
    for action in app.public_view()[1].actions.offense + app.public_view()[1].actions.defense:
        assert f"[{action.key}] {action.label}" in output
    opponent_calls = (
        app.game.view().actions.defense if human == "home" else (app.game.view().actions.offense)
    )
    for action in opponent_calls:
        assert f"[{action.key}] {action.label}" not in output
    assert all(f"[{key}] " in output for key in keys)
    assert saved_facts(app.game) == before and app.automatic_paused


@pytest.mark.parametrize(
    "key,choice",
    [("r", "toss:receive"), ("K", "toss:kick"), ("1", "toss:receive"), ("2", "toss:kick")],
)
def test_toss_shortcuts_match_explicit_engine_choice(key: str, choice: str) -> None:
    app = regulation()
    reference = loads_game(dumps_game(app.game), app.load_team)
    assert app.command(key)
    reference.execute_with_view("decide", [choice])
    if choice == "toss:kick":
        reference.execute_with_view("kick", ["kickoff"])
    assert saved_facts(app.game) == saved_facts(reference)


def test_opening_help_lists_bracketed_choices_and_does_not_duplicate_status() -> None:
    app = regulation()
    before = saved_facts(app.game)
    assert not app.command("?")
    output = app.output.getvalue()
    assert "[R]" in output and "[K]" in output
    assert "choose toss:receive" in output and "choose toss:kick" in output
    assert saved_facts(app.game) == before
    app.output = io.StringIO()
    app.human_side = app.game.view().pending.chooser_side
    app.display()
    assert app.output.getvalue().count(app.game.view().status) == 1


@pytest.mark.parametrize("key,action", [("p", "punt"), ("F", "field_goal")])
def test_offensive_special_shortcuts_match_coached_engine_calls(key: str, action: str) -> None:
    app = terminal(new_game(), "home")
    reference = new_game()
    assert app.command(key)
    reference.coach_execute("home", "kick", action)
    assert saved_facts(app.game) == saved_facts(reference)


def test_f_on_defense_is_blitz_not_a_field_goal() -> None:
    app = terminal(new_game(), "away")
    reference = new_game()
    assert app.command("f")
    reference.coach_step("away", "F")
    assert saved_facts(app.game) == saved_facts(reference)
    assert not app.command("p")


def test_k_is_a_kickoff_only_when_offered() -> None:
    app = regulation()
    assert app.command("choose toss:receive")
    app.human_side = app.game.view().state.possession
    reference = loads_game(dumps_game(app.game), app.load_team)
    app.display()
    assert "[K] Kickoff" in app.output.getvalue()
    assert "[O]" not in app.output.getvalue()  # No invented onside action.
    assert app.command("k")
    reference.execute_with_view("kick", ["kickoff"])
    assert saved_facts(app.game) == saved_facts(reference)
    before = saved_facts(app.game)
    assert not app.command("k")  # Pending reception is not another kickoff.
    assert saved_facts(app.game) == before


@pytest.mark.parametrize("key,action", [("k", "kneel"), ("h", "hail_mary")])
def test_game_play_shortcuts_only_submit_offered_engine_actions(key: str, action: str) -> None:
    app = regulation(Clock(2, 10))
    live(app)
    reference = loads_game(dumps_game(app.game), app.load_team)
    assert app.command(key)
    reference.execute_with_view("action", [action])
    assert saved_facts(app.game) == saved_facts(reference)


@pytest.mark.parametrize("key,choice", [("n", "clock:hurry"), ("s", "clock:spike")])
def test_clock_shortcuts_use_legal_choices_without_reinterpreting_timing(
    key: str, choice: str
) -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    reference = loads_game(dumps_game(app.game), app.load_team)
    assert app.command(key)
    reference.execute_with_view("decide", [choice])
    assert saved_facts(app.game) == saved_facts(reference)


def test_paired_input_is_rejected_and_each_human_call_is_fresh() -> None:
    app = terminal(new_game(), compact=True)
    app.display()
    assert "Pair fresh" not in app.output.getvalue()
    before = saved_facts(app.game)
    assert not app.command("1 a") and not app.command("snap 1 A")
    assert saved_facts(app.game) == before
    reference = new_game()
    for key in ("1", "2"):
        assert app.command(key)
        reference.coach_step("home", key)
        assert saved_facts(app.game) == saved_facts(reference)


def test_required_choice_numbers_never_become_a_scrimmage_call() -> None:
    app = terminal(new_game())
    app.game.snap("9", "A")  # Engine setup creates a required interception choice.
    app.human_side = app.game.view().pending.chooser_side
    pending = app.game.view().pending
    assert pending is not None
    index, choice = next(
        (index, choice) for index, choice in enumerate(pending.choices, 1) if choice.enabled
    )
    reference = loads_game(dumps_game(app.game), app.load_team)
    assert app.command(str(index))
    reference.execute_with_view("decide", [choice.id])
    assert saved_facts(app.game) == saved_facts(reference)


def test_disabled_choice_shortcuts_and_full_id_are_rejected_without_rolls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = regulation()
    view = app.game.view()
    disabled = replace(
        view.pending.choices[0], enabled=False, reason="synthetic unavailable choice"
    )
    public = replace(
        view, pending=replace(view.pending, choices=(disabled, *view.pending.choices[1:]))
    )
    _, turn = app.public_view()
    monkeypatch.setattr(app.game, "view", lambda: public)
    monkeypatch.setattr(app, "public_view", lambda: (public, replace(turn, pending=public.pending)))
    before = saved_facts(app.game)
    assert not app.command("?")
    assert "synthetic unavailable choice" in app.output.getvalue()
    assert "[R]" not in app.output.getvalue()
    for command in ("1", "r", "choose toss:receive"):
        assert not app.command(command)
        assert saved_facts(app.game) == before


def test_illegal_shortcuts_and_blank_input_have_no_default_or_hidden_action() -> None:
    app = regulation()
    before = saved_facts(app.game)
    for command in ("", "p", "f", "h", "o", "3", "rt", "1t"):
        assert not app.command(command)
        assert saved_facts(app.game) == before


@pytest.mark.parametrize(
    "human,key", [("home", str(key)) for key in range(1, 10)] + [("away", key) for key in "ABCDEF"]
)
def test_each_scrimmage_shortcut_matches_its_canonical_engine_id(human: str, key: str) -> None:
    app = terminal(new_game(), human)
    reference = new_game()
    assert app.command(key.lower())
    reference.coach_step(human, key)
    assert saved_facts(app.game) == saved_facts(reference)


@pytest.mark.parametrize("human", ["home", "away"])
def test_timeout_shortcut_targets_only_the_humans_offered_timeout(human: str) -> None:
    app = regulation()
    app.game.execute_with_view("decide", ["toss:receive" if human == "away" else "toss:kick"])
    app.game.execute_with_view("kick", ["kickoff"])
    app.game.execute_with_view("decide", ["kick:touchback"])
    app.game.snap("1", "A")
    app.human_side = human
    reference = loads_game(dumps_game(app.game), app.load_team)
    app.command("?")
    assert "[T]" in app.output.getvalue()
    assert app.command("t")
    reference.coach_execute(human, "decide", f"clock:timeout:{human}")
    assert saved_facts(app.game) == saved_facts(reference)


@pytest.mark.parametrize("key", ["TO", "TD", "TH", "TA"])
def test_only_t_is_offered_as_a_timeout_alias(key: str) -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    before = saved_facts(app.game)
    assert not app.command(key)
    assert not app.command("?")
    assert f"[{key}]" not in app.output.getvalue()
    assert "[T]" in app.output.getvalue()
    assert saved_facts(app.game) == before


def test_normal_optional_runoff_preserves_defensive_timeout_window() -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    app.human_side = "home"  # Away received the seed-7 toss; home is defending.
    before = saved_facts(app.game)
    view, turn = app.public_view()
    assert not turn.automatic and turn.human_role == "defense"
    assert tuple(c.id for c in turn.pending.choices) == ("clock:timeout:home",)
    assert not app.command("choose clock:hurry")
    assert not app.command("choose clock:timeout:away")
    assert saved_facts(app.game) == before
    reference = loads_game(dumps_game(app.game), app.load_team)
    assert app.command("c")
    reference.coach_step("home", "C")
    assert saved_facts(app.game) == saved_facts(reference)


def test_return_and_touchback_shortcuts_use_the_required_reception_menu() -> None:
    for key, choice in (("tb", "kick:touchback"), ("r", "kick:return")):
        app = regulation()
        assert app.command("r")
        app.human_side = app.game.view().state.possession
        assert app.command("k")
        app.human_side = app.game.view().pending.chooser_side
        reference = loads_game(dumps_game(app.game), app.load_team)
        assert app.command(key)
        reference.execute_with_view("decide", [choice])
        assert saved_facts(app.game) == saved_facts(reference)
