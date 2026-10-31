---
id: IMPORT-010
title: Support portrait pages with rotated MaysFootball defense charts
status: open
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- maysfootball
- pdf-layout
links: []
commits: []
---

## Description

The 2008 MaysFootball free-download PDF contains offense and defense/special pages on portrait sheets. The defense content is rotated within the portrait page. The initial inspector required a landscape defense/special page and rejected page 2. A normalized rotation view is now in the worktree, but source-level cell extraction and a team-file round trip still need verification.

## Resolution / verification

- Add a synthetic PDF regression with portrait defense/special content rotated on the page; demonstrate failure against the unchanged inspector before implementing support.
- Recognize and normalize only the verified rotation/profile; retain original source page number, source hash, and cell provenance.
- Reject mixed, malformed, or ambiguous rotations rather than guessing cell positions.
- Verify the 2008 source PDF locally outside ordinary test collection and round-trip its exported team data after all required metadata decisions are resolved.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 20:54 ---
Synthetic inspection and end-to-end export regressions pass with the normalized rotation view. The local 2008 PDF now inspects pages 2 and 4 as 90-degree rotated defense/special pages, and each yields 480 chart positions. Full export remains blocked by separate missing-rating and four-component-color issues (IMPORT-012 and IMPORT-015); no historical chart values are recorded here.

--- 2026-10-30 21:40 ---
Cell extraction for both rotated pages now preserves original coordinates and recognizes
their verified converted fill palette. Full team export still waits on the separate
recovery-metadata and decorated-result questions; no chart values are recorded.

--- 2026-10-30 21:55 ---
The recovery metadata position is now verified for all seven local PDFs (IMPORT-017).
Rotated 2008 team export remains blocked by decorated named results; coordinates and fill
round trips are covered synthetically.
