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

Owner requested per-play in-bounds (IB) and out-of-bounds (OOB) declarations beside Hurry-up, Timeout and Spike. The local Bowl Bound rulebook defines optional Advanced Rule I-4(C) OOB and I-6(C) IB declarations before the offensive dice roll. OOB guarantees a 10-second play; IB only increases the likelihood that the clock keeps running. Neither declaration is implemented in the current engine; disabled UI placeholders must not imply gameplay support.

## Resolution / verification

- Implement Advanced I-4(C) OOB and I-6(C) IB in the engine, declaring before any offensive roll. OOB guarantees a 10-second play; IB increases the likelihood that the clock continues. Apply the documented five-yard cost and exceptions; do not add clock-only browser overrides.
- IB and OOB are mutually exclusive and clear after one play; cover failed submissions, possession changes, pending penalties/turnovers, scoring, timing, statistics, traces, coaching privacy and exact save continuation with synthetic test-first evidence.
- Offer only legal engine IDs and reasons in the shared desktop/mobile row; retain private chart boundaries and review the approved rules profile before enabling either declaration.

## Comments

--- 2026-10-26 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 22:50 ---
Checked `docs/reference/bbrules2007.pdf` (printed pp. 14–15). The book describes
the OOB and IB declarations by name, not as `7+` / `7-` chart notation. Treat those
as a possible CLI shorthand only; confirm the command syntax before implementation.
