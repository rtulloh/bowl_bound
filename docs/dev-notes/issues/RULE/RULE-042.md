---
id: RULE-042
title: Offer a timeout as a pre-play modifier after kickoff
status: open
priority: Medium
milestone: '33'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- rules-profile
- timing
- usability
links: []
commits: []
---

## Description

After a kickoff, the receiving-side human defender is offered formations but no timeout. The approved interaction is the Paydirt-style pre-play modifier: the player selects their timeout, then selects the defensive formation; Bowl Bound resolves that play and charges the selected timeout as the play's timing modifier. Current timing logic exposes timeouts only after a completed play, making the first scrimmage snap an unintended exception.

## Resolution / verification

- The engine offers each eligible side's own timeout as an explicit armed pre-play modifier, including immediately after kickoff; the frontend never invents availability.
- Selecting a timeout does not advance the clock or resolve a play. The next legal play charges that side's timeout, uses the 10-second timing rule, records the result clearly, and clears the armed modifier.
- Preserve ordinary post-play clock decisions and prevent stale armed modifiers across a turnover, scoring play, save/load, invalid action, or new game.
- Add synthetic engine, API, CLI, coached-browser, and save/load regressions; verify the production frontend build.

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 13:45 ---
Owner approved the pre-play-modifier behavior. Consulted local Paydirt
`paydirt-web/backend/routes.py` (`call_defensive_timeout`, request
`call_defensive_timeout`, and the post-play timeout flag): it records a player
timeout choice before resolving the play, then applies the short timing after
that play. Bowl Bound will adapt the interaction only, retaining its own
engine-owned legal actions and timing rules; it will not reuse Paydirt code or
introduce a runtime dependency.

--- 2026-11-02 00:00 ---
Reassigned from Milestone 23 to the owner-prioritized Milestone 33 playability
follow-up scope. The first scrimmage play after a kickoff must not omit an
otherwise legal defensive timeout.
