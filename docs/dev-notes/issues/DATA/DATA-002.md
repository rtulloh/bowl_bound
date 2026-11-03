---
id: DATA-002
title: Season PBP event totals require official-stat reconciliation before fitting
status: open
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- investigating
links: []
commits: []
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
