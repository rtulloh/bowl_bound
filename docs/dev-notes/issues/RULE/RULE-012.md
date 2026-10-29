---
id: RULE-012
title: Return-foul midpoint rounds away from the 50 for odd end-zone origins
status: open
priority: Medium
milestone: '22'
created-at: 2026-10-27
resolved-at: null
closed-at: null
tags: []
links: []
commits: []
---

## Description

penalty_yardage.enforce_return_penalty and special_teams._accepted_return both use (start + 1) // 2 for the midpoint. For origins 101-109 the midpoint lies on the returner's own half, so closer-to-the-50 is start // 2; origin 105 yields 53 instead of 52. Rare but wrong by one yard in both modules.

## Resolution / verification

- Shared midpoint helper with rulebook citation; tests for origins 101, 103, 105, 107 and 109 in both turnover and kick returns.

## Comments

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
