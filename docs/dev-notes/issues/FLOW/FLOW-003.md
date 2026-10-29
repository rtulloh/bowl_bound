---
id: FLOW-003
title: Generate engine-owned roster narration for scrimmage plays
status: resolved
priority: Medium
milestone: 21a
created-at: 2026-10-28
resolved-at: 2026-10-28
closed-at: null
tags:
- tested
- awaiting-playtest
links: [CLI-036, DEV-030, DEV-031, FLOW-004, FLOW-005]
commits: ["1505562","4457887"]
---

## Execution order

Depends on: DEV-030.
See [Milestone 21a plan](../../milestone-21a.md) for the full dependency order.

## Description

Implement named run/pass narration from structured committed engine facts under the reviewed M21a contract. Keep generic narration when roster entries or actor evidence are absent. Names are illustrative, not a new simulation layer.

## Resolution / verification

- Write synthetic red-first tests for runs, completed/incomplete passes, touchdowns and loss/no-gain outcomes on both possessions.
- Cover Option and other supported called-to-resolved play changes; actor roles follow resolved classification and never manufacture a catch, sack, tackle or receiver identity unsupported by the report.
- Use the existing deterministic player_name selector with the reviewed explicit index; no new RNG or mutable display counter.
- Keep penalties, rejected/unsupported plays and pending reports truthful; retain generic fallback and all existing structured result/trace facts.

## Comments

--- 2026-10-28 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-28 red-first and implementation ---
Paydirt consultation repeated from DEV-030: commentary.py:315–351 separates roles
from outcomes; do not reuse random participants or NFL mappings. New synthetic
tests reviewed before first run; review tightened completion labels, reroll
segments, real hurried bad-snap fallback, actor team and whole-roster immutability.
Red run: 24 expected ModuleNotFoundError failures. Added pure structured-credit
formatter; description/dataclass/digest unchanged. Implementation review pending
before tests, as requested. No historical fixtures or runtime adapter changes.

Implementation review approved before green runs (no edits/tests by reviewer).
Focused commentary/roster/statistics/terminal-presentation/profile gate: 160 passed
in 4.44s. Formatter-only coverage: 24 passed, 96.00% branch-aware coverage
(95% focused floor). Ruff lint/format passed. No existing expectations changed.
Final pre-commit review requested; runtime integration remains separate.
