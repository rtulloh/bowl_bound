---
id: RULE-010
title: Support per-play mutually exclusive IB and OOB declarations
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-10-26
resolved-at: 2026-11-01
closed-at: null
tags: []
links: []
commits: [a9316e0, bde4f40, 9c6a5e4]
---

## Description

Owner requested per-play in-bounds (IB) and out-of-bounds (OOB) declarations beside Hurry-up, Timeout and Spike. The local Bowl Bound rulebook defines optional Advanced Rule I-4(C) OOB and I-6(C) IB declarations before the offensive dice roll. OOB guarantees a 10-second play; IB only increases the likelihood that the clock keeps running.

## Resolution / verification

- Implemented Advanced I-4(C) OOB and I-6(C) IB in the engine. OOB guarantees a 10-second play; both declarations apply the five-yard cost only when they change the result, with the rulebook exceptions. Declarations are mutually exclusive, apply to the next scrimmage play and clear after it; kicks do not carry a declaration forward.
- Added synthetic coverage for rejected submissions, possession changes, pending penalties/interceptions, scoring and incomplete exceptions, timing, statistics, traces, offense-only coached controls, punt reset, and exact save continuation. Legacy save digest compatibility remains covered.
- Browser controls submit offered engine action IDs and display the selected state. Terminal shortcuts O/I and full `action bounds:oob` / `action bounds:ib` commands are offered only when legal. Private chart boundaries are unchanged.
- Verification at `a9316e0`: `.venv/bin/python -m pytest tests/test_bounds_declarations.py tests/test_api_regulation.py tests/test_regulation.py tests/test_save_game.py tests/test_session.py tests/test_session_penalties.py tests/test_session_scoring.py tests/test_cli_shortcuts.py -q` (203 passed); frontend compact-game tests under Node 24 (12 passed); Ruff check/format and `git diff --check` passed.
- Follow-up `9c6a5e4` updates the overtime action assertion to include the legal IB/OOB declarations. Verified with `.venv/bin/python -m pytest tests/test_overtime.py::test_toss_series_spot_untimed_rounds_alternating_first_and_timeouts -q` (1 passed) and Ruff check/format.

## Comments

--- 2026-10-26 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 22:50 ---
Checked `docs/reference/bbrules2007.pdf` (printed pp. 14–15). The book describes
the OOB and IB declarations by name, not as `7+` / `7-` chart notation. Treat those
as a possible CLI shorthand only; confirm the command syntax before implementation.

--- 2026-11-01 ---
Resolved by tested commit `a9316e0`. The terminal uses O/I shortcuts and explicit
action commands; it does not interpret `7+` / `7-` as declarations. Awaiting
play-test confirmation before closure.

--- 2026-11-01 ---
Updated an overtime test whose expected action list predated the legal IB/OOB
controls. The regression now verifies both declarations remain offered in an
untimed overtime series.

The coaching guide's stale “disabled” wording was corrected in `bde4f40`.
