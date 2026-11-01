---
id: RULE-015
title: Trace labels mislabel the end-zone depth roll and the F_ENDZONE decline text
status: resolved
priority: Low
milestone: '22'
created-at: 2026-10-27
resolved-at: 2026-11-01
closed-at: null
tags: []
links: []
commits: [0212469]
---

## Description

_turnover_trace_entry renders the end_zone_depth white-face roll with cell text 'recovery', and _penalty_result_text describes an F_ENDZONE prepared result as a fumble with location still to be resolved although the location is fixed one yard into the end zone.

## Resolution / verification

- End-zone depth rolls now label their trace cell `depth`; a prepared `F_ENDZONE` result describes the fixed one-yard location and still indicates that recovery is pending.
- Verification at `0212469`: `.venv/bin/python -m pytest tests/test_session_turnovers.py tests/test_session_penalties.py tests/test_resolution.py tests/test_priority_matrix.py -q` (453 passed); Ruff check and format checks passed.

## Comments

--- 2026-11-01 ---
Resolved by tested commit `0212469`. Awaiting play-test confirmation before closure.

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
