---
id: IMPORT-018
title: Preserve out-of-bounds markers on no-change chart cells
status: open
priority: High
milestone: '26'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- serialization
- timing
links: []
commits: []
---

## Description

A synthetic no-change cell with a valid out-of-bounds marker is accepted by the chart model, but CSV serialization drops the marker and writes an empty token. The bundle then changes timing semantics and fails chart round-trip validation. Keep the finding and evidence synthetic/public-safe.

## Resolution / verification

- The synthetic regression failed before the fix: `format_cell` returned an empty token for
  a valid `NO_CHANGE` cell carrying `out_of_bounds=True`.
- The serializer now emits the canonical out-of-bounds-only token. Synthetic CSV/YAML and
  provenance round trips cover offense, defense and special-teams rows.
- Focused tests pass. The 2002 source export now validates end to end; the ticket remains
  open until the milestone change is committed and the tested commit is recorded.

- Round-trip synthetic NO_CHANGE cells with out-of-bounds markers through offense, defense, and special chart serialization where that cell kind is valid.
- Verify the serialized token preserves the marker, reloads to the same normalized fact, and remains consistent with source color provenance.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
