---
id: IMPORT-015
title: Support or clearly refuse four-component PDF cell colors
status: open
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- maysfootball
- provenance
- color
links: []
commits: []
---

## Description

The 2008 MaysFootball free-download PDF exposes filled cell colors as four-component tuples. The current provenance color parser accepts only grayscale and RGB shapes, so rotated-page cell extraction fails before export. The source color space and any conversion must be established explicitly; dropping a channel or guessing RGB would corrupt color evidence.

## Resolution / verification

- Add synthetic vector-PDF tests for the observed four-component color shape and confirm they fail against the unchanged parser.
- Establish the PDF color space and use a documented, deterministic conversion only when source evidence supports it; otherwise reject with a typed safe error.
- Preserve source hash, page, cell coordinates, original text, and normalized color provenance for supported cells.
- Run local verification on the 2008 PDF outside ordinary test collection; do not add historical chart values or PDFs to repository tests, runtime files, or releases.

The DeviceCMYK conversion and exact converted-palette mapping are implemented but not yet
committed. Keep this ticket open through milestone acceptance and record the tested commit.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 21:40 ---
The local PDF content uses the DeviceCMYK fill operator. A synthetic CMYK vector-PDF
regression verifies conversion, while exact converted palette signatures reject unknown
colors instead of selecting a nearest legend color. Local extraction now classifies every
fill on the two rotated 2008 defense pages; no 2008 team is written because recovery
metadata and two decorated named results remain unresolved. No chart values are recorded.

--- 2026-10-30 21:55 ---
Recovery metadata is now supported on the local 2008 pages (IMPORT-017). The remaining
reason the 2008 teams are refused is decorated named-result semantics (IMPORT-016).
