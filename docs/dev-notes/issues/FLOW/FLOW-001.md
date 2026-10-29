---
id: FLOW-001
title: A score is displayed as Final without explaining the pending try or demo boundary
status: closed
priority: Medium
milestone: "14"
created-at: 2026-10-26
resolved-at: 2026-10-26
closed-at: 2026-10-26
tags: [reproduced]
links: []
commits: [2fcb237]
---

## Description

The Milestone 13 synthetic touchdown path displayed Final and offered no explanation that scoring ended the demo. Milestone 14 introduces a required conversion choice, so a missing field state must not imply a final game.

## Resolution / verification

Implemented in 2fcb237: display authoritative engine status through touchdown, conversion choice, two-point setup, PAT result, and the current demo-complete boundary. Null field state no longer implies Final. Component regression and post-commit real-engine Chrome play-tests passed; see timestamped verification below.

## Comments

--- 2026-10-26 13:15 ---
Recorded from the focused synthetic usability review and user feedback. Milestone assignment is planned scope, not a completed fix.

--- 2026-10-26 13:45 ---
Milestone 14 implementation now displays engine phase/status through touchdown,
PAT and two-point setup/completion, plus the scoring ledger. Component regression
first failed on premature Final; both conversion paths passed real-engine Chrome
checks. Still open until the tested implementation is committed.

--- 2026-10-26 13:50 ---
Resolved in 2fcb237 with the component regression and real-engine browser coverage.
Changed expectation: a null field state no longer implies Final; the engine
provides conversion-choice and demo-complete status.

--- 2026-10-26 13:51 ---
Play-test confirmation: after commit 2fcb237, reran the production-build Chrome
suite against the real synthetic-team API/engine. All seven tests passed, including
touchdown → PAT and touchdown → two-point setup/snap. Both paths showed the engine
status rather than premature Final, reconciled the ledger to seven/eight points,
and disabled play after the explicitly explained demo boundary. Closed FLOW-001.
The separate manual-test game was not restarted or used for this audit.
