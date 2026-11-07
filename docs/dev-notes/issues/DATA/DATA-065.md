---
id: DATA-065
title: Track persistent season-long team statistics and results for players
status: open
priority: Medium
milestone: 43
created-at: 2026-11-07
resolved-at: null
closed-at: null
tags: [feature, season-statistics, persistence, player-experience, backlog]
links: []
commits: []
---

## Description

Players should be able to follow how teams perform over the course of a played
season. Retain completed game results and accumulate team statistics so players
can inspect records, cumulative totals, per-game averages and progress after
each game, then resume that same season in a later session.

This is a player feature, separate from developer-only season audit scripts.
A historical year is not a unique played season: players may run multiple
independent seasons with the same charts. Assign each campaign its own identity.
The engine's finalized game statistics and scoring facts remain authoritative;
the UI must not infer results from commentary or interpret chart values.

## Resolution / verification

- Define a persistent season/campaign record with name, source year, stable team
  identities and completed game IDs/results; support creating, selecting and
  resuming separate played seasons without mixing their records.
- Present each team's games played, wins/losses/ties where supported, points for
  and against, cumulative rushing/passing/total-offense statistics, touchdowns,
  interceptions thrown and sacks taken using the engine's supported statistics.
  Include clearly labeled per-game averages, sortable team comparisons and a
  chronological game-results view so players can see progress.
- Commit each completed game's final result and statistics exactly once.
  Loading/replaying a save, retrying a completion request or reopening the UI must
  not count the same game again. Keep in-progress and abandoned games distinct
  from completed totals; define safe explicit correction/removal behavior.
- Preserve totals, result history and campaign identity through game/season
  save-load and application restarts. Retain source year/chart/rules identity
  sufficiently to detect incompatible or mixed-season records.
- Aggregate in a shared backend/domain service from structured engine facts.
  Make manual CLI/web games usable with the season record, and provide a
  player-facing season view; define initial frontend/CLI scope during planning.
- Preserve Bowl Bound college statistical conventions, including sacks in
  rushing totals, overtime, nullified plays and final turnover credit. Do not
  promise unsupported player or special-team statistics or turn unknowns into zero.
- Add self-contained synthetic tests first for multiple teams, swapped home/away
  roles, independent campaigns, repeated save/load/completion, final versus
  unfinished games, corrections and exact reconciliation of every displayed
  cumulative total to retained final game boxes.
- Keep player season data private/local by default, with explicit storage and
  migration/recovery behavior. Do not require cloud accounts or publish saves,
  charts or detailed play logs as part of the feature.
- Document player controls and run applicable engine/API/persistence/frontend
  regressions and a multi-game save/resume play-test before closure.

## Comments

--- 2026-11-07 — owner feature request ---

Added to the backlog at the owner's request: let players watch team performance
through a season. Assigned to future Milestone 43; this does not expand the active
Milestone 42 / 1.0.0 correction release. No implementation is claimed.
See [Milestone 43](../../milestone-43.md).
