---
id: IMPORT-013
title: Resolve Mays 2002 red-filled defensive yardage cells safely
status: open
priority: High
milestone: '26'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- maysfootball
- provenance
- chart-semantics
links: []
commits: []
---

## Description

The 2002 MaysFootball PDF contains exact-zero yardage cells whose source fill can be red or green. The CSV token `0` has no sign, so inferring its color from token text alone can make a correct source cell disagree with provenance. Use the measured source RGB only to disambiguate an exact zero; do not infer color for any other token.

## Resolution / verification

- Add synthetic red/green exact-zero regressions.
- Preserve existing color checks for every nonzero or named token.
- Preserve the original token, RGB evidence, page, and cell position for any supported representation.
- Verify local team-file serialization and reload; do not weaken existing provenance consistency checks.

The exact-zero disambiguation is implemented but not yet committed. Keep the ticket open
through milestone commit and record the tested commit before marking it resolved.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 21:20 ---
Synthetic tests show red and green zero-yard cells round-trip while preserving their measured
RGB. Both local 2002 teams now pass the current exporter dry run and strict team-file reader;
the existing red/green validation remains in place for all other tokens. The fix remains
uncommitted pending Milestone 26 acceptance.
