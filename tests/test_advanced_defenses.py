"""Synthetic coverage for Bowl Bound Advanced II defensive choices."""

from dataclasses import replace

import pytest

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, ScriptedDice
from bowl_bound.models import (
    NormalizedCell,
    PenaltyCode,
    PenaltyData,
    PenaltyTeam,
    Play,
    ResultKind,
)
from bowl_bound.save_game import SavedGame, SaveFormatError, dumps_game, loads_game
from bowl_bound.team_csv import TeamFileMetadata
from tests.synthetic_teams import metadata, team_chart, write_team, yards


def new_game(
    *,
    start_yards_to_goal: int = 65,
    advanced_ii: bool = True,
    home_privileges: tuple[str, ...] = (),
    away_privileges: tuple[str, ...] = (),
    rolls: tuple[OffensiveRoll | DefensiveRoll, ...] = (),
) -> SavedGame:
    home = team_chart("Alpha Tech", offense=4, defense=3)
    away = team_chart("Beta State", offense=4, defense=3)
    return SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        start_yards_to_goal=start_yards_to_goal,
        advanced_ii=advanced_ii,
        home_privileges=home_privileges,
        away_privileges=away_privileges,
        dice=ScriptedDice(rolls),
    )


def test_new_game_offers_advanced_ii_calls_and_red_zone_only_inside_twenty() -> None:
    game = new_game(start_yards_to_goal=19)
    keys = {action.key for action in game.view().actions.defense}
    assert {"RUN", "PASS", "NICKEL", "REDZONE", "WC1", "WC9"} <= keys
    assert {"WC5", "WC5SOP", "WC5BLP"} <= keys

    on_twenty = new_game(start_yards_to_goal=20)
    assert "REDZONE" not in {action.key for action in on_twenty.view().actions.defense}

    outside = new_game(start_yards_to_goal=21)
    assert "REDZONE" not in {action.key for action in outside.view().actions.defense}


def test_correct_wild_card_guess_stops_play_without_consuming_dice() -> None:
    game = new_game()
    report = game.snap("1", "WC1")
    assert report.supported and report.outcome == "advance" and report.yards == 0
    assert report.trace == ()
    assert report.defense == "Conditional Wild Card: Play 1"


@pytest.mark.parametrize(
    ("away_privileges", "expected_yards"),
    [((), 8), (("W",), 4)],
)
def test_wrong_wild_card_doubles_only_for_a_conditional_team(
    away_privileges: tuple[str, ...], expected_yards: int
) -> None:
    game = new_game(away_privileges=away_privileges, rolls=(OffensiveRoll(1, 0, 0),))
    report = game.snap("1", "WC2")
    assert report.yards == expected_yards
    assert [entry.section for entry in report.trace] == ["offense"]


def test_correct_wild_card_pass_is_incomplete_without_dice() -> None:
    game = new_game()
    report = game.snap("9", "WC9")
    assert report.statistics.kind.value == "incomplete"
    assert report.trace == ()


@pytest.mark.parametrize(
    ("call", "cell_kind", "resolved", "outcome"),
    [
        ("WC5", ResultKind.YARDS, "Option", "advance"),
        ("WC5SOP", ResultKind.SPRINT_OUT_PASS, "Sprint Out", "advance"),
        ("WC5BLP", ResultKind.BOOTLEG_PASS, "Boot-leg", "advance"),
    ],
)
def test_correct_option_wild_card_stops_after_the_branch_roll(
    call: str, cell_kind: ResultKind, resolved: str, outcome: str
) -> None:
    play_five = (
        yards(4)
        if cell_kind is ResultKind.YARDS
        else NormalizedCell(cell_kind, metadata().evidence[0][1])
    )
    game = SavedGame.new(
        team_chart("Alpha Tech", plays={Play.FIVE: play_five}),
        team_chart("Beta State"),
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        advanced_ii=True,
        dice=ScriptedDice((OffensiveRoll(1, 0, 0),)),
    )
    report = game.snap("5", call)
    assert report.resolved_play == resolved
    assert report.outcome == outcome
    assert [entry.section for entry in report.trace] == ["offense"]
    if cell_kind is ResultKind.YARDS:
        assert report.yards == 0
    else:
        assert report.statistics.kind.value == "incomplete"


