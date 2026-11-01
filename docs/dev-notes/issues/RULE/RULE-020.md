---
id: RULE-020
title: Define and implement option-specific defensive guesses
status: open
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- advanced-option
links: []
commits: []
---

## Description

Milestone 22 calls for defensive guesses specific to SOP/BLP option plays. The current engine resolves options without a defensive guess. The exact guess choices, timing, and effect must come from Bowl Bound Advanced Rule II, not inference from another game.

## Resolution / verification

- Use the approved Play 5 Wild Card calls: Option Run (Play 5 alone), SOP (Play 5 plus Play 7), and BLP (Play 5 plus Play 8).
- Verify correct guesses stop at the documented no-gain/incomplete result; incorrect guesses use blank defense, preserve option rerolls, and double eligible yards only for conditional calls.
- Preserve called/resolved play identity, observed dice order, synthetic traces, and save replay. Record the tested commit before resolution; play testing is still required before closure.

## Comments

--- 2026-11-01 00:00 ---
Owner approved implementation of all three Play 5 Wild Card branches as part of the all-four Advanced II scope. No play-test confirmation has been recorded.

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
