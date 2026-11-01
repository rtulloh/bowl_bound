---
id: RULE-031
title: Add the Bowl Bound intentional-delay procedure
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

The owner approved intentional delay under Advanced Rule I-6(B) for implementation on 2026-11-01. It must be distinguished from existing timing, hurry-up, timeout, and kneeldown behavior; keep it unavailable until this ticket is implemented and verified.

## Resolution / verification

- Document the rulebook eligibility, penalty/clock effects, offered decisions, and interactions; add synthetic tests for legal and illegal situations, timing, possession, traces, and save replay.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Owner approved this implementation as part of the three-option scope in RULE-022.
Runtime behavior remains unavailable until the test-first implementation lands.
