---
id: IMPORT-003
title: Refuse every PDF involved in a batch team collision
status: resolved
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- review
- reproduced
- data-integrity
links:
- IMPORT-007
- IMPORT-009
commits: [d1a43cb]
---

## Description

Review of batch draft 2822c3b: tools/pdf_import/cli.py:_run_batch records keys in a forward-only seen set. Three synthetic PDFs containing the same season/slug produce one successful export and two failures; the first PDF is written. The roadmap requires all colliding PDFs to be refused. The existing test_the_same_team_in_two_pdfs_is_never_merged explicitly expects the first winner, so a green suite protects the wrong behavior. This is an already documented draft blocker now tracked as a ticket, not a newly introduced main-branch regression.

## Resolution / verification

- Collect canonical season/slug ownership for all PDFs before any writes, then reject every document participating in a collision regardless of discovery order or --force.
- Add synthetic two- and three-PDF repeats, case/spacing/slug aliases, one-PDF duplicate keys, and a colliding document containing another otherwise unique team. Preserve all-or-nothing per PDF while unrelated PDFs succeed.
- Replace the old first-winner assertion and explain the changed expectation against milestone 25 acceptance; verify identical refusal in dry-run and export.

Implemented and committed on `wip/5d-batch-import` as `d1a43cb`.

- Baseline: nine new export/dry-run collision assertions failed. The first PDF was written,
  later aliases failed, and three repeats still allowed the first PDF to succeed.
- The batch planner now records canonical `(season, slug)` ownership for the full input set
  before writes. Every document in a collision is refused, including under `--force`; an
  unrelated PDF still succeeds. Duplicate identities inside a single PDF are also recorded
  before that document is rejected, so another matching PDF is refused too.
- Synthetic coverage includes two- and three-PDF repeats, case/spacing/slug aliases,
  `--force`, dry-run, same-PDF duplicates, a colliding PDF with an otherwise unique team, and
  an unrelated successful PDF. The prior first-winner expectation was replaced.
- Verification: `tests/test_pdf_batch.py tests/test_pdf_cli.py tests/test_pdf_cli_export.py`
  — 83 passed; Ruff check, Ruff format check and `git diff --check` passed.
- The fix is on the parked draft branch pending final integration under IMPORT-009; do not
  close this issue before that integration is verified.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 00:00 ---
Collision behavior is corrected and committed in `d1a43cb`. Final integration into the active
Milestone 25 branch remains tracked by IMPORT-009.
