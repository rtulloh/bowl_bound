---
id: IMPORT-001
title: Cross-check CSV cell colors against provenance and share one legend table
status: open
priority: Medium
milestone: "25"
created-at: 2026-10-26
resolved-at:
closed-at:
tags: [importer, data-integrity]
links: []
commits: []
---

## Description

`bowl_bound/team_csv.parse_cell:248-272` infers the `ChartColor` purely from the token text
(falling back to green) and re-attaches the provenance unchanged, so a hand-edited bundle row
such as token `5` with red provenance RGB loads as an ordinary gain without error, although
docs/team-bundle.md advertises strict whitelists. Legend knowledge is encoded three times:
`normalization.py:52-63` (token to kind and color), `team_csv.py:183-272` (format_cell and
parse_cell) and `export.py:41-47` (RGB to color). `team_csv.py:1` also disables several ruff
rules for the whole file, hiding issues such as the `re`/`l` names at line 535.

## Resolution / verification

- Add failing synthetic tests where a token's class disagrees with the provenance RGB and
  expect a clear TeamFormatError naming the row and page only.
- Expose one legend table from normalization and derive format_cell, parse_cell color
  inference and the exporter's RGB mapping from it.
- Replace the whole-file noqa with targeted suppressions or fixes; keep the round-trip tests
  green and update docs/team-bundle.md.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.
