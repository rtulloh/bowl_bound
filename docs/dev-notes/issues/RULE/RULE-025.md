---
id: RULE-025
title: Add onside kick choice and resolution
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

Onside kicks are currently unsupported; the engine automatically schedules a normal kickoff. The owner clarified that second-half kicking-team assignment is fixed, with only the kick type potentially selectable. Implementing this must not reintroduce a kick-or-receive choice.

## Resolution / verification

- Verify Bowl Bound kickoff eligibility, dice, recovery, field position, timing, possession, trace, stats, AI choice, and save replay from the rulebook; synthetic tests cover success and failure. Keep the assigned kicking team fixed in both halves.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
