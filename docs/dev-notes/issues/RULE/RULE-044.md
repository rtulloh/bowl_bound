---
id: RULE-044
title: Reconcile next-play timeout timing through a pending coached play
status: open
priority: High
milestone: '33'
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags:
- investigating
links: [RULE-042, UI-052]
commits: []
---

## Description

Owner web play-test: selecting a team timeout and then a defensive formation appeared to charge 30 seconds while the timeout remained selected; the status also retained disallowed 'armed' wording. Reproduce with fictional charts and distinguish prior completed-play timing from an unresolved next play before changing timing behavior. This is a follow-up on the unmerged M33 review branch, preserving its historical acceptance.

## Resolution / verification

- Verify timeout click, defense call, CPU-owned continuation, final 10-second charge, correct team budget and cleared selection through API and engine.
- Verify critical late-quarter timing and visible engine-provided labels/status without armed wording.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-03 15:35 ---
The later screenshot/owner confirmation shows a human interception choice on the
selected next play. Prior completed-play timing was charged when that call
started; choosing either interception continuation then charged that same play
10 seconds. No lost timeout or extra-play delay was reproduced. Original
reported 30 seconds was later clarified as a 20-second prior charge; private
team/dice details are not copied here. The status misleadingly said next legal
play while THIS play was pending, and the completed timeout had no log label.

Consulted local Paydirt `paydirt/game_engine.py:3105` and
`tests/test_timeout_clock_interactions.py` (pending and period-boundary checks),
and verified Bowl Bound `cli.py` standalone T vs `_call_with_timeout` AT. Adapt
explicit ownership/boundary tests only: no NFL two-minute warning, fractional
minutes, random runoff or Paydirt runtime code.

Presentation checkpoint: six meaningful red API regressions reached the expected
correct timeout count/10-second charge, then failed on remaining armed wording.
A frontend regression failed on missing engine prior-timing explanation. Tests
now cover both interception choices at Q1/Q2/Q4, no extra charge on refresh,
save/replay and four 11-second period-boundary controls. Normal CLI AT vs web
reservation is mechanically equivalent (prior30 + selected10), retaining distinct
legacy audit method names. **435 cumulative Python cases**, **131 frontend
cases**, production build and focused Ruff pass.

Owner further clarified full AT intent: natural 10-second results must not spend
a timeout. Legacy web reservations do spend one on those outcomes, whereas CLI
AT only uses a subsequently offered timeout and cannot retain its request across
a human interception decision. A distinct prospective conditional command is
being implemented next; this ticket remains open. Do not change the meaning of
recorded legacy timeout actions or claim complete CLI parity prematurely.
