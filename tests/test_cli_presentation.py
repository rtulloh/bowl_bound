"""Readable public scoreboards and deterministic, optional human suggestions."""

import io
from dataclasses import replace

import pytest

from bowl_bound import coaching_session
from tests.test_cli import new_game, saved_facts, terminal
from tests.test_cli_shortcuts import live, regulation


@pytest.mark.parametrize("human", ["home", "away"])
def test_enter_submits_the_visible_recommendation_without_preview_side_effects(human: str) -> None:
    app = terminal(new_game(), human, compact=True)
    before = saved_facts(app.game)
    view, turn = app.public_view()
    recommendation = coaching_session.recommend_call(view, turn)
    assert recommendation in turn.actions.offense + turn.actions.defense
    for command in ("?", "status", "stats", "trace", "?"):
        assert not app.command(command)
        assert saved_facts(app.game) == before
    assert f"Default={recommendation.key}/{recommendation.label}" in app.output.getvalue()
    reference = terminal(new_game(), human)
    assert reference.command(recommendation.key)
    assert app.command("")
    assert saved_facts(app.game) == saved_facts(reference.game)


@pytest.mark.parametrize(
    "role,down,distance,expected",
    [
        ("offense", 1, 10, "1"),
        ("offense", 2, 2, "1"),
        ("offense", 3, 5, "6"),
        ("offense", 3, 12, "9"),
        ("defense", 1, 10, "A"),
        ("defense", 2, 2, "B"),
        ("defense", 3, 5, "D"),
        ("defense", 3, 12, "E"),
    ],
)
def test_suggestions_use_public_down_distance_and_only_legal_calls(
    role: str,
    down: int,
    distance: int,
    expected: str,
) -> None:
    app = terminal(new_game(), "home" if role == "offense" else "away")
    view, turn = app.public_view()
    view = replace(view, state=replace(view.state, down=down, yards_to_go=distance))
    assert coaching_session.recommend_call(view, turn).key == expected
    calls = turn.actions.offense if role == "offense" else turn.actions.defense
    restricted = replace(turn, actions=replace(turn.actions, **{role: (calls[-1],)}))
    assert coaching_session.recommend_call(view, restricted) == calls[-1]


def test_blank_does_not_select_a_required_decision_or_kickoff() -> None:
    app = regulation()
    for _ in range(2):
        before = saved_facts(app.game)
        assert not app.command("")
        assert saved_facts(app.game) == before
        assert not app.command("?")
        assert "Default=" not in app.output.getvalue()
        if app.game.view().phase == "opening_choice":
            assert app.command("r")
            app.human_side = app.game.view().state.possession


def test_finished_automatic_and_missing_state_have_no_suggestion() -> None:
    app = terminal(new_game(), "home")
    view, turn = app.public_view()
    for other_view, other_turn in (
        (replace(view, finished=True), turn),
        (replace(view, state=None), turn),
        (view, replace(turn, automatic=True)),
        (view, None),
    ):
        assert coaching_session.recommend_call(other_view, other_turn) is None


def test_scoreboard_is_one_line_with_timeouts_and_engine_situation_labels() -> None:
    app = regulation()
    before = saved_facts(app.game)
    app.display()
    view = app.game.view()
    clock = view.clock
    expected = (
        f"{clock.quarter_label} {clock.label} | "
        f"{view.away} {view.score.away} ({clock.timeouts[1]}) - "
        f"{view.home} {view.score.home} ({clock.timeouts[0]}) | "
        f"{view.state.situation} @ {view.state.spot} | {view.state.possession_name} ball"
    )
    assert expected in app.output.getvalue().splitlines()
    assert "Timeouts:" not in app.output.getvalue()
    assert app.output.getvalue().startswith("\n")
    assert saved_facts(app.game) == before


def test_commentary_brackets_results_without_fabricating_or_leaking_calls() -> None:
    app = terminal(new_game(), "home", compact=True)
    app.display()
    before = app.output.getvalue()
    assert "Offense:" not in before and "Defense:" not in before
    app.output = io.StringIO()
    assert app.command("1")
    report = app.last_report
    assert report is not None
    app.display()
    text = app.output.getvalue()
    assert text.startswith("\n")
    assert f"  Offense: {report.called_play}" in text
    assert f"  Defense: {report.defense}" in text
    assert f"► {report.commentary}\n  (" in text
    assert ")\n\nBeta State" in text
    assert text.count(report.description) == 1


def test_regulation_scoreboard_after_a_play_uses_new_engine_clock_and_state() -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    app.output = io.StringIO()
    app.display()
    view = app.game.view()
    assert f"{view.clock.quarter_label} {view.clock.label} |" in app.output.getvalue()
    assert f"{view.state.situation} @ {view.state.spot}" in app.output.getvalue()


