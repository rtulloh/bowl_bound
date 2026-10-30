---
id: IMPORT-007
title: Complete the directory batch import workflow and aggregate reporting
status: resolved
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: 2026-10-30
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
commits: [824b0c6]
---

## Description

Finish the parked wip/5d-batch-import implementation as the canonical directory export workflow. This ticket owns the positive batch behavior and integration structure; IMPORT-002 through IMPORT-006 own the specific rollback, collision, dry-run, diagnostic and input-contract defects found during review.

## Resolution / verification

- Accept a real directory only for export mode; discover non-hidden .pdf files nonrecursively in deterministic case-insensitive order and keep single-PDF behavior compatible.
- Process independent PDFs after an individual failure, emit one public-safe status per PDF plus a deterministic final summary, and return zero only when every planned PDF succeeds.
- Preserve per-PDF atomicity and existing-output safety while sharing typed planning/result records instead of positional tuples or recomputed keys.
- Add synthetic success, mixed-failure, empty-directory, ordering, hidden-file and aggregate-exit tests; fix and link IMPORT-002 through IMPORT-006 before resolution.
- Reconsult Paydirt batch/import behavior and record what was adapted or rejected without copying Excel/NFL assumptions or adding a runtime dependency.

Implemented and committed on `wip/5d-batch-import` as `824b0c6`.

- Replaced case-sensitive path ordering with casefolded filename ordering and the original spelling as a deterministic tie-breaker. The former expectation was changed to the milestone's case-insensitive contract; it failed against the unchanged implementation and passes now.
- Batch planning and final status use typed per-PDF records for identities, plans, errors, successes, and dry-run summaries. Identity collection still precedes cross-PDF collision rejection; independent writes continue after failures. The aggregate exit status is derived from final per-PDF results.
- Existing synthetic tests cover complete success, mixed failures, empty input, hidden/non-PDF filtering, status order, summaries, dry-run, and aggregate exit codes.
- Reconsulted Paydirt `extract_charts.py:462-475`, `docs/chart-generator.md`, and the AI audit batch helper/test. Adapted independent-item failure isolation and result aggregation. Rejected lowercase-only discovery, raw errors/tracebacks, partial output, and zero exit on partial failure; no Excel layout, NFL behavior, or Paydirt dependency was reused.
- Verification: `tests/test_pdf_*.py tests/test_export_hardening.py` — 203 passed; Ruff check, Ruff format check and `git diff --check` passed.
- IMPORT-002 through IMPORT-006 are resolved with tested commits. Final integration remains tracked by IMPORT-009.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 00:00 ---
Deterministic batch discovery and per-PDF result aggregation are committed in `824b0c6`.
Final integration remains tracked by IMPORT-009; do not close before the integrated milestone
gate passes.
