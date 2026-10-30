---
id: IMPORT-003
title: Refuse every PDF involved in a batch team collision
status: open
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- review
- reproduced
- data-integrity
links:
- IMPORT-007
- IMPORT-009
commits: []
---

## Description

Review of batch draft 2822c3b: tools/pdf_import/cli.py:_run_batch records keys in a forward-only seen set. Three synthetic PDFs containing the same season/slug produce one successful export and two failures; the first PDF is written. The roadmap requires all colliding PDFs to be refused. The existing test_the_same_team_in_two_pdfs_is_never_merged explicitly expects the first winner, so a green suite protects the wrong behavior. This is an already documented draft blocker now tracked as a ticket, not a newly introduced main-branch regression.

## Resolution / verification

- Collect canonical season/slug ownership for all PDFs before any writes, then reject every document participating in a collision regardless of discovery order or --force.
- Add synthetic two- and three-PDF repeats, case/spacing/slug aliases, one-PDF duplicate keys, and a colliding document containing another otherwise unique team. Preserve all-or-nothing per PDF while unrelated PDFs succeed.
- Replace the old first-winner assertion and explain the changed expectation against milestone 25 acceptance; verify identical refusal in dry-run and export.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
