---
id: RULE-038
title: Special-team returns still award a touchback after crossing their own end line
status: resolved
priority: High
milestone: '23'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- reproduced
- code-review
- incomplete-fix
links: []
commits:
- 1834ed7
---

## Description

Review of 5294eb8..44d3438 found an incomplete application of the RULE-013 correction. `turnovers._apply_return_yards` now checks END_LINE first, but `special_teams.SpecialTeamsPlay._return_cell` still returns a touchback whenever a return starts in the end zone and ends at or behind the goal line, including beyond the end line (`special_teams.py:499-515`).

Synthetic reproduction: use `SpecialTeamsPlay("kickoff", FieldState(Possession.HOME,65,1,10), special_chart("Home", kickoff=yards(70)), special_chart("Away", kickoff_return=yards(-5)), ScriptedDice([OffensiveRoll(1,0,0), OffensiveRoll(1,0,0)]), home_season=2002)`. begin() produces a kick landing five yards deep. Choosing kick:return carries the ball to the returner's end line. The result is TOUCHBACK with no points and away at its own 20; the approved profile requires a safety for home. Punt and recovered-kick returns share this method.

This is a residual pre-existing defect missed by the correction in the reviewed range, not a claim that the refactor first introduced it. RULE-013 tests exercise the turnover path but omit special-team return parity. Assigned to milestone 23 after milestone 22 acceptance.

## Resolution / verification

- Apply the goal-line/end-line distinction consistently to kickoff, punt, and recovered-kick returns.
- Add synthetic boundaries just before, on and beyond the end line for ordinary returns and accepted/declined return penalties, asserting score, possession, timing and free-kick scheduling.
- Reconcile the shared-return policy and RULE-013 verification notes with all entry paths.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Resolved in `1834ed7`. Synthetic kickoff and punt returns now cover one yard
short of, at, and beyond the receiving end line, and a recovered-ball return
uses the same safety boundary. The special-teams, shared-return, turnover,
regulation, and save regression set passed (211 tests), together with Ruff and
formatting. Awaiting owner play-test confirmation before closure.
