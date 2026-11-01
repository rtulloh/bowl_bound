---
id: RULE-024
title: Define gameplay effects for Bowl Bound power ratings
status: open
priority: Low
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- scope-review
links: []
commits: []
---

## Description

Advanced Rule VIII power ratings are distinct from importer metadata and local placeholder ratings. Decide whether ratings affect eligibility or outcomes and define the rule before any rating influences gameplay.

## Resolution / verification

- Record the rulebook-backed rating inputs, formula, uncertainty handling, and chart-season scope; if approved, add synthetic tests and ensure missing/local-only metadata cannot silently affect a game. Otherwise leave ratings informational only.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
