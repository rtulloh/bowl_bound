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
- The wider cumulative model check found and corrected one stale generic RGB fixture
  expectation in `f9a31b9`; all 111 model tests passed.

### 2026-10-30 — IMPORT-002

- Baseline synthetic regressions failed for non-UTF-8 rollback, a failed restore aborting
  remaining recovery, grayscale metadata color parsing, invented white metadata RGB, stale
  CLI milestone wording, invalid ticket dates without their path, and unversioned empty RGB.
- Implemented byte-exact best-effort rollback; one shared PDF RGB parser; explicit missing-fill
  metadata evidence; team-file version 2 with version-1 read compatibility; corrected docs and
  CLI wording; and path-qualified ticket date errors.
- Updated fictional sample YAMLs and release manifest hashes for the new bundle version.
- Focused importer/model/codec/issue/release regression slice: 404 passed; updated bundle
  suite: 73 passed; CLI suite: 28 passed. Ruff, format and whitespace checks passed.
- Implementation and help-test commits: `d8c9d9c`, `03ab1d8`. Resolution evidence is in
  [IMPORT-002](issues/IMPORT/IMPORT-002.md).

### 2026-10-30 — IMPORT-003

- Baseline tests on the parked draft reproduced the first-winner bug: nine collision assertions
  failed, including two-name aliases, three repeats, dry-run, and `--force`.
- The planner now gathers all `(season, slug)` owners before writing and refuses every PDF
  involved. It also tracks identities before rejecting an intra-PDF duplicate, preventing a
  second PDF with that identity from being written.
- Batch and CLI tests: 83 passed. Ruff, format and whitespace checks passed.
- Parked-branch implementation commit: `d1a43cb`. Integration onto the active Milestone 25
  branch remains assigned to [IMPORT-009](issues/IMPORT/IMPORT-009.md).

### 2026-10-30 — IMPORT-004

- Baseline tests reproduced that dry-run accepted existing targets and unsafe root/target types
  where export failed: six new assertions failed against the unchanged batch draft.
- Added a shared destination preflight for planning and the immediate write check. Dry-run now
  validates existing files, `--force`, root and target types, source aliases/hardlinks, and
  symlinked roots/parents without writing. Prepared serialized teams and summary metadata are
  reused across planning and export.
- Updated maintainer and player documentation to state the checks and the limits of dry-run.
- Focused batch/CLI/export-hardening suite: 97 passed. Ruff check, format check and
  `git diff --check` passed.
- Parked-branch implementation commit: `95cbe68`. Final integration remains assigned to
  [IMPORT-009](issues/IMPORT/IMPORT-009.md).

### 2026-10-30 — IMPORT-005

- Baseline tests reproduced seven CLI leaks from arbitrary `ValueError` and `OSError` messages;
  the generic parser-exception path already used a fixed message.
- Added typed project-owned CLI/inspection errors, a safe errno message map, and a fixed fallback
  for other failures. Removed path text from source-read errors and raw exception text from
  normalization and chart-construction validation errors. Kept the optional PDF install hint.
- Synthetic tests cover single-file inspection, batch export, and batch/single output failures;
  they assert both output streams are free of source sentinels and that unrelated PDFs continue.
- PDF importer and export-hardening tests: 194 passed. Ruff check, format check and
  `git diff --check` passed.
- Parked-branch implementation commit: `0f050eb`. Final integration remains assigned to
  [IMPORT-009](issues/IMPORT/IMPORT-009.md).

### 2026-10-30 — IMPORT-006

- Baseline input-contract tests failed five times: inspection accepted/scanned directories,
  and symlinked directory inputs reached inspection and export processing.
- Input discovery now rejects direct symlinks before directory checks. Inspection requires a
  single non-symlink PDF file; export accepts one file or a PDF directory. Existing sorted,
  nonrecursive, case-insensitive and hidden-file discovery behavior remains covered.
- Added both-mode tests for empty, one-PDF and multi-PDF directories, plus symlinked
  directory/file and dangling inputs. Refusals are verified to happen before scanning/parsing
  and without creating output. Updated CLI help, importer reference and player guide.
- PDF importer and export-hardening tests: 203 passed. Ruff check, format check and
  `git diff --check` passed.
- Parked-branch implementation commit: `a052138`. Final integration remains assigned to
  [IMPORT-009](issues/IMPORT/IMPORT-009.md).

### 2026-10-30 — IMPORT-007

- Reconsulted Paydirt `extract_charts.py:462-475`, `docs/chart-generator.md`, and
  `tests/ai_audit.py:197-199` / `tests/test_ai_audit.py:167-172`. Adapted serial independent-item
  failure isolation and structured result aggregation. Rejected lowercase-only `.xls` discovery,
  raw errors/tracebacks, unsafe partial output, and success exit after partial failure; no Excel
  layouts, NFL behavior, or runtime dependency was reused.
- Regression-first ordering assertion failed against case-sensitive `Path` sorting. Discovery
  now sorts case-insensitively with original filename as a deterministic tie-breaker. Per-PDF
  plan/result records replace positional index-to-error maps and recomputed aggregate state.
- Existing synthetic tests cover full success, mixed failures, empty directories, status ordering,
  hidden/non-PDF filtering, dry-run and aggregate exit codes. Focused importer/export-hardening
  suite: 203 passed. Ruff check, format check and `git diff --check` passed.
- Parked-branch implementation commit: `824b0c6`. Final integration remains assigned to
  [IMPORT-009](issues/IMPORT/IMPORT-009.md).

### 2026-10-30 — IMPORT-008

- Replaced the stale 5a–5c importer heading with a concise reference for one-file inspection,
  directory preview/export, per-file status, partial success, aggregate exit codes, collision
  handling, overwrites, symlinks, privacy and troubleshooting.
- Clarified `--force` in CLI help and added a help regression. Wheel metadata coverage confirms
  `pdfplumber` is in the `pdf` extra and `reportlab` is test-only in `dev`. The public native
  dependency lock and runtime manifest continue to exclude PDF libraries and importer tools.
- Shortened the player import walkthrough and marked it optional/advanced; detailed layout
  internals remain in the source-only reference. Packaged player links resolve within the exact
  release allowlist. Broader installation/onboarding work remains tracked by DEV-045.
- Synthetic importer, CLI and wheel tests: 208 passed. Native build workflow tests: 4 passed.
  Ruff, format, whitespace and packaged-link checks passed.
- Parked-branch implementation commit: `b0ad58d`. Root player-guide, release-boundary and
  acceptance evidence commits are recorded in [IMPORT-008](issues/IMPORT/IMPORT-008.md).
