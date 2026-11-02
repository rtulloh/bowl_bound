---
id: RULE-037
title: Conditional Wild Card incorrectly doubles QB Sneak despite the Rule IX exemption
status: open
priority: High
milestone: '23'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- reproduced
- code-review
- test-expectation
links: []
commits: []
---

## Description

Review of 5294eb8..44d3438 found a rule and test expectation error. `resolve_qb_sneak` marks wrong conditional Wild Cards for doubling (`resolution.py:361-369`), and `_apply_live_result` doubles every eligible nonnegative YARDS result without excluding resolution.qb_sneak. The existing test `test_conditional_mismatched_wild_card_doubles_green_sneak_yardage` asserts two yards and therefore locks in the error.

Authoritative local rulebook `docs/reference/bbrules2007.pdf`: Advanced II-1(C), printed page 17, applies the conditional doubling with the same exclusions as Advanced IX. Advanced IX, printed page 30, explicitly excludes quarterback sneaks along with negative final yardage, penalties and special-team entries. The approved rules profile also retains Rule IX exclusions; no deliberate project override for sneak doubling is documented. RULE-021 and milestone 22 say eligible yardage doubles, which does not remove that exclusion.

Synthetic reproduction: a green Play 1 chart box, `snap("Q", "WC1")`, one offensive roll, and an unmarked defender return two yards; the color-only QB Sneak should gain one. A test already reproduces the incorrect two-yard result. This can turn fourth-and-two into a first down or score from the two-yard line.

Assigned to milestone 23 as a rules-correctness follow-up. Correct the existing expectation with the source explanation; do not merely add a new test mirroring the current result.

## Resolution / verification

- Exclude QB Sneak from conditional yardage doubling while keeping a correct WCSNEAK stop at zero.
- Update the contrary test expectation and add goal-line/fourth-down coverage for correct and wrong Wild Cards with both conditional and W-marked defenders.
- Reconcile RULE-021 notes and current rules documentation with the Rule IX exemption, documenting any separately approved override explicitly.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
