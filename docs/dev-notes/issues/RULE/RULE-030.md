---
id: RULE-030
title: Define weather effects for Bowl Bound games
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

Weather effects under Advanced Rule VI are deferred and have no approved runtime model. Do not add ambient randomness or alter chart outcomes without explicit rule support.

## Resolution / verification

- Inventory rulebook weather conditions, eligibility, affected procedures, and season applicability; record adopt/defer decisions. For each adopted condition, create a separate implementation ticket with deterministic synthetic tests and unchanged behavior when weather is absent.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
