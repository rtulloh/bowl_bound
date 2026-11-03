---
id: DATA-013
title: Large cohort generation repeats source work and lacks resumable batches
status: open
priority: Medium
milestone: 34a
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags:
- testing
links: []
commits: []
---

## Description

Generating many teams repeats full-source provenance scans and hashes and the initial two-team runner has no safe cohort checkpoint contract. Expanded work must cache evidence and opponent fits once and resume immutable artifacts safely.

## Resolution / verification

- Use synthetic tests for cached deterministic bundles, bounded execution and tamper-safe checkpoint resume.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