def test_incorrect_option_wild_card_rerolls_against_blank_and_applies_conditional_double() -> None:
    bootleg = NormalizedCell(ResultKind.BOOTLEG_PASS, metadata().evidence[0][1])
    game = SavedGame.new(
        team_chart("Alpha Tech", plays={Play.FIVE: bootleg}),
        team_chart("Beta State"),
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        advanced_ii=True,
        dice=ScriptedDice((OffensiveRoll(1, 0, 0), OffensiveRoll(1, 0, 0))),
    )
    report = game.snap("5", "WC5SOP")
    assert report.resolved_play == "Boot-leg"
    assert report.yards == 8
    assert [entry.section for entry in report.trace] == ["offense", "option"]


@pytest.mark.parametrize("call", ("WC1", "WC2", "WC3", "WC4", "WC6", "WC7", "WC8", "WC9"))
@pytest.mark.parametrize(
    ("option_cell", "resolved_play", "resolved_name"),
    [
        (yards(4), Play.FIVE, "Option"),
        (
            NormalizedCell(ResultKind.SPRINT_OUT_PASS, metadata().evidence[0][1]),
            Play.SEVEN,
            "Sprint Out",
        ),
        (
            NormalizedCell(ResultKind.BOOTLEG_PASS, metadata().evidence[0][1]),
            Play.EIGHT,
            "Boot-leg",
        ),
    ],
)
@pytest.mark.parametrize(("away_privileges", "expected_yards"), [((), 8), (("W",), 4)])
def test_wrong_numbered_wild_cards_do_not_stop_any_option_branch(
    call: str,
    option_cell: NormalizedCell,
    resolved_play: Play,
    resolved_name: str,
    away_privileges: tuple[str, ...],
    expected_yards: int,
) -> None:
    plays = {Play.FIVE: option_cell}
    if resolved_play is not Play.FIVE:
        plays[resolved_play] = yards(4)
    rolls = (OffensiveRoll(1, 0, 0),) + (
        (OffensiveRoll(1, 0, 0),) if resolved_play is not Play.FIVE else ()
    )
    game = SavedGame.new(
        team_chart("Alpha Tech", plays=plays),
        team_chart("Beta State"),
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        advanced_ii=True,
        away_privileges=away_privileges,
        dice=ScriptedDice(rolls),
    )

    report = game.snap("5", call)

    assert report.resolved_play == resolved_name
    assert report.yards == expected_yards


def test_run_defense_uses_parenthesized_zero_on_defensive_roll_one() -> None:
    game = new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)))
    report = game.snap("1", "RUN")
    assert report.yards == 0
    assert [entry.section for entry in report.trace] == ["offense", "advanced_defense"]
    assert report.trace[-1].cell == "(0)"


def test_run_defense_covers_all_36_defensive_face_combinations() -> None:
    from bowl_bound.dice import GREEN_FACES, RED_FACES

    reports = [
        new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(red, green))).snap("1", "RUN")
        for red in RED_FACES
        for green in GREEN_FACES
    ]
    assert [report.yards for report in reports] == [
        0 if report.trace[-1].roll["total"] == 1 else 4 for report in reports
    ]


def test_pass_defense_makes_pass_incomplete_on_defensive_roll_one() -> None:
    game = new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)))
    report = game.snap("9", "PASS")
    assert report.outcome == "advance"
    assert report.statistics.kind.value == "incomplete"


def test_pass_defense_covers_all_36_defensive_face_combinations() -> None:
    from bowl_bound.dice import GREEN_FACES, RED_FACES

    reports = [
        new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(red, green))).snap("9", "PASS")
        for red in RED_FACES
        for green in GREEN_FACES
    ]
    assert [report.statistics.kind.value for report in reports] == [
        "incomplete" if report.trace[-1].roll["total"] == 1 else "completion" for report in reports
    ]


