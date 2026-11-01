---
id: FLOW-002
title: Kickoff status text contradicts a pending receiver decision
status: resolved
priority: Low
milestone: '22'
created-at: 2026-10-27
resolved-at: 2026-11-01
closed-at: null
tags: []
links: []
commits: [72b53e9]
---

## Description

RegulationGame overrides status with 'Kickoff required before scrimmage play.' whenever the phase is KICKOFF, including while kick:touchback / kick:return is pending for the receiver. Both the browser and CLI display that status directly above the receiver's choice.

## Resolution / verification

- During a pending receiver decision, status names the receiving team and says it is choosing how to receive the kickoff. Before the kick is taken, the existing kickoff-required status remains. CLI and browser adapters stay unchanged.
- Verified at `72b53e9`: 34 regulation and API-regulation tests passed; Ruff check/format passed.

## Comments

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Both synthetic receiving-side cases failed against the old status, then passed
after the regulation view used its pending decision chooser.
