---
id: RULE-035
title: Conditional Run/Pass classification is stale after penalty rerolls
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

Review of 5294eb8..44d3438 reproduced inconsistent Advanced II yardage after a declined penalty. `resolution.py:279-297` computes conditional_double from the first offensive cell; `penalties.py:213-220` carries it unchanged through rerolls, including QR/QT and Option branch changes.

Synthetic reproduction: use `tests.test_coaching_decisions_v8._penalty_chart("Home", PenaltyTeam.DEFENSE, NormalizedCell(ResultKind.QUARTERBACK_RUN, provenance()), 5)` and replace its supplemental cells with four-yard synthetic results. Start an advanced_ii PlaySession, then snap Play 1 versus RUN with offensive 10, defensive 2, offensive 20, supplemental 10; decline DEF5. The resulting QR gains four yards. A direct QR with the same conditional RUN defense and same supplemental result gains eight. The approved RULE-019 profile explicitly classifies QR/QT as passes for conditional guessing; a declined penalty must not freeze the pre-reroll classification.

Current tests cover direct QR/QT and direct SOP/BLP, but no classification-changing penalty reroll. Assigned to milestone 23 after milestone 22 acceptance.

## Resolution / verification

- Recompute conditional correctness from the resolved play/result after penalty and supplemental routing as required by the approved profile.
- Cover declined penalties into QR/QT and SOP/BLP, with RUN/PASS and W-marked versus conditional defenders; preserve fixed table row rules and physical dice traces.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
