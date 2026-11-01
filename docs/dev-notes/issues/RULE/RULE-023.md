---
id: RULE-023
title: Implement Bowl Bound yardage factors
status: open
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- advanced-option
links: []
commits: []
---

## Description

Advanced Rule IX yardage factors are deferred. No gameplay ticket currently defines how these factors affect chart outcomes, which charts carry them, or how missing factors behave.

## Resolution / verification

- Document the exact factor calculation and eligible outcomes from the Bowl Bound rulebook; if approved, test integer arithmetic, boundaries, missing metadata, priority interactions, traces, and save replay with synthetic charts. Otherwise keep factors out of gameplay and document the deferral.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