@pytest.mark.parametrize(
    ("call", "play", "privileges", "expected_yards"),
    [
        ("RUN", "1", (), 4),
        ("PASS", "1", (), 8),
        ("PASS", "9", (), 4),
        ("RUN", "9", (), 8),
        ("PASS", "1", ("W",), 4),
        ("RUN", "9", ("W",), 4),
    ],
)
def test_run_and_pass_conditional_calls_double_only_wrong_guesses(
    call: str, play: str, privileges: tuple[str, ...], expected_yards: int
) -> None:
    game = new_game(
        away_privileges=privileges,
        rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(2, 0)),
    )
    report = game.snap(play, call)
    assert report.yards == expected_yards


@pytest.mark.parametrize(("call", "expected_yards"), [("RUN", 8), ("PASS", 4)])
def test_screen_is_a_pass_for_conditional_run_pass_guesses(call: str, expected_yards: int) -> None:
    game = new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0)))
    report = game.snap("6", call)
    assert report.yards == expected_yards
    assert report.trace[-1].cell == "blank"


def test_conditional_guess_never_doubles_negative_yardage() -> None:
    home = team_chart("Alpha Tech", plays={Play.ONE: yards(-3)})
    away = team_chart("Beta State")
    game = SavedGame.new(
        home,
        away,
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        advanced_ii=True,
        dice=ScriptedDice((OffensiveRoll(1, 0, 0), DefensiveRoll(2, 0))),
    )
    assert game.snap("1", "PASS").yards == -3


def test_nickel_zone_adds_two_yards_against_run_on_rolls_one_through_five() -> None:
    game = new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(2, 0)))
    report = game.snap("1", "NICKEL")
    assert report.yards == 6
    assert report.trace[-1].cell == "+2"


def test_nickel_zone_covers_all_36_defensive_face_combinations() -> None:
    from bowl_bound.dice import GREEN_FACES, RED_FACES

    outcomes = []
    for red in RED_FACES:
        for green in GREEN_FACES:
            game = new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(red, green)))
            outcomes.append(game.snap("1", "NICKEL").yards)
    assert outcomes == [6] * 36


def test_nickel_zone_covers_all_36_pass_face_combinations() -> None:
    from bowl_bound.dice import GREEN_FACES, RED_FACES

    reports = [
        new_game(rolls=(OffensiveRoll(1, 0, 0), DefensiveRoll(red, green))).snap("9", "NICKEL")
        for red in RED_FACES
        for green in GREEN_FACES
    ]
    assert [report.statistics.kind.value for report in reports] == [
        "incomplete" if report.trace[-1].roll["total"] == 1 else "completion" for report in reports
    ]


@pytest.mark.parametrize(
    ("call", "branch", "defensive_roll", "expected_yards", "incomplete"),
    [
        ("PASS", ResultKind.SPRINT_OUT_PASS, DefensiveRoll(1, 0), None, True),
        ("RUN", ResultKind.SPRINT_OUT_PASS, DefensiveRoll(2, 0), 8, False),
        ("NICKEL", ResultKind.BOOTLEG_PASS, DefensiveRoll(2, 0), 4, False),
    ],
)
def test_advanced_defenses_follow_the_option_branch_before_resolving(
    call: str,
    branch: ResultKind,
    defensive_roll: DefensiveRoll,
    expected_yards: int | None,
    incomplete: bool,
) -> None:
    option = NormalizedCell(branch, metadata().evidence[0][1])
    game = SavedGame.new(
        team_chart("Alpha Tech", plays={Play.FIVE: option}),
        team_chart("Beta State"),
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        advanced_ii=True,
        dice=ScriptedDice(
            (
                OffensiveRoll(1, 0, 0),
                defensive_roll,
                OffensiveRoll(1, 0, 0),
            )
        ),
    )

    report = game.snap("5", call)

    assert [entry.section for entry in report.trace] == [
        "offense",
        "advanced_defense",
        "option",
    ]
    assert report.resolved_play == (
        "Sprint Out" if branch is ResultKind.SPRINT_OUT_PASS else "Boot-leg"
    )
    if incomplete:
        assert report.statistics.kind.value == "incomplete"
    else:
        assert report.yards == expected_yards


