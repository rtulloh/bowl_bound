---
id: FLOW-002
title: Kickoff status text contradicts a pending receiver decision
status: open
priority: Low
milestone: '22'
created-at: 2026-10-27
resolved-at: null
closed-at: null
tags: []
links: []
commits: []
---

## Description

RegulationGame overrides status with 'Kickoff required before scrimmage play.' whenever the phase is KICKOFF, including while kick:touchback / kick:return is pending for the receiver. Both the browser and CLI display that status directly above the receiver's choice.

## Resolution / verification

- Status reflects the pending decision when one exists; synthetic test for both receiving sides; adapters unchanged.

## Comments

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
