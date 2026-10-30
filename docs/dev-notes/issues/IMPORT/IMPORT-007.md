---
id: IMPORT-007
title: Complete the directory batch import workflow and aggregate reporting
status: open
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- batch
- feature
links:
- IMPORT-002
- IMPORT-003
- IMPORT-004
- IMPORT-005
- IMPORT-006
- IMPORT-008
- IMPORT-009
commits: []
---

## Description

Finish the parked wip/5d-batch-import implementation as the canonical directory export workflow. This ticket owns the positive batch behavior and integration structure; IMPORT-002 through IMPORT-006 own the specific rollback, collision, dry-run, diagnostic and input-contract defects found during review.

## Resolution / verification

- Accept a real directory only for export mode; discover non-hidden .pdf files nonrecursively in deterministic case-insensitive order and keep single-PDF behavior compatible.
- Process independent PDFs after an individual failure, emit one public-safe status per PDF plus a deterministic final summary, and return zero only when every planned PDF succeeds.
- Preserve per-PDF atomicity and existing-output safety while sharing typed planning/result records instead of positional tuples or recomputed keys.
- Add synthetic success, mixed-failure, empty-directory, ordering, hidden-file and aggregate-exit tests; fix and link IMPORT-002 through IMPORT-006 before resolution.
- Reconsult Paydirt batch/import behavior and record what was adapted or rejected without copying Excel/NFL assumptions or adding a runtime dependency.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
