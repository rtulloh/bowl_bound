---
id: IMPORT-004
title: Make dry-run perform the same destination validation as export
status: open
priority: Medium
milestone: '25'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- review
- reproduced
- testing
links: []
commits: []
---

## Description

Confirmed on main ab4c70e and batch draft 2822c3b. Pre-create seasons/2002/synthetic-state/team.yaml, mock export_document with the existing synthetic _team fixture, and run the same export with and without --dry-run. Real export returns 1 and preserves the file; dry-run returns 0/status validated. Both paths return before _write_teams performs output safety checks. The draft also bypasses root/path checks for every planned PDF. docs/pdf-import.md promises output validation, and the new player guide tells users to validate before exporting.

## Resolution / verification

- Extract one side-effect-free destination preflight used by dry-run and real export, while retaining the immediate write-time safety recheck.
- Test existing targets with/without --force, root-as-file, source alias/hardlink, symlinked roots/parents, and a conflicting target directory. Dry-run must write nothing and match deterministic real-run failures; do not promise to predict later disk failures.
- Use a typed per-PDF plan for canonical keys, serialized targets and summary metadata instead of recomputing keys and passing positional four-element tuples/unparameterized lists between phases. Reuse verified serialized content where practical; preserve lazy PDF imports.
- Update both importer and player documentation to state exactly what preflight validates and retain synthetic partial-batch tests.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
