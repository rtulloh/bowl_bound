---
id: IMPORT-014
title: Report safe actionable reasons for typed PDF export failures
status: open
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- diagnostics
- privacy
links: []
commits: []
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
