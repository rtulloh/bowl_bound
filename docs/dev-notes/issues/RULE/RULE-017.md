---
id: RULE-017
title: Advance periods without a separate runoff choice
status: resolved
priority: Medium
milestone: '27'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- requested
links: []
commits: [52c7d08]
---

## Description

Owner requested removal of the separate normal clock:runoff choice. Standard timing should resolve implicitly when the next action is selected. A Q1/Q3 transition then runs that selected play in the next quarter; a half/game boundary transitions without running or rolling an extra play. Kneeldown remains the play for deliberately running down the clock. Preserve timeout requests through CLI-038 play/timeout suffixes and existing Bowl Bound timing.

## Resolution / verification

- Apply prior-play standard timing once without offering a runoff or Continue action in the CLI, API view, or browser. Preserve legacy replay support for existing saves.
- At Q1/Q3 boundaries, advance before running the selected next action, preserving down, ball spot, and possession. At halftime/game end, transition without a new play, dice, log entry, or statistics credit.
- Kneeldown remains a legal play and uses its normal chart timing.
- Keep 7T/AT timeout requests engine-offered and deterministic; verify timeout, period-boundary, game-end, save/resume, and no-extra-roll behavior with synthetic regression tests.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 ---
Resolved in tested commit `52c7d08`: no player-facing runoff/Continue action;
Q1/Q3 advance into the next selected play, and halftime/final transitions add no
play, dice, log entry, or statistics credit. Full Python, frontend, build, audit,
and real-engine browser gates pass. Awaiting owner play-test confirmation before closure.
