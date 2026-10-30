---
id: IMPORT-006
title: Enforce the milestone 25 input contract before discovering PDFs
status: open
priority: Medium
milestone: '25'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- review
- reproduced
- testing
links:
- IMPORT-007
- IMPORT-008
- IMPORT-009
commits: []
---

## Description

Batch draft 2822c3b calls path.is_dir() before path.is_symlink(), so a symlink to a directory is traversed and exported successfully. Inspection mode checks the discovered PDF count instead of the supplied argument type, so a directory holding one PDF writes an inspection report. Both are explicit outstanding milestone 25 requirements. Synthetic probes for each returned 0 when refusal was expected. Existing tests cover a symlinked PDF and a directory containing three PDFs, leaving these boundaries untested. Single-PDF directory inspection is currently documented on main; changing it should be an explicit milestone 25 contract change.

## Resolution / verification

- Reject a symlinked input directory before scanning or parsing any document, and require the original inspection-mode argument to be a single non-symlink PDF file.
- Add zero/one/multiple-PDF directory cases in both modes, symlink-to-directory/file and dangling-link cases; assert the parser is never invoked on refused input and no output appears.
- Update help, importer reference and player examples together. Preserve nonrecursive, sorted, case-insensitive PDF discovery and hidden-file handling for export.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
