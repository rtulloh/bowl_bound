---
id: IMPORT-011
title: Support alternate offense grid profiles in free MaysFootball PDFs
status: resolved
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- importer
- maysfootball
- pdf-layout
links: []
commits:
- def1311132006903792ef5620e3e6d04d986e5be
---

## Description

The 2005 offense pages and first two 2006 offense pages use a verified 20.28-point row pitch, distinct from the existing 17.40-point profile. They were rejected because the locator searched only the shorter chart region and found 27 of 30 printed anchors. Both geometries need explicit profiles; the 2002–2008 PDFs remain local-only test material.

## Resolution / verification

- For each newly supported geometry, add a synthetic fixture and a regression that fails against the unchanged locator.
- Validate all 30 printed roll anchors and exact expected column boundaries for each profile; preserve cell order and source coordinates.
- Do not infer or interpolate missing anchors, rows, or cells.
- Verify the affected source pages locally and confirm serialized charts load through the team reader.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 22:00 ---
The 2007 and 2008 offense profiles now pass local page geometry and reach later semantic
validation. 2005 and 2006 remain refused at the missing-anchor check; no rows or cell
positions are inferred.

--- 2026-10-30 21:59 ---
Added a synthetic 20.28-point row-grid profile test for both affected layout variants; it
failed against the previous locator and passes with explicit row bounds and 30-anchor
validation. The current batch dry run now validates all seven local PDFs, and all 18
historical team bundles pass strict team-file/provenance verification. Resolution remains
pending the milestone commit.
--- 2026-10-30 22:31 ---
Resolved in tested milestone commit `def1311132006903792ef5620e3e6d04d986e5be`. Full gate: `.venv/bin/python -m pytest --cov -q` — 2,595 passed, 93.37% coverage; the frontend tests/build and quality checks also pass. All seven local PDFs export successfully to 18 temporary bundles. No historical source files were committed. Keep resolved pending owner play-test confirmation; close only after that confirmation.
