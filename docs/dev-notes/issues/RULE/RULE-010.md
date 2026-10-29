---
id: RULE-010
title: Support per-play mutually exclusive IB and OOB declarations
status: open
priority: Medium
milestone: '22'
created-at: 2026-10-26
resolved-at: null
closed-at: null
tags:
- requested
links: []
commits: []
---

## Description

Owner requested guaranteed in-bounds (IB) and out-of-bounds (OOB) as one-play modifiers beside Hurry-up, Timeout and Spike. Only no-huddle/hurry mode persists. The current engine does not implement these declarations; disabled UI placeholders must not imply gameplay support.

## Resolution / verification

- Implement Advanced I-4(C) OOB and I-6(C) IB in the engine, declaring before any offensive roll, with applicable five-yard costs and documented exceptions; no clock-only browser overrides.
- IB and OOB are mutually exclusive and clear after one play; cover failed submissions, possession changes, pending penalties/turnovers, scoring, timing, statistics, traces, coaching privacy and exact save continuation with synthetic test-first evidence.
- Offer only legal engine IDs and reasons in the shared desktop/mobile row; retain private chart boundaries and review the approved rules profile before enabling either declaration.

## Comments

--- 2026-10-26 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
