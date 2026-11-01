---
id: RULE-014
title: Return penalty acceptance refused with a false end-zone reason and inconsistent
  with kick returns
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-10-27
resolved-at: 2026-11-01
closed-at: null
tags: []
links: [RULE-003]
commits: [84a553a]
---

## Description

session disables return:accept whenever enforce_return_penalty raises and always reports end-zone enforcement is not yet supported, including an in-field interception return reaching a touchdown with a foul by the non-returning team. special_teams._accepted_return enforces the same foul from the real end-zone coordinate with touchback or safety fallback, so turnovers and special teams implement VI-4(C)(vi) differently.

## Resolution / verification

- Turnover and special-teams returns now use `enforce_return_penalty`, which returns a field-position, touchback, or safety disposition. Kickoffs retain their season-specific touchback spot; unsupported endpoints report the specific validation reason.
- Synthetic tests cover both foul sides, field/end-zone/end-line/touchdown endpoints, canceled recovery rolls, credited return yards, and end-zone safety scoring.
- Verification at `84a553a`: `.venv/bin/python -m pytest tests/test_penalty_yardage.py tests/test_penalties.py tests/test_session_penalties.py tests/test_return_audit.py tests/test_return_fumble_series.py tests/test_turnovers.py tests/test_session_turnovers.py tests/test_engine_hardening.py tests/test_special_teams.py tests/test_session_special_teams.py tests/test_statistics.py tests/test_regulation.py tests/test_overtime_extra.py -q` (333 passed); Ruff check and format checks passed.

## Comments

--- 2026-11-01 ---
Resolved by tested commit `84a553a`. Awaiting play-test confirmation before closure.

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
