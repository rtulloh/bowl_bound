---
id: RULE-041
title: Resolve fumble recovery before offering a penalty choice
status: resolved
priority: High
milestone: '33'
created-at: 2026-11-02
resolved-at: 2026-11-02
closed-at: null
tags:
- reproduced
- gameplay
- penalties
links: []
commits: [4b647969f1438aba8cdce5cdaf6e29e029c619f0]
---

## Description

When a prepared play has both a selectable penalty and a fumble result, the engine offers accept/decline before resolving fumble recovery. The decline label says recovery remains unresolved, so the offended team must gamble instead of comparing the completed play result against enforcement. Bowl Bound penalty choices must be made after the fumble outcome is determined.

## Resolution / verification

- Synthetic in-field fumble-plus-penalty regressions resolve recovery ownership, spot, scoring, and any required turnover consequence before rendering accept/decline choices.
- Penalty choices compare known engine-owned outcomes; no decline label leaves fumble recovery unresolved.
- Recovery dice are consumed exactly once, remain save/replay deterministic, and accepted enforcement does not apply a discarded fumble result.
- Interception, end-zone recovery, penalty, timing, statistics, and structured-trace behavior remain correct for both possessions.

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 00:00 ---
Reassigned from Milestone 23 to the owner-prioritized Milestone 33 playability
follow-up scope because a penalty choice must compare complete football outcomes,
including recovery, rather than force a gamble.

--- 2026-11-02 21:00 ---
Added synthetic test-first regressions: 22 expected failures showed missing
recovery traces, unresolved decline projections and unconsumed recovery dice.
The engine now completes fumble recovery and required end-zone/return-foul
choices before offering the original penalty. Decline applies the prepared
result exactly once; acceptance discards it. Both pending and final traces retain
the consulted dice; state, scoring, statistics, clock and log commit only after
the original choice.

Replay profile advances to `bowl-bound-m33-v1`. Three synthetic legacy-save cases
first reproduced the compatibility problem. Validated historical prefixes retain
the old ordering; new commands use the corrected ordering. An old save paused
before recovery offers only `fumble:resolve` before accept/decline, without drawing
dice during load/resave. Prefix and final-digest validation remain strict.

Validation: 47 focused cases pass, including both possessions, fourth downs,
touchdowns/safeties, nested return fouls, prepared return-yardage credit, timing,
statistics, exact dice, save/replay, API and CLI. The cumulative engine/save/API/CLI/
coaching/metadata run passed 450 cases; four subsequent integration/credit cases
pass in the focused suite. AI-010's clean-baseline mutation audit detects 17/17
faults. Ruff lint/format pass with no skips or warnings. Details and exact commands:
[milestone evidence](../../milestone-33.md#rule-041--recovery-before-penalty-comparison).
Only obsolete unresolved-fumble wording and current-profile identifiers change
existing expectations; no assertion weakened. Keep open until tested commit is
recorded; owner play-test confirmation and full milestone gate remain pending.

--- 2026-11-02 21:04 ---
Resolved by tested commit `4b647969f1438aba8cdce5cdaf6e29e029c619f0`.
Focused suite: 47 passed; cumulative run: 450 passed; coaching mutation audit:
17/17 faults detected; tracker: 18 passed; Ruff lint/format passed. The exact
commands and scope are recorded above and in the milestone notes. No owner
play-test confirmation is claimed; ticket remains resolved awaiting that audit.
The full milestone gate remains pending.


--- 2026-11-02 20:48 ---
The first full regression found an existing engine-hardening test explicitly
expecting the obsolete decline-before-end-zone-recovery order. A focused unchanged
run failed on that now-illegal decline. Updated only its command chronology to
resolve the actual end-zone recovery, verify original possession/log remain
uncommitted, then decline the original penalty. Preserved its final touchback,
exact four-entry trace and single-log assertions. The new name states the corrected
contract. This is the intended RULE-041 behavior; no production fix or assertion
removal. The full gate reruns after this test expectation update.

Focused verification after the chronology update: `.venv/bin/python -m pytest tests/test_engine_hardening.py tests/test_fumble_penalty_order.py -q`: **109 passed in 3.36s**. Ruff check/format and diff checks passed.
