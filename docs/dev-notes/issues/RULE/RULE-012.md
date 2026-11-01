---
id: RULE-012
title: Return-foul midpoint rounds away from the 50 for odd end-zone origins
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-10-27
resolved-at: 2026-11-01
closed-at: null
tags: []
links: []
commits: [d12daca]
---

## Description

penalty_yardage.enforce_return_penalty and special_teams._accepted_return both use (start + 1) // 2 for the midpoint. For origins 101-109 the midpoint lies on the returner's own half, so closer-to-the-50 is start // 2; origin 105 yields 53 instead of 52. Rare but wrong by one yard in both modules.

## Resolution / verification

- Added a shared midpoint helper cited to Basic VI-4(C)(vii); both turnover and kick-return enforcement now round the half-yard marker toward the 50 for origins 101, 103, 105, 107 and 109.
- Verification at `d12daca`: `.venv/bin/python -m pytest tests/test_penalty_yardage.py tests/test_special_teams.py tests/test_return_audit.py tests/test_engine_hardening.py -q` (163 passed); Ruff check and format checks passed.

## Comments

--- 2026-11-01 ---
Resolved by tested commit `d12daca`. Awaiting play-test confirmation before closure.

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
