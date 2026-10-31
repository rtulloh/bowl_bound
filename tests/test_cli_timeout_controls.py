"""Timeout controls use offense/defense roles, never home/away key aliases."""

import pytest

from bowl_bound.save_game import dumps_game, loads_game
from bowl_bound.timing import Clock
from tests.test_cli import saved_facts
from tests.test_cli_shortcuts import live, regulation


@pytest.mark.parametrize("call,role", [("7", "offense"), ("A", "defense")])
def test_call_timeout_suffix_matches_separate_engine_offered_timeout(call: str, role: str) -> None:
    app = regulation(Clock(1, 30))
    reference = regulation(Clock(1, 30))
    live(app)
    live(reference)
    if role == "defense":
        possession = app.game.view().state.possession
        app.human_side = "away" if possession == "home" else "home"
        reference.human_side = app.human_side

    side_index = 0 if app.human_side == "home" else 1
    remaining = app.game.view().clock.timeouts[side_index]
    app.display()
    assert "Add T to a play" not in app.output.getvalue()

    assert app.command(f"{call}T")
    assert reference.command(call)
    reference.advance_computer()
    assert "T" in reference._shortcuts(*reference.public_view())
    assert reference.command("T")

    assert saved_facts(app.game) == saved_facts(reference.game)
    assert app.game.view().clock.timeouts[side_index] == remaining - 1


def test_call_timeout_suffix_does_not_invent_an_unavailable_timeout() -> None:
    app = regulation(Clock(1, 30, (0, 0)))
    live(app)
    before = len(app.game.view().log)
    app.display()
    assert "Append T to your call" not in app.output.getvalue()

    assert app.command("7T")

    assert len(app.game.view().log) == before + 1
    assert app.game.view().clock.timeouts == (0, 0)
    assert "Play applied; your timeout was not offered" in app.output.getvalue()


@pytest.mark.parametrize("suffix", ["0T", "7TT", "GT", "7Z"])
def test_invalid_timeout_suffix_does_not_change_game(suffix: str) -> None:
    app = regulation()
    live(app)
    before = saved_facts(app.game)

    assert not app.command(suffix)

    assert saved_facts(app.game) == before
    assert "Not applied:" in app.output.getvalue()


def test_timeout_suffix_is_documented_in_both_help_views() -> None:
    app = regulation()
    live(app)

    app.display()
    assert "Add T to a play" not in app.output.getvalue()
    assert not app.command("?")
    assert "Add T to a play or formation key" in app.output.getvalue()
    assert not app.command("commands")
    assert "7T or AT" in app.output.getvalue()


@pytest.mark.parametrize("role", ["offense", "defense"])
def test_single_human_timeout_key_on_either_side_of_ball(role: str) -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    possession = app.game.view().state.possession
    app.human_side = (
        possession if role == "offense" else ("away" if possession == "home" else "home")
    )
    if app.public_view()[1].automatic:
        app.advance_computer()
    view, turn = app.public_view()
    binding = app._shortcuts(view, turn)["T"]
    before = saved_facts(app.game)
    assert not app.command("?")
    text = app.output.getvalue()
    assert "[T]" in text and "[TH]" not in text and "[TA]" not in text
    for legacy in ("TH", "TA", "TO", "TD"):
        assert not app.command(legacy)
        assert saved_facts(app.game) == before
    reference = loads_game(dumps_game(app.game), app.load_team)
    operation = "decide" if binding[0] == "choose" else binding[0]
    reference.coach_execute(app.human_side, operation, binding[1])
    assert app.command("T")
    assert saved_facts(app.game) == saved_facts(reference)


def test_no_two_sided_timeout_shortcuts_are_advertised() -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    before = saved_facts(app.game)
    assert not app.command("?")
    text = app.output.getvalue()
    assert "[T]" in text and "[TO]" not in text and "[TD]" not in text
    assert "[TH]" not in text and "[TA]" not in text
    assert not app.command("TH") and not app.command("TA")
    assert saved_facts(app.game) == before


def test_defender_can_still_call_timeout_when_normal_timing_would_end_the_period() -> None:
    from bowl_bound.timing import Clock

    app = regulation(Clock(1, 20))
    live(app)
    assert app.command("1")
    possession = app.game.view().state.possession
    app.human_side = "away" if possession == "home" else "home"
    view, turn = app.public_view()
    assert view.clock_optional and turn.human_role == "defense" and not turn.automatic
    assert {c.id for c in turn.pending.choices} == {f"clock:timeout:{app.human_side}"}
    reference = loads_game(dumps_game(app.game), app.load_team)
    reference.coach_execute(app.human_side, "decide", f"clock:timeout:{app.human_side}")
    assert app.command("T")
    assert saved_facts(app.game) == saved_facts(reference)
    assert app.game.view().clock.quarter == 1 and app.game.view().clock.remaining == 10


@pytest.mark.parametrize("cpu_role", ["offense", "defense"])
def test_computer_can_call_only_its_own_legal_timeout(
    cpu_role: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = regulation()
    live(app)
    assert app.command("1")
    possession = app.game.view().state.possession
    other = "away" if possession == "home" else "home"
    app.human_side = other if cpu_role == "offense" else possession
    cpu = possession if cpu_role == "offense" else other

    def timeout(observation) -> str:
        target = f"clock:timeout:{observation.side}"
        return target if target in observation.choices else observation.choices[0]

    monkeypatch.setattr(app.game._coach, "decision", timeout)
    before = app.game.view()
    reference = loads_game(dumps_game(app.game), app.load_team)
    reference.execute_with_view("decide", [f"clock:timeout:{cpu}"])
    app.advance_computer()
    assert saved_facts(app.game) == saved_facts(reference)
    after = app.game.view()
    assert after.clock.remaining == before.clock.remaining - 10
    assert after.clock.timeouts[0 if cpu == "home" else 1] == 2
    assert after.clock.timeouts[0 if app.human_side == "home" else 1] == 3
