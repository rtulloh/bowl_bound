---
id: DATA-002
title: Season PBP event totals require official-stat reconciliation before fitting
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
- c0cbf10
---

## Description

A public season snapshot can contain every scheduled game while event flags and official cumulative statistics still disagree. Raw overlapping flags, no-play records, ownership on kicks and later statistical corrections can alter denominators. Generation must retain diagnostics and block claims of exact historical calibration when mismatches remain.

## Resolution / verification

- Normalize sacks and no-play evidence without double counting
- Report actual observed totals and explicit official aggregate deltas
- Use aggregate adjustments only through named recorded policies

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.


--- 2026-11-02 20:29 ---
Source review added regressions for explicit PAT-label precedence, non-return zero
flags, unknown fumble evidence, return ownership/display-name consistency and
separate scrimmage/return-fumble denominators. The adapter preserves these facts;
official mismatches are reported rather than hidden behind cumulative substitutions.

--- 2026-11-02 20:51 ---
Source precedence, college sack/no-play accounting, ownership, coverage/official deltas and fail-closed calibration yardage have synthetic regression coverage. Actual official aggregate mismatches remain visible; no exact historical fit or correction of the upstream source is claimed.
Focused cumulative gate at 9565398: 121 passed. Owner play-test confirmation remains unrecorded, so this ticket is not closed.
