---
id: RULE-028
title: Add the Bowl Bound Razzle-Dazzle play
status: open
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- advanced-option
links: [RULE-022]
commits: []
---

## Description

The owner approved Razzle-Dazzle under Advanced Rule I-1 for implementation on 2026-11-01. It is not a current callable play; keep it unavailable until this ticket is implemented and verified. The engine must not infer it from an ordinary chart result.

## Resolution / verification

- Document eligibility, call sequence, chart/dice use, priority, possession, statistics, timing, and trace behavior from the Bowl Bound rulebook; add synthetic test-first coverage for successful and failed branches and save replay.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Owner approved this implementation as part of the three-option scope in RULE-022.
Runtime behavior remains unavailable until the test-first implementation lands.
