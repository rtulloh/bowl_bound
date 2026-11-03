---
id: RULE-044
title: Reconcile next-play timeout timing through a pending coached play
status: resolved
priority: High
milestone: '33'
created-at: 2026-11-03
resolved-at: 2026-11-03
closed-at: null
tags:
- owner-review
- timing
links: [RULE-042, UI-052]
commits: [04707ce113729830700308610a120d53d1dd3282, e3d6516fd7362940c7178dcea2276f1b1f75747c, b265de374e8ea1cb1e918ae8ac8bbffb83df7632]
---

## Description

Owner web play-test: selecting a team timeout and then a defensive formation appeared to charge 30 seconds while the timeout remained selected; the status also retained disallowed 'armed' wording. Reproduce with fictional charts and distinguish prior completed-play timing from an unresolved next play before changing timing behavior. This is a follow-up on the unmerged M33 review branch, preserving its historical acceptance.

## Resolution / verification

- Bind an eligible timeout request to the selected call, preserve it through required decisions, spend once for a normal play longer than 10 seconds, and clear it unused for natural 10-second/no-time outcomes. Verify ownership, clocks, budget and save/replay in engine/API controls.
- Match ordinary CLI AT timing/eligibility, explicitly document its existing human-pending limitation, and preserve legacy unconditional commands and saves.
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
reservation is mechanically equivalent (prior 30 + selected 10), retaining distinct
legacy audit method names. **435 cumulative Python cases**, **131 frontend
cases**, production build and focused Ruff pass.

Owner further clarified full AT intent: natural 10-second results must not spend
a timeout. Legacy web reservations do spend one on those outcomes, whereas CLI
AT only uses a subsequently offered timeout and cannot retain its request across
a human interception decision. A distinct prospective conditional command is
being implemented next; this ticket remains open. Do not change the meaning of
recorded legacy timeout actions or claim complete CLI parity prematurely.

--- 2026-11-03 15:40 ---
Owner explicitly requires AT-style conditional eligibility. Added a distinct
`timeout_after:<side>` prospective request; recorded `timeout:<side>` actions
retain original unconditional semantics. The web primary action displays the
engine's conditional offer, while old adapters/saves retain their original keys.
Natural 10-second results use no timeout; mandatory decisions preserve the
request for that same play, then clear it once without charging twice. This
extends persistence beyond CLI AT's current human-pending limitation rather
than pretending the existing terminal suffix already does that.

Test-first: 15 engine tests failed on absent command, six new API branches on
422, frontend on displaying the legacy control instead of the conditional offer.
An initial new API test had a missing parametrized function argument; corrected
that fixture before recording meaningful API failures. Focused current result:
44 passed in 7.43s; cumulative 568 in 73.23s. Frontend 131 in 4.80s/build 1.08s; Ruff
check/format 554 files pass. New real-engine browser controls include conditional
requests/side ownership and both human interception decisions on fictional
all-interception charts (explicit baseline-v2 avoids another RZDZ decision).
These browser assertions remain unverified locally because of sandbox launch
restrictions. Fresh full-source regression remains pending; ticket is open.

--- 2026-11-03 15:45 ---
Review kept the owner's approved pre-call button wording Use TEAM timeout on
next play; eligibility is in the engine status/help. Status changes from next
play to THIS play only after a call has a required continuation. A new red CLI
menu regression caught the new web-only key leaking into SPECIAL PLAYS; both
timeout prefixes are now excluded there, with historical T/AT bindings retained.
Two browser-fixture interception paths also pass directly through the real API
(TestClient), which is not a browser execution claim. Runtime isolation test,
18 tracker checks, pip check and npm audit (zero vulnerabilities) pass. An
initial runtime-stage command used a nonexistent test filename; rerun the actual
release-package isolated-runtime test successfully. No check was skipped.

Final-source full gate initially exposed two stale exact CLI/API drive-log
expectations missing additive `timing_label: null`. Both failed meaningfully,
then both passed in 0.67s with only that documented field added; all strict
football/save/future comparisons remain. The early full run was interrupted
at 511 passed/2 failed in 278.38s and is not acceptance evidence. Executable source
remains e3d6516; a fresh complete gate follows this test-contract correction.

--- 2026-11-03 15:55 ---
Parent verified frozen e3d6516 on a separate port: eligible same-play timeout
spends one budget/10 seconds and appears in history; health/frontend/assets pass.
An independently generated fictional golden save from actual frozen `97d9314`
loads/re-saves, preserving its legacy prior 30 + selected 10 charge and one timeout.
An authorized private CLI save also loads without changing its saved public
score/clock; no raw save, team details or play logs are copied here.

Play-test confirmation (partial): owner reports the offensive control on frozen
e3d6516 used exactly 10 seconds after selecting a timeout and play 1. Defensive
confirmation is still pending; this does not close the ticket.

Browser self-review now handles a possible human-owned RZDZ result choice in
the existing normal-tier timeout scenarios: wait for actual engine responses,
assert unchanged clock/budget/intent during continuations, complete enabled
human choices, then assert one final charge. It does not replace normal-tier
coverage with a simpler policy or make invented decisions on the frontend.
The fresh Python gate has passed the earlier stale-expectation point; no full
pass or automated browser execution is claimed yet.

--- 2026-11-03 — final engineering verification ---
Resolved against executable e3d6516 (presentation 04707ce), with b265de3's
explicit nullable API-contract correction. Subsequent 899cd8c changes only
browser tests/docs. No new runtime change is hidden behind a prior green gate.

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **3,499
  passed in 873.91s, 93.17% branch-aware coverage**, exit 0, no skips/warnings.
- Relevant cumulative timeout/CLI/coaching/saves/API/fumble/fourth-down/current
  RZDZ/version contracts: **568 passed in 73.23s**. Final focused timeout, CLI and
  tracker command: **122 passed in 13.30s**, including the review's red CLI menu
  control. The two corrected exact CLI/API drive cases pass in 0.67s.
- Pinned frontend: **131 tests**, production build, npm audit **zero
  vulnerabilities**. Ruff check/format **554 files**, pip check, isolated real
  runtime/default-game staging, link and diff checks pass. Runtime paths are
  already manifest-selected; no module or private material was added to packaging.
- **40** real-engine browser cases collect; both new fictional INT fixtures pass
  through TestClient. Automated browser execution remains unverified under the
  documented local Chromium sandbox restriction. No fresh hosted pass is claimed.
- Independent frozen e3d6516 HTTP/frontend/history checks and actual 97d fictional
  golden-save load/re-save preserve legacy behavior. Original live games/servers
  were left intact. No branch push, merge, release or tag was performed.

Owner confirmed offense on the immutable candidate. **Defensive owner play-test
confirmation remains pending**, so the ticket is resolved rather than closed.
Original M33 acceptance remains historical; subsequent button-count wording and
play-history work are separate owner requests.
