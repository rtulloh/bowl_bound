---
id: DATA-018
title: Empty historical slate must not produce a successful simulation batch
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

Read-only self-review found that a fully excluded historical slate can complete a zero-game batch with zero failures. A new synthetic regression reproduces the missing rejection. Coverage reports may legitimately contain zero eligible fixtures, but simulation/refinement must reject them before creating outputs and never label an empty cohort mechanically ready.

## Resolution / verification

- Synthetic all-excluded slate raises an actionable no-selected-fixtures error before any engine execution or simulation output, while phase-one exclusion reports remain valid.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
