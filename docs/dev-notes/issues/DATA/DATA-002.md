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
