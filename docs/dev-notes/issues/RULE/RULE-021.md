---
id: RULE-021
title: Add the Bowl Bound QB Sneak procedure
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- advanced-option
links: [RULE-022]
commits: [d0fa13b]
---

## Description

QB Sneak follows Advanced Rule I-2 and is available as a callable play. Its result follows Bowl Bound rules and normalized chart semantics; a similarly named play in another game is not authoritative.

## Resolution / verification

- Implemented in `d0fa13b` after test-first failures for Q parsing and defensive-key validation.
- The engine uses only the Play 1 roll. Green awards one yard; white/yellow awards no gain; red fumbles at the line. WCSNEAK ends without dice; other Wild Card calls produce a blank defensive result. Existing conditional-guess doubling and fumble recovery/state handling apply.
- Synthetic focused coverage includes normal, red-zone/goal-line, fumble, Wild Card, trace, statistics/state, API/CLI, coaching, normalization, CSV, and save compatibility behavior.
- Validation: 416 targeted Python tests passed; 120 frontend tests passed on Node 24.22.2; frontend production build passed; Ruff lint/format checks passed.
- Status is resolved pending owner play-test confirmation; do not close from automated tests alone.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
