---
id: DATA-015
title: Sparse cohort assessments need JSON-safe missing metric states
status: open
priority: Medium
milestone: 34a
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags: []
links: []
commits: []
---

## Description

The first real-engine synthetic cohort run exposed an infinite absolute-error value when a target metric had no simulated observations. Immutable JSON reports reject nonfinite values. Preserve the missing denominator and failed sparse gate without inventing a zero or weakening exposure checks.

## Resolution / verification

- Synthetic complete-game tests serialize sparse per-team OFF/DEF assessments as explicit unavailable values, retain failed sample gates, and resume byte-consistent engine evidence.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
