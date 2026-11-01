---
id: RULE-029
title: Define and implement elected safety procedure
status: open
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- advanced-option
links: [RULE-022]
commits: []
---

## Description

The owner approved Advanced Rule I-5 elected safeties for implementation on 2026-11-01. This is separate from ordinary safeties and the existing free-kick procedure; keep the election unavailable until this ticket is implemented and verified.

## Resolution / verification

- Record when a team may elect a safety and the resulting score, possession, kickoff, timing, statistics, and trace behavior; implement with synthetic tests for every legal phase and save replay.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Owner approved this implementation as part of the three-option scope in RULE-022.
Runtime behavior remains unavailable until the test-first implementation lands.
