---
id: RULE-033
title: Wrong Wild Card guesses stop Option runs as if WC5 was called
status: resolved
priority: High
milestone: '23'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- reproduced
- code-review
links: []
commits: [e63ef70]
---

## Description

Review of 5294eb8..44d3438 reproduced an Advanced II error in `bowl_bound/resolution.py:261-276`. For Play 5, the branch check compares only `call[3:]` with the resolved branch; it never requires the guessed play to be 5. Every ordinary WC1–WC4/WC6–WC9 call has an empty suffix and is therefore treated as a correct Option-run guess.

Synthetic reproduction: use `tests.test_advanced_defenses.new_game(rolls=(OffensiveRoll(1, 0, 0),))` and call `snap("5", "WC1")` (also WC2 and WC9). The chart's four-yard Option run becomes zero yards. Expected: eight yards for a conditional wrong guess; four for a W-marked defender. Only WC5 should stop that run. This contradicts RULE-019 and the exact-guess rule in docs/rules-profile.md.

Existing tests cover correct WC5 variants and a wrong SOP/BLP branch, but omit wrong numbered guesses against an Option run. Assigned to follow-up milestone 23 because milestone 22 is committed.

## Resolution / verification

- Test-first reproduction added a synthetic matrix for every wrong numbered Wild
  Card across Option run, SOP, and BLP branches, for conditional and W-marked
  defenders. Before the fix, all Option-run cases stopped at zero yards.
- `e63ef70` requires both a Play 5 guess and an exact branch match before the
  Wild Card stop applies. Other numbered guesses resolve normally; a conditional
  defender doubles eligible yardage and a W-marked defender does not.
- Focused validation: 146 Advanced II, resolution, and coaching-evaluation tests
  passed; Ruff lint/format and `git diff --check` passed.
- Status is resolved pending owner play-test confirmation.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Test-first failure reproduced the reported Option-run zero-yard behavior. The
tested fix in `e63ef70` awaits owner play-test confirmation before closure.
