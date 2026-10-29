---
id: RULE-011
title: Returner recovering its own return fumble gets second down and offensive labels
status: resolved
priority: High
milestone: '21'
created-at: 2026-10-27
resolved-at: 2026-10-28
closed-at: null
tags:
- reproduced
links: [RULE-008]
commits: [effb7d9]
---

## Description

turnovers._resolve_return_cell passes the new-possession placeholder state into resolve_fumble, which treats the returner as the scrimmage offense: without return privilege apply_gain yields 2nd down for the team that just took possession with outcome OFFENSIVE_RECOVERY; with privilege the return continues through _apply_return_yards to 2nd down and a touchdown is labeled OFFENSIVE_TOUCHDOWN. Synthetic reproduction: interception at 20 with return cell F+3 and recovery total 10 produced away ball 2nd and 7 at 57. The same path serves end-zone recovery returns. docs/turnovers.md states a defensive recovery starts first-and-ten after any return. Related: an own recovery on fourth down that turns the ball over on downs is still labeled offensive_recovery.

## Resolution / verification

- Thread a new-series flag through resolve_fumble so returner recoveries start first-and-ten with DEFENSIVE_RECOVERY or DEFENSIVE_TOUCHDOWN; label turnover on downs correctly. Tests for in-field and end-zone origins on both possessions, recovery with and without return privilege, and the touchdown case. Save profile bumped; docs/turnovers.md verified.

## Comments

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-27 19:00 ---
Reassigned from 22 to 21 under the owner’s High-to-Low remediation request: this
engine correctness defect also changes Hard’s isolated sampled outcomes, so it
is a dependency of trustworthy milestone-21 acceptance, not a new advanced option.
Paydirt `game_engine.py:929–943` resets every return-chain result to first down;
its RULE-017 cross-check demonstrates why original-play recovery must instead
retain original scrimmage context. Adapt the context distinction, not NFL rules.
Added red-first synthetic tests for both possessions and in-field/end-zone
origins, with/without advancement, touchdown labels, observed rolls, session
integration and fourth-down recovery labels.

--- 2026-10-27 implementation validation ---
19 expected red-first failures; corrected new-series context and fourth-down
outcome labels, then added save/resume through the corrected recovery and next
snap. Focused turnover/engine/session/save/statistics/coaching/tracker run:
270 passed in 18.21s. Replay profile is bowl-bound-m21-v1; previous profile
rejected before team lookup. No private saves changed. Retain open status until
commit-referenced validation and play-test acceptance are recorded.

--- 2026-10-28 tested-commit verification ---
Dedicated fix commit(s) recorded in metadata; included in tested runtime source
41da5fd. Full `.venv/bin/python -m pytest --cov -q`: 2,133 passed in
385.03s, 93.42% branch-aware coverage, no reported skips/warnings. Focused
red-first/check evidence above remains applicable. Mark resolved, not closed:
owner play-test confirmation and milestone review remain outstanding. Final
browser retry/failure evidence is tracked separately under DEV-029.
