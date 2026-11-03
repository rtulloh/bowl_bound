---
id: DATA-005
title: Season audit rejects lawful overtime series state resets
status: resolved
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: '2026-11-02'
closed-at: null
tags:
- tested
links: []
commits:
- 3e699aa
- 1a0e76d
---

## Description

The generator pilot exposed a local-season audit assumption: adjacent states must match except kickoff. Production college overtime intentionally resets state for each new series. All affected pilot games finished, but legitimate overtime starts failed the disconnected-state check. Record engine-observed series-start evidence and validate its order and exact state without allowing arbitrary discontinuities.

## Resolution / verification

- Synthetic declared overtime reset passes only with matching engine-observed state and series order
- Undeclared, stale and malformed resets still fail
- Replay the retained private failing seeds without chart-strength changes

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.


--- 2026-11-02 20:29 ---
Readiness also requires zero reconciliation failures in the selected training
candidate, held-out batch and separate coaching checks. Added a synthetic
end-to-end declared training failure to prevent a clean held-out average from
concealing earlier failed engine/audit evidence.

--- 2026-11-02 20:51 ---
Synthetic lawful/undeclared/stale/malformed overtime boundary checks pass; all four retained original failing seeds pass unchanged-chart replay. Readiness also requires zero selected-training/held-out/coaching failures (61dec6c).
Focused cumulative gate at 9565398: 121 passed. Owner play-test confirmation remains unrecorded, so this ticket is not closed.

--- 2026-11-02 21:04 ---
Parallel M33 adversarial review found missing controls for forged reverse boundary order and an untied regulation score. Reopened pending narrow strict guards and synthetic red/green tests. Actual recorded pilot boundaries will be rechecked; engine outcomes and chart values are unchanged.

--- 2026-11-02 21:14 ---
Narrow reviewed strict guards from M33 0a89a68 adapted in tested 1a0e76d: 40 local-season cases and 126 focused cumulative cases pass. All 904 retained final-pilot engine reports, including 17 overtime games, pass current production validate_game through a documented private serialized-fact adapter. Simulation function, generation code and runtime engine are unchanged since calibration; original evidence remains intact. Owner play-test confirmation is absent, so this ticket is resolved, not closed.
