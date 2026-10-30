# Milestone 25 — Batch PDF import and documentation

## Scope and starting point

The canonical scope is [Milestone 25 in the project plan](project-plan.md#25-add-batch-import-and-documentation-deferred-from-5d).
Resume the parked `wip/5d-batch-import` draft at `2822c3b`; it is a starting point,
not an accepted milestone. The draft adds directory input and per-file statuses,
but review reproduced defects in rollback, collision handling, dry-run validation,
diagnostics and input contracts.

Work is tracked by [IMPORT-001](issues/IMPORT/IMPORT-001.md) through
[IMPORT-009](issues/IMPORT/IMPORT-009.md). Keep each ticket test-first, commit its
implementation separately, and record tested commit references before resolving
the issue. Do not close tickets until the required play-test confirmation exists.

## Paydirt consultation — 2026-10-30

Reviewed local `/Users/rtulloh/work/paydirt` before implementation:

- `extract_charts.py:51-72` reads Excel background fill values to classify BLACK
  cells and RED extra points. Its broad exception fallback returns `False`; do not
  copy that behavior. Adapt only the lesson that background evidence must be read
  before serialization loses it.
- `docs/chart-generator.md:20-39,72-85` documents which source colors and number
  formats matter and warns that conversion to CSV loses them. Its batch converter
  continues after individual errors and a zero exit code does not prove all teams
  succeeded. Adapt per-file reporting and an aggregate result; retain Bowl Bound's
  stronger per-PDF transaction, rollback, refusal and safe-diagnostic contract.
- `tests/test_chart_loader.py:130-160` tests special-cell text cleanup and CSV
  grammar, not source RGB provenance. `tests/test_team_charts.py:555-571` checks
  BLACK values after loading but has no shared token/color legend to reuse.

Do not reuse Excel layouts, NFL behavior, permissive cleanup, default output paths
or broad exception handling. No Paydirt code, team data or runtime dependency is
added.

## Acceptance

- Directory export is deterministic, nonrecursive, safe against symlinks and
  destination conflicts, and reports each file plus a correct aggregate exit code.
- Every file is independently transactional; rollback restores original bytes and
  attempts all recovery steps even if one restore fails.
- Duplicate season/team identities refuse every conflicting PDF. Dry-run performs
  the same deterministic validation as export without writing files.
- Diagnostics reveal only project-owned safe reasons and source page/position, not
  arbitrary parser messages, filenames or chart text.
- Inspection accepts one PDF file only; export rejects symlinked input directories.
- Player/maintainer guidance covers batch use and troubleshooting; PDF dependencies
  remain optional and excluded from runtime/native release requirements.
- Focused tests, applicable cumulative checks, documentation, Paydirt notes and
  ticket commit references are recorded before the dedicated milestone commit.

## Work log

### 2026-10-30 — IMPORT-001

- Baseline synthetic provenance mismatch test failed against unchanged code as expected:
  the reader did not raise `TeamFormatError`.
- Implemented shared color/token/RGB legend, reader and writer provenance checks, and removed
  the file-wide Ruff suppression. Regenerated only the fictional public sample provenance;
  refreshed its allowlist hashes and clarified the synthetic RGB documentation.
- Focused bundle, PDF import/export, sample and release packaging checks: 161 passed. Ruff,
  format and whitespace checks passed.
- Implementation commit: `8f6f759`. Resolution evidence is recorded in
  [IMPORT-001](issues/IMPORT/IMPORT-001.md); it remains resolved pending any required play test.