def test_paused_errors_never_offer_or_submit_an_enter_default() -> None:
    app = terminal(new_game(), "home")
    app.automatic_paused = True
    before = saved_facts(app.game)
    app.display()
    assert "Default=" not in app.output.getvalue()
    assert not app.command("")
    assert saved_facts(app.game) == before and app.automatic_paused


def test_optional_clock_menu_keeps_the_visible_default_as_a_scrimmage_call() -> None:
    from bowl_bound.save_game import dumps_game, loads_game

    app = regulation()
    live(app)
    assert app.command("1")
    app.human_side = app.game.view().state.possession
    view, turn = app.public_view()
    assert view.clock_optional and view.pending
    recommendation = coaching_session.recommend_call(view, turn)
    assert recommendation in turn.actions.offense
    reference = loads_game(dumps_game(app.game), app.load_team)
    reference.coach_step(app.human_side, recommendation.key)
    app.display()
    assert f"Default={recommendation.key}/{recommendation.label}" in app.output.getvalue()
    assert app.command("")
    assert saved_facts(app.game) == saved_facts(reference)


def test_computer_runoff_does_not_repeat_the_same_play_commentary() -> None:
    app = regulation(seed=39)
    app.human_side = "home"
    commands = iter(["k", "", "quit"])
    assert app.run(lambda _: next(commands)) == 0
    assert len(app.game.view().log) == 2
    assert len({report.description for report in app.game.view().log}) == 2
    for report in app.game.view().log:
        assert app.output.getvalue().count("► " + report.description) == 1
    before = saved_facts(app.game)
    output = app.output.getvalue()
    assert not app.command("log")
    assert app.output.getvalue().startswith(output)
    assert app.game.view().log[-1].description in app.output.getvalue()[len(output) :]
    assert saved_facts(app.game) == before


def test_changed_report_is_still_shown_and_trace_remains_inspectable() -> None:
    app = terminal(new_game(), "home")
    assert app.command("1")
    report = app.last_report
    original = app.output.getvalue()
    app._report(report)
    assert app.output.getvalue() == original
    changed = replace(report, description="Synthetic finalized engine commentary", pending=False)
    app._report(changed)
    assert app.output.getvalue().count("► Synthetic finalized engine commentary") == 1
    assert app.last_report == changed
    assert not app.command("trace")
    assert "cell " in app.output.getvalue()


@pytest.mark.parametrize("human", ["home", "away"])
@pytest.mark.parametrize("compact", [False, True])
def test_routine_selection_instructions_are_not_repeated(human: str, compact: bool) -> None:
    app = terminal(new_game(), human, compact=compact)
    before = saved_facts(app.game)
    for command in ("status", "?", "status"):
        assert not app.command(command)
    text = app.output.getvalue()
    assert "Choose an offensive play and defensive formation." not in text
    assert "Choose your defensive formation; the computer offense stays hidden." not in text
    assert "Choose your offensive play; the computer defense stays hidden." not in text
    assert "ball" in text
    assert ("DEFENSIVE FORMATION" if human == "away" else "OFFENSIVE PLAY CALL") in text
    assert "Default=" in text
    assert saved_facts(app.game) == before


def test_required_and_clock_decision_instructions_remain_visible() -> None:
    app = regulation()
    app.display()
    assert app.game.view().status in app.output.getvalue()
    live(app)
    assert app.command("1")
    app.output = io.StringIO()
    before = saved_facts(app.game)
    app.display()
    assert app.game.view().clock_optional
    assert app.game.view().status in app.output.getvalue()
    assert saved_facts(app.game) == before


@pytest.mark.parametrize("human,summary", [("home", "OFF: 1-9"), ("away", "DEF: A-F")])
def test_compact_only_lists_shortcut_keys_until_help(human: str, summary: str) -> None:
    app = terminal(new_game(), human, compact=True)
    before = saved_facts(app.game)
    view, turn = app.public_view()
    default = coaching_session.recommend_call(view, turn)
    app.display()
    output = app.output.getvalue()
    assert summary in output
    assert "?=help" in output and "/" in output
    assert f"Default={default.key}/{default.label}" in output
    for action in turn.actions.offense + turn.actions.defense + turn.actions.special:
        assert f"[{action.key}] {action.label}" not in output
        assert f"(call {action.key})" not in output
    assert "QB Sneak" not in output and "onside" not in output
    if human == "away":
        assert "OFF:" not in output
        assert ",P" not in output
    assert not app.command("?")
    for action in turn.actions.offense + turn.actions.defense:
        assert f"[{action.key}] {action.label}" in app.output.getvalue()[len(output) :]
    assert saved_facts(app.game) == before


@pytest.mark.parametrize("human", ["home", "away"])
def test_compact_solitaire_never_offers_both_sets_of_calls(human: str) -> None:
    app = terminal(new_game(), human, compact=True)
    app.display()
    output = app.output.getvalue()
    assert ("OFF: 1-9" in output) == (human == "home")
    assert ("DEF: A-F" in output) == (human == "away")
    assert "1 A" not in output and "Default=" in output
    assert "[1] Line Plunge" not in output
    assert not app.command("?")
    text = app.output.getvalue()[len(output) :]
    assert ("[1] Line Plunge" in text) == (human == "home")
    assert ("[A] Standard" in text) == (human == "away")


