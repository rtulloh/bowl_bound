---
id: RULE-003
title: Fumbles into the fumbler's own end zone ignore who recovered and own-return touchbacks
status: resolved
priority: High
milestone: "18a"
created-at: 2026-10-26
resolved-at: 2026-10-26
closed-at:
tags: [gameplay, reproduced]
links: [RULE-014]
commits: [975ea48]
---

## Description

`bowl_bound/turnovers.py:161-162` returns a safety whenever the fumble spot reaches the
fumbler's goal line, after the recovery roll was already consumed. Basic VI-13 D says a
defensive recovery there is a touchdown; the safety applies to an offensive recovery, and only
the end line (not the goal line) makes the spot itself a safety. `special_teams._recovery:553-562`
implements this correctly, so two modules disagree on the same rule.

Synthetic reproduction: offense at its own 3, fumble location -6, with recovery rolls 10
(fumbler retains) and 39 (opponent recovers) both produce `SAFETY`.

Related: `turnovers._apply_return_yards:390-399` converts any return that reaches the
returner's own goal line into a touchback at the 20 even when `continues_original_play`
is true (an offensive recovery returned backwards into its own end zone should be a safety).

## Resolution / verification

- Write failing synthetic tests for defensive and offensive recoveries at the goal line, in
  the end zone and behind the end line, plus the own-recovery backward return case.
- Route end-zone recovery through one shared rule shared with special teams rather than
  patching both modules separately; keep traces showing the recovery roll used.
- Align docs/turnovers.md (currently says "on or behind the fumbler's own end line") with the
  implemented distinction, and rerun the turnover, conversion and full-game suites.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
Recovery identity before the end line, no recovery beyond it, own-return safety and offensive touchdown classification.
Status remains open until the tested implementation commit is recorded.

--- 2026-10-26 17:05 ---
Resolved in tested commit `975ea48` (`milestone 18a: harden engine correctness`).
Full cumulative gate: 1,564 Python tests, 92.84% branch-aware coverage; Ruff checks,
49 frontend tests, production build and 14 real-engine Chrome tests passed.
The focused 190-test hardening/variable/save/return/statistics command passed again
on that commit. Exact commands and changed expectations are recorded in the
linked Milestone 18a acceptance note. No skipped tests or warnings were reported.
Await owner play-test confirmation before closing; the running backend was not
restarted, so this is not a claim that its existing game uses the corrected code.
