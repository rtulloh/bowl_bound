---
id: RULE-031
title: Add the Bowl Bound intentional-delay procedure
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- advanced-option
links: [RULE-022]
commits: [bf0d7f9]
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

--- 2026-11-01 ---
Implemented in `bf0d7f9`. Synthetic tests first demonstrated that the clock choice
was unavailable. The engine now offers the five-yard penalty only after an
eligible 30-second play when no timeout was taken, charges 40 seconds total, and
omits the penalty if that timing expires the period. Save replay, older pending
clock-choice digest compatibility, CLI shortcut, and no-dice behavior are covered.
Validation: 188 focused Python tests, 20 clock UI tests, Ruff, format, and
`git diff --check` passed. Awaiting owner play-test confirmation before closure.
