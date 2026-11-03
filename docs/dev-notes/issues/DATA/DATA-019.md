---
id: DATA-019
title: Unidentified core targets must not disappear from cohort fit gates
status: open
priority: High
milestone: 34a
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags: []
links: []
commits: []
---

## Description

Self-review found that unknown source fumble facts can omit the fumble target and let other metrics alone define a passing assessment. Entirely unidentified restricted targets can also reach a completion update that assumes a target exists. Keep missing source metrics explicit, fail statistical readiness without inventing values, and never propose updates against absent targets.

## Resolution / verification

- Synthetic unknown-fumble and absent-target cases produce explicit unidentifiable states, preserve numeric unknowns, block full statistical passing, and retain unchanged unsupported calibration knobs without errors.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

Additional red/green case: unidentified offensive targets previously discarded
otherwise identifiable defensive targets through one shared exception handler.
Estimate each role separately, preserve known defense evidence and retain the
unsupported offensive role with its specific limitation. No metric is invented.
