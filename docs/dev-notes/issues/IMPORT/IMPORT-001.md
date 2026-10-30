---
id: IMPORT-001
title: Cross-check CSV cell colors against provenance and share one legend table
status: resolved
priority: Medium
milestone: "25"
created-at: 2026-10-26
resolved-at: 2026-10-30
closed-at:
tags: [importer, data-integrity]
links: []
commits: [8f6f759, f9a31b9]
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

Implemented and committed as `8f6f759`.

- Baseline: the new synthetic reader regression failed against the unchanged implementation
  with `DID NOT RAISE TeamFormatError` after the CSV token was paired with red RGB provenance.
- After the fix: the reader reports only CSV file/row and PDF page, and writer validation
  rejects the same mismatch before emitting files. Synthetic token/color cases cover yardage,
  named results, events, penalties, blank/no-change and incomplete markers.
- The shared legend now supplies normalization token meanings, canonical CSV names, token
  color inference and exact RGB values used by PDF export. Whole-file Ruff suppression was
  removed; ambiguous local names were clarified and zipped chart columns now require equal
  lengths.
- Fictional sample provenance now carries legend-compatible synthetic RGB values; release
  manifest hashes were refreshed. Documentation distinguishes these placeholders from PDF
  measurements.
- Verification: `.venv/bin/python -m pytest tests/test_team_csv.py tests/test_pdf_export.py
  tests/test_sample_teams.py tests/test_pdf_cli_export.py tests/test_pdf_export_e2e.py
  tests/test_release_package.py tests/test_release_archive.py -q` — 161 passed;
  Ruff check, Ruff format check and `git diff --check` passed.
- Cumulative follow-up: the broader M25 regression run exposed one model test still expecting
  the old generic RGB fixture. Updated it to the new synthetic green evidence and committed
  as `f9a31b9`; `tests/test_models.py` — 111 passed.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-30 00:00 ---
Cumulative model tests found a stale RGB fixture expectation after the synthetic sample color
change. Updated that expectation in `f9a31b9`; all 111 model tests passed.
