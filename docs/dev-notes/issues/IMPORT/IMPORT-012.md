---
id: IMPORT-012
title: Resolve power-rating metadata for free MaysFootball chart PDFs
status: open
priority: High
milestone: '26'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- maysfootball
- metadata
- local-only-override
links: []
commits: []
---

## Description

The 2003–2008 MaysFootball PDFs have no numeric rating in the supported header box. The owner approved a local-only rating of 200 for private play-testing on 2026-10-30. The importer needs an explicit opt-in and a durable marker so this value is never mistaken for source data.

## Resolution / verification

- Preserve a valid printed rating even when the local placeholder option is enabled; reject numeric-but-ambiguous ratings.
- Use the approved rating of 200 only when no numeric rating is printed and the user explicitly opts in.
- Store a versioned `local-only-placeholder` marker in team metadata without inventing PDF coordinates or provenance text.
- Never silently substitute a default rating.
- Verify the 2003–2008 PDFs locally without putting source ratings or chart values in tests or tracked files.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 20:54 ---
Owner approved a local-only power rating of 200 for private play-testing and clarified that the rating does not affect game behavior. Implementation and source-PDF verification remain in progress.

--- 2026-10-30 22:00 ---
The explicit flag, versioned local-only marker, printed-rating preservation, and synthetic
round-trip tests are implemented. All seven local PDFs pass rating extraction with the
approved fallback where needed; the remaining batch failures occur at later validations.
Keep the issue open until the milestone change is committed.
