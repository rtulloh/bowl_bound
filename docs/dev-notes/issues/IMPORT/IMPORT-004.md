---
id: IMPORT-004
title: Make dry-run perform the same destination validation as export
status: resolved
priority: Medium
milestone: '25'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- review
- reproduced
- testing
links:
- IMPORT-007
- IMPORT-009
commits: [95cbe68]
---

## Description

Confirmed on main ab4c70e and batch draft 2822c3b. Pre-create seasons/2002/synthetic-state/team.yaml, mock export_document with the existing synthetic _team fixture, and run the same export with and without --dry-run. Real export returns 1 and preserves the file; dry-run returns 0/status validated. Both paths return before _write_teams performs output safety checks. The draft also bypasses root/path checks for every planned PDF. docs/pdf-import.md promises output validation, and the new player guide tells users to validate before exporting.

## Resolution / verification

- Extract one side-effect-free destination preflight used by dry-run and real export, while retaining the immediate write-time safety recheck.
- Test existing targets with/without --force, root-as-file, source alias/hardlink, symlinked roots/parents, and a conflicting target directory. Dry-run must write nothing and match deterministic real-run failures; do not promise to predict later disk failures.
- Use a typed per-PDF plan for canonical keys, serialized targets and summary metadata instead of recomputing keys and passing positional four-element tuples/unparameterized lists between phases. Reuse verified serialized content where practical; preserve lazy PDF imports.
- Update both importer and player documentation to state exactly what preflight validates and retain synthetic partial-batch tests.

Implemented and committed on `wip/5d-batch-import` as `95cbe68`.

- Baseline: six new dry-run destination tests failed against the unchanged draft because dry-run reported success where export refused existing files, root/target type conflicts, symlinked paths and a source hardlink.
- A shared side-effect-free preflight now runs during planning and again immediately before writing. Dry-run and export return the same deterministic destination failures; `--force` permits existing files without modifying them during dry-run.
- A typed `PreparedTeam` retains round-tripped serialized files, canonical identity and summary counts. The batch plan reuses these values instead of serializing teams and deriving folder names again. PDF imports remain lazy.
- Updated maintainer and player docs with the preflight scope and its limit: later disk or permission failures cannot be predicted.
- Verification: `tests/test_pdf_batch.py tests/test_pdf_cli.py tests/test_pdf_cli_export.py tests/test_export_hardening.py` — 97 passed; Ruff check, Ruff format check and `git diff --check` passed.
- Final integration onto the active Milestone 25 branch remains tracked by IMPORT-009.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 00:00 ---
Dry-run destination validation is corrected and committed in `95cbe68`. The fix remains on the
parked batch branch pending integration under IMPORT-009; do not close before the integrated
Milestone 25 regression gate passes.
