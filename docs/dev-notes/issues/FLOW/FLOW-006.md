---
id: FLOW-006
title: Use verified starters for roster-backed commentary names
status: resolved
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- reproduced
links: []
commits:
- def1311132006903792ef5620e3e6d04d986e5be
---

## Description

Roster-backed commentary currently rotates across every listed player, so reserves can be narrated as starters even when verified starting-lineup data is available. Add explicit starter metadata to optional rosters and use that starter pool for commentary while preserving legacy rosters without starter metadata.

## Resolution / verification

- Synthetic tests cover starter selection, deterministic rotation, fallback for positions without starter metadata, strict starter-name validation, and legacy roster compatibility.
- Private historical roster files mark only source-verified starters for QB, RB, WR, and TE, with source notes; unavailable evidence is documented rather than guessed.
- Documentation explains starter metadata and local-only roster updates; historical rosters remain ignored and excluded from releases.

## Comments

--- 2026-10-30 22:19 ---
Local startup reproduction exposed malformed empty keys and OCR residue in historical
roster JSON; the files were corrected without adding them to Git. The same two-team CLI
startup now loads both bundles and exits cleanly. All 18 ignored roster files parse, all
starter names resolve to entries in their position lists, and the synthetic roster and
commentary tests pass. A verified fullback starter is included in the corresponding RB
commentary pool. Historical file contents remain private.

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
--- 2026-10-30 22:31 ---
Resolved in tested milestone commit `def1311132006903792ef5620e3e6d04d986e5be`. Full gate: `.venv/bin/python -m pytest --cov -q` — 2,595 passed, 93.37% coverage; the frontend tests/build and quality checks also pass. The local terminal startup and all 18 ignored roster validations also pass. Starter metadata is synthetic-tested and source-backed. No historical source files were committed. Keep resolved pending owner play-test confirmation; close only after that confirmation.
