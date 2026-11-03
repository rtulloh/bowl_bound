---
id: DATA-012
title: Two-team pooled refinement cannot validate restricted historical cohorts
status: open
priority: High
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

The accepted prototype only calibrates two-team pooled outcomes. Follow-up needs a bounded historical matchup graph and exact per-team offensive and defensive target scope without recursive opponent charts or held-out leakage.

## Resolution / verification

- Test deterministic restricted schedules, matched target IDs, per-team and conference assessment and sparse no-fit states.
- Keep simulation-held-out domains separate from source-group exclusion diagnostics.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-03 target integrity ---
New report test demonstrated missing target-value hash: matching fixture IDs alone
does not freeze the actual statistical goals. The manifest now hashes the complete
restricted targets, and the runner rejects changed values before starting a game.
