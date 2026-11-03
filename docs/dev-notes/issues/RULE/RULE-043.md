---
id: RULE-043
title: Add optional Bowl Bound coffin-corner punts
status: open
priority: Medium
milestone: '35'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- planned
- advanced-option
- special-teams
links: [RULE-032, AI-030]
commits: []
---

## Description

The owner requested coffin-corner punt support as the next gameplay follow-up
and confirmed Milestone 35 because Milestone 34 already covers the independent
chart generator. Implement only this selected option from the previously
deferred Advanced III/IV package. Current games must not gain a partially
implemented option.

## Resolution / verification

- Verify and document the exact Bowl Bound rule, legal declarations, adjustment
  bounds, special-result precedence, and return/touchback behavior before coding;
  Paydirt is design input only. Keep the option explicitly enabled and preserve
  ordinary punts when disabled.
- Write synthetic tests first covering both possession sides, field boundaries,
  legal/illegal adjustments, return suppression and applicable chart specials,
  recovery, penalties, timing, scoring, statistics and trace completeness.
- The engine offers and resolves all legal actions. API, browser and CLI display
  engine facts, including equivalent public coaching guidance; add no UI rules.
- Preserve declared punt choice and actual consulted rolls through pending
  decisions, save/load and deterministic replay; never invent a return roll.
- Integrate AI-030 without weakening the approved public-information coaching
  policy. Run focused and full regressions and record play-test confirmation.

## Comments

--- 2026-11-02 ---
Created from the owner's explicit Milestone 35 request. Planning only; no engine
behavior, release scope or previously completed milestone acceptance changes.
