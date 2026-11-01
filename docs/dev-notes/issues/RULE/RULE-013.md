---
id: RULE-013
title: End-zone return fumble is a safety while an identical non-advance is a touchback
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-10-27
resolved-at: 2026-11-01
closed-at: null
tags: []
links: []
commits: [075af29]
---

## Description

An elected end-zone return that never crosses the goal line is a touchback (VI-13 F(i)), but a fumble inside the end zone recovered by the returner resolves to a safety, and a negative return cell carrying the ball beyond the own end line resolves to a touchback while fumbles and interceptions beyond that line are safeties. docs/turnovers.md endorses both outcomes in adjacent lines without a citation for the fumble case.

## Resolution / verification

- Recorded the distinction in `docs/rules-profile.md`: a return that stays between its own goal line and end line is a touchback, a return reaching its own end line is a safety, and an own-end-zone fumble recovered by the fumbling team is a safety under Basic VI-13(D)(iv).
- `_apply_return_yards` now awards a safety when an elected return reaches or crosses the returner's own end line. The negative-return regressions cover the touchback/safety boundary; existing synthetic tests cover end-zone fumble recovery outcomes.
- Verification at `075af29`: `.venv/bin/python -m pytest tests/test_engine_hardening.py tests/test_turnovers.py tests/test_session_turnovers.py tests/test_return_fumble_series.py tests/test_return_audit.py -q` (112 passed); Ruff check and format checks passed.

## Comments

--- 2026-11-01 ---
Resolved by tested commit `075af29`. Awaiting play-test confirmation before closure.

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
