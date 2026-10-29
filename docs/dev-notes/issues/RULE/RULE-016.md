---
id: RULE-016
title: Add end-zone, variable-yardage, return-foul and period-boundary regression
  coverage
status: open
priority: Medium
milestone: '23'
created-at: 2026-10-27
resolved-at: null
closed-at: null
tags: []
links: []
commits: []
---

## Description

Gaps found in the 18a suites: session-level symmetry with the away team on offense for every end-zone case; 36-combination white-face depth enumeration including sum zero; return fouls accepted and declined on each recovery type by each side, including an offensive foul enforced past the line to gain and an automatic first down on an own-recovery return; variable yardage at the goal line with clipped statistics and interception DS exceeding yards to goal; the T2/T3 independence test feeds the same roll repeatedly so a multiplied single roll would pass; variable yardage on the last play of a half, hurried and unhurried; statistics and ledger reconciliation after each new path; save/resume through penalty-decline, interception and end-zone chains with a disabled return:accept reason surviving resume; overtime variants; period boundary via kick and action and the exact 0:00 and untimed-down cases; field goal boundary at 92 versus 93 and the miss spot.

## Resolution / verification

- Each case has a synthetic exact-dice test asserting state, points, pending choices, statistics, timing and trace; none weakens an existing assertion.

## Comments

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
