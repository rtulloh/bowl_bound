---
id: RULE-034
title: Exact WCRZDZ incompletion does not consume a down or turn over on fourth down
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

Review of 5294eb8..44d3438 reproduced a state-transition error in `bowl_bound/session.py:864-894`. The exact WCRZDZ branch records an incomplete pass with identical before/after state and returns before `_apply_live_result`/`apply_result`. It never updates `_field`.

Synthetic reproduction: `tests.test_advanced_defenses.new_game().snap("RZDZ", "WCRZDZ")` leaves first-and-10 as first-and-10. Set the synthetic drive to `FieldState(Possession.HOME, 65, 4, 10)` and make the same call: home retains fourth-and-10, although an incomplete fourth-down pass must give away possession. Dice remain correctly unused and the report credits a pass attempt, making state and statistics disagree.

`tests/test_razzle_dazzle.py::test_exact_razzle_wild_card_ends_incomplete_without_any_dice` asserts the label/result/trace but never the down or possession. RULE-028 requires the normal state/timing/statistics paths. Assigned to milestone 23 as a follow-up to committed milestone 22.

## Resolution / verification

- Apply the normal incomplete-pass transition while retaining the no-dice WCRZDZ procedure.
- Cover downs 1–4, turnover-on-downs, regulation timing, two-point tries, and save continuation using synthetic charts.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
