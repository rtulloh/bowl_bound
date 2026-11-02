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
commits: [d0fa13b, '4981494']
---

## Description

QB Sneak follows Advanced Rule I-2 and is available as a callable play. Its result follows Bowl Bound rules and normalized chart semantics; a similarly named play in another game is not authoritative.

## Resolution / verification

- Implemented in `d0fa13b` after test-first failures for Q parsing and defensive-key validation.
- The engine uses only the Play 1 roll. Green awards one yard; white/yellow awards no gain; red fumbles at the line. WCSNEAK ends without dice; other Wild Card calls produce a blank defensive result. Rule IX excludes QB Sneak from conditional-guess yardage doubling; ordinary fumble recovery and state handling still apply.
- Synthetic focused coverage includes normal, red-zone/goal-line, fumble, Wild Card, trace, statistics/state, API/CLI, coaching, normalization, CSV, and save compatibility behavior.
- Validation: 416 targeted Python tests passed; 120 frontend tests passed on Node 24.22.2; frontend production build passed; Ruff lint/format checks passed.
- Updated a stale browser wording assertion to preserve the valid Bowl Bound `QB Sneak` label while still rejecting Paydirt-only labels. The test now verifies the offered Q control; all 33 real-engine browser tests passed in the follow-up validation.
- Status is resolved pending owner play-test confirmation; do not close from automated tests alone.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
The full browser gate exposed a stale assertion that rejected the word “Sneak”
even though RULE-021 makes QB Sneak a supported Bowl Bound play. Updated the
assertion in `4981494` to check the engine label and exclude only foreign labels;
the full browser suite passed.
