---
id: RULE-002
title: Interception end-zone spots award the wrong score in both end zones
status: resolved
priority: High
milestone: "18a"
created-at: 2026-10-26
resolved-at: 2026-10-26
closed-at:
tags: [gameplay, reproduced]
links: []
commits: [975ea48]
---

## Description

`bowl_bound/turnovers.py:111-116` computes `interception_spot = yards_to_goal - location`
and then treats `spot <= 0` (the interceptor's own end zone) as a defensive touchdown and
`spot >= 100` (the offense's end zone) as a safety. The rulebook (Basic VI-13 E/F) gives the
interceptor a touchback-or-return choice in its own end zone and a defensive touchdown when
the ball is intercepted in the offense's end zone; a safety applies only on or behind the end line.

Synthetic reproduction with `special_chart` teams and `ScriptedDice`:
offense 10 yards from goal, `INT 15`, choice `return` -> `DEFENSIVE_TOUCHDOWN (0, 6)`;
offense at its own 3, `INT -5`, choice `return` -> `SAFETY`.

## Resolution / verification

- Add failing synthetic regressions for interceptions caught in each end zone and on or
  behind each end line, including the touchback/return choice and the defensive touchdown.
- Mirror `special_teams._recovery`, which already distinguishes the goal line (100) from the
  end line (110) and offers `_end_zone_choice`; consider renaming `END_LINE` because it
  currently denotes the goal line.
- Update docs/turnovers.md so end-zone wording matches the implemented rule, and rerun
  turnover, session-turnover, statistics and full-game regressions.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
Both possessions, goal/end-line boundaries, interception depth and saved pending end-zone continuation.
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
