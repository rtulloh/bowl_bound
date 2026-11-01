---
id: RULE-020
title: Define and implement option-specific defensive guesses
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- advanced-option
links: []
commits: [e0081ac, 2bea18e]
---

## Description

Milestone 22 calls for defensive guesses specific to SOP/BLP option plays. The current engine resolves options without a defensive guess. The exact guess choices, timing, and effect must come from Bowl Bound Advanced Rule II, not inference from another game.

## Resolution / verification

- Use the approved Play 5 Wild Card calls: Option Run (Play 5 alone), SOP (Play 5 plus Play 7), and BLP (Play 5 plus Play 8).
- Verify correct guesses stop at the documented no-gain/incomplete result; incorrect guesses use blank defense, preserve option rerolls, and double eligible yards only for conditional calls.
- Preserve called/resolved play identity, observed dice order, synthetic traces, and save replay. Correct guesses stop at no gain/incomplete; incorrect guesses use blank defense, retain option rerolls, and double only eligible conditional yardage.
- Test-first evidence: synthetic Play 5 run/SOP/BLP cases failed before Advanced II existed and now cover correct and incorrect guesses, dice order, branch identity, and conditional doubling.
- Tested commits: `e0081ac` implements option-specific guesses; cumulative regression was run on `2bea18e`.
- Validation: 2,904 Python tests passed at 92.76% branch-aware coverage; 35 focused Advanced II tests; 119 frontend tests; production build; npm audit with zero vulnerabilities; 33 real-engine browser tests; Ruff lint/format, pip check, and 18 issue-index tests all passed.
- Automated verification is complete. Owner play-test confirmation remains before closure.

## Comments

--- 2026-11-01 00:00 ---
Owner approved implementation of all three Play 5 Wild Card branches as part of the all-four Advanced II scope. No play-test confirmation has been recorded.

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 14:05 ---
Resolved after synthetic tests and cumulative regression passed on `2bea18e`. Kept open for owner play-test confirmation.
