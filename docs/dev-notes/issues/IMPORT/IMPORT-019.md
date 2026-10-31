---
id: IMPORT-019
title: Resolve chart text crossing cell boundaries safely
status: resolved
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- importer
- pdf-layout
- maysfootball
links: []
commits:
- def1311132006903792ef5620e3e6d04d986e5be
---

## Description

A locally tested MaysFootball PDF is rejected because one or more text characters cross a detected chart-cell boundary. Investigate the supported layout and character-to-cell assignment, then accept only placements that can be assigned unambiguously. Keep historical team names, source coordinates, cell contents, and private evidence out of this ticket.

## Resolution / verification

- Add a synthetic PDF regression for the boundary condition and a nearby unambiguous placement.
- Preserve fail-closed behavior for genuinely ambiguous text; do not drop, duplicate, or silently reassign source characters.
- Preserve source text and provenance through extraction and team export, and validate all chart-cell counts and anchors.
- Rerun the affected local PDF dry run and strict team-file validation; keep historical outputs private and ignored.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 21:59 ---
Added a synthetic PDF regression that assigns a glyph with a small edge overhang exactly
once based on its unique center cell. Tests still reject ambiguous centers and larger
overhangs. The 2007 source now passes the complete dry run and strict team-file/provenance
verification; resolution remains pending the milestone commit.
--- 2026-10-30 22:31 ---
Resolved in tested milestone commit `def1311132006903792ef5620e3e6d04d986e5be`. Full gate: `.venv/bin/python -m pytest --cov -q` — 2,595 passed, 93.37% coverage; the frontend tests/build and quality checks also pass. All seven local PDFs export successfully to 18 temporary bundles. No historical source files were committed. Keep resolved pending owner play-test confirmation; close only after that confirmation.
