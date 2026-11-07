# Milestone 44 — Explicit cross-year web matchups

Status: backlog, planning only, 2026-11-07.
Ticket: [UI-070](issues/UI/UI-070.md), Medium priority.

Let web players independently choose teams from installed eligible years and
clearly see that the designated home team's season governs the game's rules.
Keep each team's original year/chart/roster identity. Make cross-year selection
clear and verify it end to end, including same-school/different-year matchups,
swapped home/away roles, supported rule transitions and saved games.

## Paydirt consultation

Reviewed local Paydirt paydirt/game_engine.py, PaydirtGameEngine.__init__:
it explicitly selects season rules from the home chart's season directory, with
home-year fallback for supported construction paths. Adapt the home-year policy;
do not copy its NFL rules, fallback implementation, private charts or runtime.
Also reviewed paydirt-web/backend/routes.py new_game: that inspected web route
loads both teams through a common season_dir, so it is not evidence of a complete
cross-year web selection flow to copy.

Reviewed Bowl Bound frontend/src/App.jsx setup selectors, backend/app.py NewGame
and new_game, docs/web-demo.md and docs/rules-profile.md's historical-season
selection section. Both UI selectors already enumerate the full catalog, API
team loads are independent, and the documented rule is already
rules_season = home_team.season. Build on these foundations. UI-009 separately
tracks season-qualified in-game labels; this ticket concerns explicit selection,
rules visibility and complete integration verification.

## Acceptance and validation

Follow UI-070's criteria with test-first synthetic behavior regressions and
existing same-year controls. Verify actual engine rule differences across a
supported boundary, not just request fields or rendered text. Keep the engine
and its approved Bowl Bound profile authoritative, including the unsupported-year
boundary. Preserve save identities and validate a real-engine browser session.

This is future feature scope, outside Milestone 42 / 1.0.0. Adding this plan does
not extend supported seasons, publish new charts or implement a new rules profile.

Tracking validation: ran `.venv/bin/python scripts/build_issue_index.py` and
`.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_create_issue.py tests/test_priority_docs.py tests/test_release_player_docs.py -q`;
38 tests passed. `git diff --check` passed. These validate backlog documentation,
not the unimplemented acceptance criteria.

## Existing engine support verified

Owner asked whether an engine update is also needed. Read-only verification on
2026-11-07 confirms current engine and CLI already allow independent-year team
IDs and choose the designated home year's supported rules. A synthetic 60-case
probe exercised swapped-year/same-school cases, actual kickoff/touchback and
historical-tie/overtime transitions, CLI launch, API creation and save/load.
Existing special-teams/session/overtime/CLI/save regressions passed 212 tests.
See UI-070's evidence comment. The seven inspected runtime/API modules are
identical in the active Milestone 42 integration tree.

No engine update is needed for this matchup feature within the existing
1940–2023 home-season rules boundary. Supporting 2024+ home seasons is a separate
rules-profile extension. UI-070 remains an open UI/integration-verification task;
no new frontend behavior or browser acceptance is claimed here.
