---
id: IMPORT-008
title: Document batch import troubleshooting and isolate optional PDF dependencies
status: resolved
priority: Medium
milestone: '25'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- importer
- documentation
- dependencies
links:
- IMPORT-006
- IMPORT-007
- IMPORT-009
commits:
- b0ad58d
- b1e4b44
---

## Description

Deliver the Milestone 25 player and maintainer guidance for batch imports. Keep the ordinary game installation concise and keep PDF extraction dependencies optional so standalone/runtime users do not install importer tooling.

## Resolution / verification

- Add concise directory batch examples for dry-run and export, per-file statuses, aggregate exit behavior, overwrite rules and the single-file inspection contract.
- Add troubleshooting for unsupported layouts, ambiguous cells, partial batch failures, collisions, symlinks, existing destinations and private source handling without exposing chart text or local paths.
- Verify PDF/extractor packages remain in the optional pdf dependency group and absent from native runtime requirements and release artifacts.
- Update help text, docs/pdf-import.md, team/import player guidance and relevant links together; keep common player onboarding separate from optional extractor setup.
- Test documented commands and dependency boundaries with synthetic/public-safe fixtures.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

### 2026-10-30 — Resolution evidence

- `b0ad58d` updates importer help and the source-only reference, and adds wheel metadata
  coverage for optional PDF dependencies. `b1e4b44` streamlines the player guide and tests
  that the native release lock and manifest exclude the importer.
- The unchanged CLI failed the new `--force` help assertion; after the wording fix, the
  complete synthetic importer, CLI and wheel slice passed (208 tests). Native workflow
  tests passed (4 tests). Ruff, formatting, whitespace and packaged player-link checks passed.
- `pdfplumber` remains in the optional `pdf` extra; `reportlab` remains in `dev`; neither
  is in native requirements. The release allowlist excludes `tools/` and `docs/pdf-import.md`.
- The player import page is 100 lines, down from 196, and now labels the extractor as
  optional/advanced. General installation and onboarding cleanup remains tracked by DEV-045.
- No MaysFootball or other historical chart files were imported, committed or packaged.
  Keep this ticket resolved, not closed, until the milestone play-test confirmation.
