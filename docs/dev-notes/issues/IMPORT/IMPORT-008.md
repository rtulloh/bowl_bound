---
id: IMPORT-008
title: Document batch import troubleshooting and isolate optional PDF dependencies
status: open
priority: Medium
milestone: '25'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- documentation
- dependencies
links:
- IMPORT-006
- IMPORT-007
- IMPORT-009
commits: []
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
