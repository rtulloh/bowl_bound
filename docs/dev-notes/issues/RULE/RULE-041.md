---
id: RULE-041
title: Resolve fumble recovery before offering a penalty choice
status: open
priority: High
milestone: '23'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- reproduced
- gameplay
- penalties
links: []
commits: []
---

## Description

When a prepared play has both a selectable penalty and a fumble result, the engine offers accept/decline before resolving fumble recovery. The decline label says recovery remains unresolved, so the offended team must gamble instead of comparing the completed play result against enforcement. Bowl Bound penalty choices must be made after the fumble outcome is determined.

## Resolution / verification

- Synthetic in-field fumble-plus-penalty regressions resolve recovery ownership, spot, scoring, and any required turnover consequence before rendering accept/decline choices.
- Penalty choices compare known engine-owned outcomes; no decline label leaves fumble recovery unresolved.
- Recovery dice are consumed exactly once, remain save/replay deterministic, and accepted enforcement does not apply a discarded fumble result.
- Interception, end-zone recovery, penalty, timing, statistics, and structured-trace behavior remain correct for both possessions.

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
