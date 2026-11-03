---
id: DATA-003
title: Derived ESPN PAT flags can contradict explicit original event labels
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

In the audited older ESPN-derived snapshot, extra-point success flags are unpopulated defaults even for original events explicitly labeled Extra Point Good. Trusting only the derived booleans produces an all-missed PAT chart. Prefer unambiguous original event labels, preserve unknowns and test source precedence synthetically.

## Resolution / verification

- A synthetic Extra Point Good event with false default flags remains successful
- Explicit missed attempts remain misses and unknown outcomes remain unknown

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
