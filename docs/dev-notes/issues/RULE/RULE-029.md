---
id: RULE-029
title: Define and implement elected safety procedure
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- advanced-option
links: [RULE-022]
commits: [a51f849, 427b42e]
---

## Description

The owner approved Advanced Rule I-5 elected safeties. During a live scrimmage, the possessing team may elect to award the opponents two points, after which the conceding team receives a safety free kick from its own 20. The choice is separate from an ordinary safety and its resulting free kick.

## Resolution / verification

- Implement the choice as an engine-owned scrimmage action. Verify two-point scoring, the conceding team's free kick from its own 20, zero dice and elapsed time, no rushing/passing credit, availability on any down before the play, rejection during a pending/free-ball decision, API/CLI/browser controls, and save replay with synthetic teams.

Verified in `a51f849`: 146 focused Python tests passed; all 15 compact-game
frontend tests passed on Node 24.22.2; repository Ruff check/format and
`git diff --check` passed. Tests cover scoring, safety free-kick spot, no clock
or statistical charge, fourth-down pre-snap availability, pending interception
rejection, API, browser controls, and save replay. Automated validation is done;
owner play-test remains before closure.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Owner approved this implementation as part of the three-option scope in RULE-022.
Runtime behavior remains unavailable until the test-first implementation lands.

--- 2026-11-01 ---
Added `elect_safety` to the overtime game-action coverage set so the full legal
menu remains asserted after this rule was added; tested in `427b42e`.
