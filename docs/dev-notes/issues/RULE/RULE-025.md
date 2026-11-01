---
id: RULE-025
title: Add onside kick choice and resolution
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- advanced-option
links: [RULE-018]
commits: [9fb974a]
---

## Description

Onside kicks are currently unsupported. Basic VI-8 specifies the 12-yard kick and recovery rule. Offer it as a kick type to the already assigned kicker; never reintroduce a kick-or-receive choice at halftime. RULE-018 records the reciprocal team assignment.

## Resolution / verification

- Implemented in `9fb974a` from Basic VI-8 (printed p. 10): one offensive roll; a 12-yard dead-ball kick; kicker recovers on totals 13–20 inclusive, otherwise the receiver recovers. No return roll, points, or offensive statistics are added. Current unreturned-kick timing remains zero.
- The action is offered only to the already assigned kicker. It is available on ordinary opening, post-score, and second-half kickoffs, but not safety free kicks. No halftime kick/receive election was restored.
- The baseline computer chooses the normal kickoff by default; human/terminal/browser and API paths accept the offered onside action. Synthetic tests cover all 216 physical offensive-dice combinations, threshold edges, both recovery teams and field positions, trace, timing, statistics, safety-free-kick rejection, reciprocal halftime assignment, and save replay.
- Test-first evidence: new synthetic cases initially failed on the missing action and missing API enum; a direct safety-free-kick constructor case failed before the guard was added.
- Validation at `9fb974a`: 162 focused Python tests passed (including API, regulation, CLI, special teams, and issue-tracker tests); Ruff checks and formatting passed; 121 frontend tests passed; production build passed; all 33 real-engine browser tests passed on synthetic teams. The browser run emitted the existing `NO_COLOR`/`FORCE_COLOR` warning and had no skipped tests.
- Await owner play-test confirmation before closure.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Implemented and automatically verified in `9fb974a`. Awaiting owner play-test
confirmation; automated tests do not close the gameplay ticket.
