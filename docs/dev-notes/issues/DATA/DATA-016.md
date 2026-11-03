---
id: DATA-016
title: Defensive completion responses depend on own offensive strength
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

Generator defensive forced-completion response yardage uses the same team's scaled offensive completion pool. Refining offense can therefore alter defensive cells, confounding separate offense and defense effects. Use an explicit source-neutral league completion prior plus the team's independently fitted defensive effect; record its provenance and limits.

## Resolution / verification

- Synthetic test shows an offensive-only calibration changes offense while preserving defense; defensive completion response yardage has explicit independently modeled source context and existing chart loading/probability gates remain valid.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
