# Milestone 27 — Automatic play timing and timeout suffixes

## Scope

The canonical scope is [Milestone 27 in the project plan](project-plan.md#27-apply-play-timing-automatically-and-support-combined-timeout-input).
The owner reproduced a rejected `7T` command during local play-testing and supplied
that syntax for requesting a timeout after the play. The matching defense form is `AT`.
The owner then requested automatic normal timing at quarter, half, and game boundaries,
with no separate normal-runoff action; kneeldown remains the clock-draining play.

## Paydirt consultation — 2026-10-30

Reviewed the local Paydirt checkout before planning and implementation:

- `paydirt/interactive_game.py:510-537, 643-650, 840-850` parses `T` as a play modifier
  and documents inputs such as `7T`. `tests/test_interactive_game.py:531-565` covers
  suffix parsing. Adapt the compact suffix syntax and test-first coverage.
- `paydirt/game_engine.py:5910-5999` applies play timing and advances periods in the
  engine; `paydirt/auto_game.py:272-286` observes those transitions after a play, and
  `tests/test_auto_game.py:115-133` covers advancement after an untimed down. Adapt
  automatic period handling, but do not reuse Paydirt's NFL timing or overtime rules.
- `paydirt/game_engine.py:3017-3056` applies a timeout by reducing the same play's
  elapsed time. Do not reuse that rule: Bowl Bound's timeout duration and period
  transitions remain governed by its own rules profile.
- No Paydirt code, NFL behavior, game data, or runtime dependency is reused.

## Work log

### 2026-10-30 — regression-first implementation

- Added synthetic offense (`7T`) and defense (`AT`) regressions. Against the unchanged
  implementation, all three new cases failed because the CLI rejected the suffix.
- The implementation submits the legal call, advances the concealed computer response,
  and executes only the human timeout exposed by the engine. If no timeout is offered,
  the play remains applied and the CLI reports that no timeout was used.
- Requested help and the player guide explain the suffix; routine play displays stay
  uncluttered. Invalid suffixes preserve the complete saved-game state.
- The owner expanded the scope to remove the separate runoff/Continue action. Normal
  timing now commits when the next action is selected; Q1/Q3 advance and run that
  action in the next quarter, while halftime/final boundaries do not consume a new
  play or dice. Kneeldown remains the clock-draining play.

### 2026-10-30 — milestone verification

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: 2,604 passed;
  93.32% branch coverage (75% threshold met).
- `.venv/bin/python -m ruff check .`, `.venv/bin/python -m ruff format --check .`,
  and `.venv/bin/python -m pip check`: passed.
- `npm test`: 120 passed; `npm run build`: passed; `npm audit`: zero vulnerabilities.
- `npm run test:e2e`: 33 passed using the real engine and synthetic sample teams.
  Playwright emitted one environment color-variable warning; no tests were skipped.
- Focused engine/CLI/API checks passed (177); the milestone issue index test passed.

Milestone commit: `52c7d08` (`milestone 27: apply play timing automatically`).
CLI-038 and RULE-017 are resolved against this tested commit. Owner play-test
confirmation is still required before closing either ticket.
