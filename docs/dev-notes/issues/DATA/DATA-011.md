---
id: DATA-011
title: Historical game presence does not establish complete cohort evidence
status: open
priority: High
milestone: 34a
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags:
- reproduced
links: []
commits: []
---

## Description

Expanded college snapshots have uneven game and event coverage. A schedule game with one observed event must not silently qualify an entire team or historical slate.

## Resolution / verification

- Audit schedule identity, expected games, temporal and field coverage, provenance and uncertainty with synthetic fixtures.
- Report every external, missing or disqualified game and never invent an opponent chart.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

Phase-one test-first checkpoint (2026-11-03): exact historical fixture/target
contracts, cached deterministic generation, private CSV/JSON/Markdown report hashes,
invalid opponent/year/neutral rejection, missing-team states and no-overwrite CLI
checks are implemented. New tests first failed for absent interfaces or biased
sparse sampling. Focused cumulative generator/runner/tracker run: 125 passed in
36.76 seconds; Ruff check and format pass. No broad simulation has started.

Source screening correction: repeated stale late-game snap clocks cannot establish
missing plays. A new synthetic regression failed before moving that condition to
an explicit uncertainty warning. Four-period, minimum-volume and known-primary-
yardage checks remain required; official event completeness is never asserted.
Initial strict-screen private audits are preserved unchanged.