@pytest.mark.parametrize("kind", [ResultKind.QUARTERBACK_RUN, ResultKind.QUARTERBACK_TRAPPED])
def test_qr_and_qt_classify_conditional_guesses_without_changing_fixed_tables(
    kind: ResultKind,
) -> None:
    cell = NormalizedCell(kind, metadata().evidence[0][1])

    def game_for(call: str, defensive_roll: DefensiveRoll) -> SavedGame:
        return SavedGame.new(
            team_chart("Alpha Tech", plays={Play.ONE: cell}),
            team_chart("Beta State"),
            home_id="2026/alpha-tech",
            away_id="2026/beta-state",
            seed=17,
            mode="drive",
            advanced_ii=True,
            dice=ScriptedDice(
                (
                    OffensiveRoll(1, 0, 0),
                    defensive_roll,
                    OffensiveRoll(1, 0, 0),
                )
            ),
        )

    pass_report = game_for("PASS", DefensiveRoll(1, 0)).snap("1", "PASS")
    assert pass_report.yards == 4
    assert [entry.section for entry in pass_report.trace] == [
        "offense",
        "advanced_defense",
        "supplemental:QR" if kind is ResultKind.QUARTERBACK_RUN else "supplemental:QT",
    ]
    assert pass_report.trace[1].cell == "blank"

    run_report = game_for("RUN", DefensiveRoll(2, 0)).snap("1", "RUN")
    assert run_report.yards == 8
    assert run_report.trace[1].cell == "blank"

    run_stop_report = game_for("RUN", DefensiveRoll(1, 0)).snap("1", "RUN")
    assert run_stop_report.trace[1].cell == "(0)"


@pytest.mark.parametrize(
    ("call", "source_play", "reroll", "result_play", "conditional_yards"),
    [
        ("RUN", Play.ONE, ResultKind.QUARTERBACK_RUN, Play.ONE, 8),
        ("RUN", Play.ONE, ResultKind.QUARTERBACK_TRAPPED, Play.ONE, 8),
        ("RUN", Play.FIVE, ResultKind.SPRINT_OUT_PASS, Play.SEVEN, 8),
        ("RUN", Play.FIVE, ResultKind.BOOTLEG_PASS, Play.EIGHT, 8),
        ("PASS", Play.ONE, ResultKind.YARDS, Play.ONE, 8),
        ("PASS", Play.FIVE, ResultKind.SPRINT_OUT_PASS, Play.SEVEN, 4),
    ],
)
@pytest.mark.parametrize("away_privileges", [(), ("W",)])
def test_penalty_reroll_reclassifies_conditional_advanced_defense(
    call: str,
    source_play: Play,
    reroll: ResultKind,
    result_play: Play,
    conditional_yards: int,
    away_privileges: tuple[str, ...],
) -> None:
    penalty = NormalizedCell(
        ResultKind.PENALTY,
        metadata().evidence[0][1],
        penalty=PenaltyData(PenaltyTeam.DEFENSE, PenaltyCode.FIXED, 5),
    )
    rerolled = (
        yards(4)
        if reroll is ResultKind.YARDS
        else NormalizedCell(reroll, metadata().evidence[0][1])
    )
    offense = team_chart("Alpha Tech", offense=0, defense=0)
    offense = replace(
        offense,
        offense=tuple(
            replace(row, cell=penalty)
            if row.play is source_play and row.roll == 10
            else replace(row, cell=rerolled)
            if row.play is source_play and row.roll == 20
            else replace(row, cell=yards(4))
            if row.play is result_play and row.roll == 10 and result_play is not Play.ONE
            else row
            for row in offense.offense
        ),
        supplemental=tuple(
            replace(row, cell=yards(4)) if row.roll == 10 else row for row in offense.supplemental
        ),
    )
    rolls = [OffensiveRoll(1, 0, 0), DefensiveRoll(2, 0), OffensiveRoll(2, 0, 0)]
    if reroll is not ResultKind.YARDS:
        rolls.append(OffensiveRoll(1, 0, 0))
    game = SavedGame.new(
        offense,
        team_chart("Beta State", offense=0, defense=0),
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        advanced_ii=True,
        away_privileges=away_privileges,
        dice=ScriptedDice(rolls),
    )

    pending = game.snap(str(source_play.value), call)
    view = game.view()
    assert view.pending is not None
    projected = next(item for item in view.pending.decision_outcomes if item.choice_id == "decline")
    report = game.decide("decline")

    assert pending.pending
    assert report.yards == (4 if away_privileges else conditional_yards)
    assert (
        projected.yards_to_goal,
        projected.down,
        projected.yards_to_go,
    ) == (
        65 - report.yards,
        2,
        10 - report.yards,
    )
    expected_play = {
        Play.SEVEN: "Sprint Out",
        Play.EIGHT: "Boot-leg",
    }.get(result_play, "Line Plunge")
    assert report.resolved_play == expected_play


