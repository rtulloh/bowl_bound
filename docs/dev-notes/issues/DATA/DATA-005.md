---
id: DATA-005
title: Season audit rejects lawful overtime series state resets
status: open
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- reproduced
links: []
commits: []
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
