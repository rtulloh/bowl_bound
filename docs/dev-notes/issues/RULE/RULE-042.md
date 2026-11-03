---
id: RULE-042
title: Offer a timeout as a pre-play modifier after kickoff
status: open
priority: Medium
milestone: '33'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- rules-profile
- timing
- usability
links: []
commits: []
---

## Description

After a kickoff, the receiving-side human defender is offered formations but no timeout. The approved interaction is the Paydirt-style pre-play modifier: the player selects their timeout, then selects the defensive formation; Bowl Bound resolves that play and charges the selected timeout as the play's timing modifier. Current timing logic exposes timeouts only after a completed play, making the first scrimmage snap an unintended exception.

## Resolution / verification

- The engine offers each eligible side's own timeout as an explicit armed pre-play modifier, including immediately after kickoff; the frontend never invents availability.
- Selecting a timeout does not advance the clock or resolve a play. The next legal play charges that side's timeout, uses the 10-second timing rule, records the result clearly, and clears the armed modifier.
- Preserve ordinary post-play clock decisions and prevent stale armed modifiers across a turnover, scoring play, save/load, invalid action, or new game.
- Add synthetic engine, API, CLI, coached-browser, and save/load regressions; verify the production frontend build.

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 13:45 ---
Owner approved the pre-play-modifier behavior. Consulted local Paydirt
`paydirt-web/backend/routes.py` (`call_defensive_timeout`, request
`call_defensive_timeout`, and the post-play timeout flag): it records a player
timeout choice before resolving the play, then applies the short timing after
that play. Bowl Bound will adapt the interaction only, retaining its own
engine-owned legal actions and timing rules; it will not reuse Paydirt code or
introduce a runtime dependency.

--- 2026-11-02 00:00 ---
Reassigned from Milestone 23 to the owner-prioritized Milestone 33 playability
follow-up scope. The first scrimmage play after a kickoff must not omit an
otherwise legal defensive timeout.


--- 2026-11-02 20:40 ---
Verified Paydirt routes.py request validation/forwarding at lines 427–430,
1078–1089 and 1186–1191, and tests/test_timeout_clock_interactions.py before
implementation. Adapted the interaction and boundary-test approach only; no NFL
two-minute warning, minute-based clock, random 35-second timing or runtime code
is reused. Parent confirmed the single side-owned modifier, own cancellation,
no-overwrite and preserved post-play choices.

Test-first: 17 expected failures exposed absent post-kickoff actions. Later red
regressions exposed the safe-kneel calculation ignoring an armed offensive
10-second play, and a stale arm after a prior intentional delay ended Q1. Both
were corrected. An initial synthetic sentinel used an invalid black die face;
fixed to legal (3,4,5) before checking exactly-once consumption. A punt fixture
now completes its real fair-catch decision; spending before that would be wrong.
Hard’s actual RZDZ continuation is replayed and checked while the arm remains.

Review preserved the existing no-time elected-safety rule: its unused arm clears
without consuming a timeout or clock. A dedicated red test showed the new timeout
path initially overrode that rule; fixed the implementation rather than changing
Bowl Bound timing. The earlier generic elected-safety 10-second expectation was
replaced with this explicit approved-rule regression. No existing assertions
were weakened. `clock:spike` creates the next play under combined timing; cancel
the armed timeout before choosing that separate next-play timing treatment.
A red regression verifies it is unavailable while armed and restored on cancel.
Existing prior-play timeout/hurry/delay choices remain available. Validation and
committed reference pending; browser coverage is required before resolution.


RULE-042 focused validation (2026-11-02):
- `.venv/bin/python -m pytest tests/test_armed_timeouts.py tests/test_coaching_invariants.py tests/test_regulation.py tests/test_api_regulation.py tests/test_cli_timeout_controls.py tests/test_cli_shortcuts.py tests/test_kneel_safety.py tests/test_save_game.py tests/test_coaching_saves.py tests/test_fumble_penalty_order.py tests/test_fourth_down_guidance.py tests/test_issue_tracker.py -q`: **425 passed in 44.04s**, including **37 new armed-timeout cases**, no skips/warnings.
- Pinned Node/npm in `frontend/`: `npm test` **130 passed (16 files)** and `npm run build` passed. Focused clock/no-rules tests: **22 passed**.
- Ruff check and format check passed (**535 files**), and `git diff --check` passed.
- Added real-engine browser cases for each human side after kickoff: offered own-side arm, unchanged clock/budget, raw-text save/load, legal offensive/defensive call, one 10-second charge and reset. Browser acceptance remains pending the fresh hosted branch run; the local process-launch restriction is not counted as a pass.
