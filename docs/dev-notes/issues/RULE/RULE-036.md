---
id: RULE-036
title: QB Sneak treats an ignored yellow chart token as an actual timing penalty
status: open
priority: High
milestone: '23'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- reproduced
- code-review
links: []
commits: []
---

## Description

Review of 5294eb8..44d3438 reproduced a QB Sneak timing error in `session.py:1877-1882`. The sneak resolver correctly turns a yellow Play 1 cell into no gain, but `_record` infers penalty timing from every original LookupTrace cell. A yellow penalty token consulted only for its color therefore shortens the play to ten seconds even though no penalty occurred.

Synthetic reproduction: create `tests.test_qb_sneak.colored_chart((239, 255, 1), cell=NormalizedCell(ResultKind.PENALTY, provenance(), penalty=PenaltyData(PenaltyTeam.OFFENSE, PenaltyCode.FIXED, 5)))`; snap Q versus A with one `OffensiveRoll(1, 0, 0)`. The result is a completed zero-yard rush with down advanced, no pending decision or penalty enforcement, but `report.timing.penalty` is True and `duration(report.timing, Clock())` is 10 instead of 30. Yellow penalty boxes are a supported real chart category.

RULE-021 specifies color-only interpretation. Its yellow-box test uses a numeric token rather than a penalty token and never asserts timing. Assigned to milestone 23 after milestone 22 acceptance.

## Resolution / verification

- Derive timing from the executed sneak result; retain the original chart cell solely as source evidence.
- Test yellow penalty, white, green and red boxes through RegulationGame, with timing, stats, state, traces and save replay.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
