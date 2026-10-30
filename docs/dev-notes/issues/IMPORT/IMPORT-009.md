---
id: IMPORT-009
title: Finish Milestone 25 acceptance and merge the parked batch importer
status: open
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- milestone
- validation
links:
- IMPORT-002
- IMPORT-003
- IMPORT-004
- IMPORT-005
- IMPORT-006
- IMPORT-007
- IMPORT-008
commits: []
---

## Description

Integrate the repaired batch importer onto the public main lineage and close Milestone 25 with reproducible acceptance evidence. The parked draft is not complete until all milestone tickets are reviewed, documentation is current and the dedicated milestone commit exists.

## Resolution / verification

- Review every open Milestone 25 ticket, require tested commit references before marking resolved, and keep unresolved scope explicit.
- Run focused batch/importer tests, the enforced release/importer coverage checks, the full Python/frontend/browser gate and any private local verification separately reported.
- Record Paydirt references, changed expectations, synthetic evidence, privacy review and exact commands in a Milestone 25 note under docs/dev-notes/.
- Merge the completed work without private PDFs, reports or historical teams; regenerate the issue index and verify all links.
- Create the dedicated commit with subject milestone 25: support batch team PDF imports only after acceptance criteria pass.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