def test_compact_optional_controls_advertise_only_offered_shortcuts() -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    app.human_side = app.game.view().state.possession
    view, turn = app.public_view()
    app.output = io.StringIO()
    before = saved_facts(app.game)
    app.display()
    text = app.output.getvalue()
    assert "OFF: 1-9" in text
    assert "N" in text and "S" in text and "T" in text
    assert "clock:hurry" not in text and "clock:spike" not in text
    assert saved_facts(app.game) == before
    assert not app.command("?")
    assert "clock:hurry" in app.output.getvalue()[len(text) :]


@pytest.mark.parametrize("human", ["home", "away"])
def test_contextual_help_has_grouped_play_menu_without_command_clutter(human: str) -> None:
    app = terminal(new_game(), human, compact=True)
    before = saved_facts(app.game)
    assert not app.command("?")
    text = app.output.getvalue()
    title = "OFFENSIVE PLAY CALL" if human == "home" else "DEFENSIVE FORMATION"
    assert title in text and "----------------------------------------" in text
    assert "OPTIONS:" in text and "[/] Stats" in text
    assert "Shortcuts: use" not in text and "Full commands still work:" not in text
    assert "(call " not in text and "(kick " not in text and "(action " not in text
    if human == "home":
        assert "RUNNING / OPTION PLAYS:" in text and "PASSING PLAYS:" in text
        assert "SPECIAL TEAMS:" in text and "[P] Punt" in text
        assert text.index("[5] Option") < text.index("PASSING PLAYS:") < text.index("[6] Screen")
        assert "Inside running play" in text
    else:
        assert "[A] Standard" in text and "[F] Blitz" in text
        assert "[P]" not in text
    assert "commands" in text
    assert saved_facts(app.game) == before


def test_commands_reference_is_separate_read_only_and_retains_full_syntax() -> None:
    app = terminal(new_game(), "home", compact=True)
    before = saved_facts(app.game)
    assert not app.command("commands")
    output = app.output.getvalue()
    assert "snap PLAY DEFENSE" not in output and "call KEY" in output and "choose ID" in output
    assert "save PATH" in output and "load PATH" in output
    assert "OFFENSIVE PLAY CALL" not in output
    assert saved_facts(app.game) == before


def test_help_groups_legal_special_plays_separately_from_special_teams() -> None:
    from bowl_bound.timing import Clock

    app = regulation(Clock(2, 10))
    live(app)
    app.human_side = app.game.view().state.possession
    assert not app.command("?")
    text = app.output.getvalue()
    assert "SPECIAL PLAYS:" in text and "SPECIAL TEAMS:" in text
    assert text.index("SPECIAL PLAYS:") < text.index("[K] Kneel") < text.index("SPECIAL TEAMS:")
    assert "[H] Hail Mary" in text
    assert "[P] Punt" in text and "[F] Field goal" in text
    assert "QB Sneak" not in text and "[Q]" not in text


@pytest.mark.parametrize(
    "human,role,keys", [("home", "OFF", ("1", "9")), ("away", "DEF", ("A", "F"))]
)
def test_compact_summary_never_claims_a_full_range_when_calls_are_restricted(
    human: str,
    role: str,
    keys: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = terminal(new_game(), human, compact=True)
    view, turn = app.public_view()
    attribute = "offense" if human == "home" else "defense"
    calls = getattr(turn.actions, attribute)
    restricted = tuple(a for a in calls if a.key in keys)
    turn = replace(turn, actions=replace(turn.actions, **{attribute: restricted}))
    monkeypatch.setattr(app, "public_view", lambda: (view, turn))
    before = saved_facts(app.game)
    app.display()
    output = app.output.getvalue()
    assert f"{role}: {','.join(keys)}" in output
    assert "1-9" not in output and "A-F" not in output
    assert not app.command("?")
    help_text = app.output.getvalue()[len(output) :]
    for call in calls:
        assert (f"[{call.key}] {call.label}" in help_text) == (call.key in keys)
    assert saved_facts(app.game) == before


def test_compact_report_shows_only_real_recorded_roll_evidence() -> None:
    app = terminal(new_game(), "home", compact=True)
    assert app.command("1")
    report = app.last_report
    output = app.output.getvalue()
    assert "  (" in output
    for entry in report.trace:
        assert f"{entry.section}:{entry.roll['total']}→{entry.cell!r}" in output
    before = saved_facts(app.game)
    assert not app.command("trace")
    for entry in report.trace:
        assert f"cell {entry.cell}" in app.output.getvalue()
    assert saved_facts(app.game) == before
