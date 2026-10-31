---
id: IMPORT-014
title: Report safe actionable reasons for typed PDF export failures
status: resolved
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- importer
- diagnostics
- privacy
links: []
commits:
- def1311132006903792ef5620e3e6d04d986e5be
---

## Description

Batch export currently reduces several project-owned validation failures from layout and metadata extraction to “unexpected failure while exporting the document; the document may use an unsupported layout.” This obscures whether a source needs a supported layout, a rating, or another correction. Raw parser text must remain hidden.

## Resolution / verification

- Add CLI tests that exercise typed layout, metadata, and provenance failures and assert the safe actionable status shown to the user.
- Map only project-owned exception types to fixed or explicitly sanitized messages; keep unexpected third-party exception text redacted.
- Ensure batch processing continues for unrelated PDFs and aggregate exit status remains correct.
- Assert stdout and stderr do not contain source paths, chart text, or parser exception details.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 22:00 ---
Typed project validation failures now produce safe actionable CLI messages, and synthetic
tests confirm batch processing continues. The implementation is uncommitted; close the
issue only after the tested commit is recorded.
--- 2026-10-30 22:31 ---
Resolved in tested milestone commit `def1311132006903792ef5620e3e6d04d986e5be`. Full gate: `.venv/bin/python -m pytest --cov -q` — 2,595 passed, 93.37% coverage; the frontend tests/build and quality checks also pass. All seven local PDFs export successfully to 18 temporary bundles. No historical source files were committed. Keep resolved pending owner play-test confirmation; close only after that confirmation.