def test_nickel_zone_uses_its_printed_play_range_for_qr_outcomes() -> None:
    cell = NormalizedCell(ResultKind.QUARTERBACK_RUN, metadata().evidence[0][1])
    game = SavedGame.new(
        team_chart("Alpha Tech", plays={Play.ONE: cell}),
        team_chart("Beta State"),
        home_id="2026/alpha-tech",
        away_id="2026/beta-state",
        seed=17,
        mode="drive",
        advanced_ii=True,
        dice=ScriptedDice((OffensiveRoll(1, 0, 0), DefensiveRoll(1, 0), OffensiveRoll(1, 0, 0))),
    )
    report = game.snap("1", "NICKEL")
    assert report.statistics.kind.value != "incomplete"
    assert report.trace[1].cell == "+2"


def test_red_zone_defense_uses_blank_result_without_a_defensive_roll() -> None:
    game = new_game(start_yards_to_goal=19, rolls=(OffensiveRoll(1, 0, 0),))
    report = game.snap("1", "REDZONE")
    assert report.yards == 4
    assert [entry.section for entry in report.trace] == ["offense"]


def test_w_coded_marker_is_verified_but_deferred_on_normal_save_load() -> None:
    game = new_game(away_privileges=("W",), rolls=(OffensiveRoll(1, 0, 0),))
    game.snap("1", "WC2")
    snapshot = dumps_game(game)
    home, away = team_chart("Alpha Tech"), team_chart("Beta State")

    def load(key: str):
        chart = {"2026/alpha-tech": home, "2026/beta-state": away}[key]
        markers = ("W",) if key.endswith("beta-state") else ()
        return chart, metadata_with_markers(markers)

    restored = loads_game(snapshot, load)
    assert restored.view().log == game.view().log
    assert not any(action.key.startswith("WC") for action in restored.view().actions.defense)

    with pytest.raises(SaveFormatError):
        loads_game(snapshot, lambda key: {"2026/alpha-tech": home, "2026/beta-state": away}[key])


def test_api_keeps_w_code_as_metadata_without_enabling_wild_card(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from backend.app import create_app

    seasons = tmp_path / "seasons"
    write_team(seasons, team_chart("Alpha Tech"))
    write_team(
        seasons,
        team_chart("Beta State"),
        metadata_with_markers(("W",)),
    )
    client = TestClient(create_app(seasons))
    created = client.post(
        "/api/games",
        json={"home": "2026/alpha-tech", "away": "2026/beta-state", "seed": 1},
    )
    assert created.status_code == 200
    actions = created.json()["view"]["actions"]["defense"]
    assert not any(action["key"].startswith("WC") for action in actions)

    save = client.get(f"/api/games/{created.json()['game_id']}/save")
    restored = client.post("/api/games/load", content=save.content)
    assert restored.status_code == 200
    restored_actions = restored.json()["view"]["actions"]["defense"]
    assert not any(action["key"].startswith("WC") for action in restored_actions)


def test_human_advanced_defense_does_not_break_computer_call_history() -> None:
    home = team_chart("Alpha Tech", season=2007)
    away = team_chart("Beta State", season=2007)
    game = SavedGame.new(
        home,
        away,
        home_id="2007/alpha-tech",
        away_id="2007/beta-state",
        seed=17,
        coach_seed=31,
        coach_policy="hard-v8",
        mode="drive",
        advanced_ii=True,
    )

    report, _, _, _ = game._coach_step_with_choice("away", "WC1")

    assert report is not None and report.supported
    assert game._coach._counts[("home", "offense")]
    assert game._coach._counts[("away", "defense")] == {"WC1": 1}


def metadata_with_markers(markers: tuple[str, ...]) -> TeamFileMetadata:
    return replace(metadata(), defense_chart_markers=markers)
