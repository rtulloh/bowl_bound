---
id: FLOW-005
title: Attach optional roster context to new-game and load lifecycles
status: resolved
priority: Medium
milestone: 21a
created-at: 2026-10-28
resolved-at: 2026-10-28
closed-at: null
tags:
- tested
- awaiting-playtest
links: [CLI-036, DEV-030, DEV-031, FLOW-003]
commits: ["0b2f030","4457887"]
---

## Execution order

Depends on: DEV-030, FLOW-003.
See [Milestone 21a plan](../../milestone-21a.md) for the full dependency order.

## Description

Connect canonical team IDs to optional validated rosters for CLI and backend new/load paths, then provide that context to engine narration. Keep path validation and privacy in the existing loader and apply the reviewed lifecycle policy consistently.

## Resolution / verification

- Write synthetic red-first tests for both teams, home/away human selection, reversed team arrangements, drive/regulation paths and API/CLI create/load entry points.
- Missing roster files or empty positions remain playable with generic names; malformed existing files follow the documented strict error contract without echoing names or file contents.
- Canonical team identity, not display-name guesses, selects rosters; preserve existing size/UTF-8/path/symlink validation.
- Do not introduce a dependency on local historical files, a whole-roster browser payload, or a Paydirt runtime import; session contexts must not leak between games.

## Comments

--- 2026-10-28 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-28 implementation ---
Paydirt commentary.py:94–114 reviewed: adapt positional context separation, not
silent malformed-file fallback or global caches. Tests independently reviewed
before red: corrected volatile save-envelope comparison, atomicity evidence and
registry-eviction proof. First red uncovered unsupported synthetic2026 regulation
season; corrected all fixtures to2007, reviewed and reran:8 expected failures.
Added private atomic SavedGame roster snapshots, CLI startup/load attachment and
API creation/load validation before registration. Review before green pending.

Implementation review found no production blockers and requested acceptance
matrix expansion: added CLI main startup/load across human sides/reversed teams
and drive/regulation, independent contexts, exact roster errors/intermediate
symlinks. Reviewed before tests. Focused gate174 passed in16.81s. Initial command
misspelled test_api_saves.py as test_save_api.py (no tests ran); corrected command
passed. Ruff found import ordering only; fixed before final review.
