---
id: IMPORT-006
title: Enforce the milestone 25 input contract before discovering PDFs
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
- IMPORT-008
- IMPORT-009
commits: [a052138]
---

## Description

Batch draft 2822c3b calls path.is_dir() before path.is_symlink(), so a symlink to a directory is traversed and exported successfully. Inspection mode checks the discovered PDF count instead of the supplied argument type, so a directory holding one PDF writes an inspection report. Both are explicit outstanding milestone 25 requirements. Synthetic probes for each returned 0 when refusal was expected. Existing tests cover a symlinked PDF and a directory containing three PDFs, leaving these boundaries untested. Single-PDF directory inspection is currently documented on main; changing it should be an explicit milestone 25 contract change.

## Resolution / verification

- Reject a symlinked input directory before scanning or parsing any document, and require the original inspection-mode argument to be a single non-symlink PDF file.
- Add zero/one/multiple-PDF directory cases in both modes, symlink-to-directory/file and dangling-link cases; assert the parser is never invoked on refused input and no output appears.
- Update help, importer reference and player examples together. Preserve nonrecursive, sorted, case-insensitive PDF discovery and hidden-file handling for export.

Implemented and committed on `wip/5d-batch-import` as `a052138`.

- Baseline: five input-contract tests failed. Inspection accepted or scanned directories, and a symlink to a directory reached both inspection and export processing.
- `_sources` now rejects direct symlinks before calling `is_dir` or listing candidates. Inspection accepts only a single non-symlink PDF file; export accepts one PDF or a directory.
- Synthetic tests cover empty, one-PDF and multi-PDF directories in both modes, plus symlinked directories/files and dangling links in both modes. Refused input is not scanned or parsed and creates no output. Existing export tests preserve sorted, nonrecursive, case-insensitive discovery and hidden-file handling.
- Updated CLI help, the importer reference and the player guide. The prior single-PDF directory inspection expectation was replaced by the explicit file-only contract.
- Verification: `tests/test_pdf_*.py tests/test_export_hardening.py` — 203 passed; Ruff check, Ruff format check and `git diff --check` passed.
- Final integration onto the active Milestone 25 branch remains tracked by IMPORT-009.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 00:00 ---
Input mode and symlink boundaries are tested and fixed in `a052138`. Final integration remains
tracked by IMPORT-009; do not close before the integrated milestone gate passes.
