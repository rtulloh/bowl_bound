---
id: IMPORT-017
title: Support alternate fumble-recovery metadata profiles
status: resolved
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- importer
- metadata
- maysfootball
links: []
commits:
- def1311132006903792ef5620e3e6d04d986e5be
---

## Description

With the owner-approved local rating fallback enabled, some MaysFootball PDFs still fail because the rotated recovery text shifts a few points left of the original right-edge threshold. The export must not invent roll ranges or silently use a default.

## Resolution / verification

- Add synthetic PDFs for the verified alternate recovery presentation and for absent or ambiguous recovery evidence.
- Preserve source page, text, coordinates, and hash for any supported recovery range.
- Keep missing, overlapping, or incomplete recovery ranges safely refused.

The supported column window now includes the verified small left shifts. The change is
implemented but uncommitted; keep this ticket open through milestone acceptance and record
the tested commit.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 21:55 ---
Added synthetic regressions for both verified left-shift positions; they failed before the
threshold change and pass now. The seven local PDFs all pass recovery-metadata extraction;
the batch dry run proceeds to separate geometry or decorated-result blockers. No endpoints
or team data are recorded here.
--- 2026-10-30 22:31 ---
Resolved in tested milestone commit `def1311132006903792ef5620e3e6d04d986e5be`. Full gate: `.venv/bin/python -m pytest --cov -q` — 2,595 passed, 93.37% coverage; the frontend tests/build and quality checks also pass. All seven local PDFs export successfully to 18 temporary bundles. No historical source files were committed. Keep resolved pending owner play-test confirmation; close only after that confirmation.
