---
id: FLOW-004
title: Generate truthful roster narration for kicks and turnovers
status: resolved
priority: Medium
milestone: 21a
created-at: 2026-10-28
resolved-at: 2026-10-28
closed-at: null
tags:
- tested
- awaiting-playtest
links: [CLI-036, DEV-030, DEV-031, FLOW-003]
commits: ["3b8b8e4","4457887"]
---

## Execution order

Depends on: DEV-030, FLOW-003.
See [Milestone 21a plan](../../milestone-21a.md) for the full dependency order.

## Description

Extend engine narration to currently supported special-team and turnover outcomes only. Attribute participants to the correct team at each stage without treating the final possessor as every actor. Do not add advanced football behavior.

## Resolution / verification

- Write synthetic red-first cases for kickoffs, punts, field goals, kick conversions, returns, fair catches and touchbacks where supported; do not invent a return on a fair catch or touchback.
- Cover interceptions, offensive/defensive fumble recovery, returner-own-fumble recovery, return touchdowns and chained possession changes using structured facts and correct team attribution.
- Pending interception/return/recovery decisions must not narrate uncommitted future choices or hidden calls; missing actor evidence uses generic wording.
- Preserve timing, score, field position, recovery/new-series labels, statistics and complete physical-dice traces; unsupported advanced kicks remain unavailable.

## Comments

--- 2026-10-28 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-28 red-first and implementation ---
Paydirt commentary.py:396–417 consulted for recovery/team separation, not random
defenders or invented participants. Pre-test review caught a kickoff fixture
that was pending, not an automatic touchback; corrected physical distance and
added explicit committed-outcome assertions before the red run. Red result:
16 expected missing-label/fallback failures, 4 existing safeguards passed.
Implemented stage/outcome-whitelisted kicker/punter/returner labels; generic
pending/penalty/fumble/blocked-chain fallbacks. No prose or chart-cell parsing.
Implementation review requested before green tests.

Pre-green review identified three gaps before commit: aborted-kick safeties
without recovery traces, end-zone interception return stage naming, and repeated
return-chart consultations after no-foul rerolls. Added reviewed synthetic/real
regressions; unchanged implementation produced exactly 6 additional failures
(22 passed). Fixes use stage/outcome evidence, never chart-token interpretation.
Recovery chains still remain generic; repeated consultations without a recovery
are one returner, not evidence of a second possession change.

Corrections reviewed before green tests; final coverage review strengthened real
fumble fixtures with RB names and explicit recovery outcomes/possession. Focused
commentary/special/session-turnover/new-series/hurry gate: 110 passed in 1.34s.
Formatter suite: 56 passed, 95.12% branch-aware coverage (95% floor). Ruff passed.
All six review regressions now pass; no existing expectation weakened.
