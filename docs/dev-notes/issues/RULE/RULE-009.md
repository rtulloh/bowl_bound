---
id: RULE-009
title: Offered field goal can raise, fourth-down spike allowed, and runoff can discard a requested snap
status: resolved
priority: Low
milestone: "18a"
created-at: 2026-10-26
resolved-at: 2026-10-26
closed-at:
tags: [gameplay]
links: []
commits: [975ea48]
---

## Description

Three small engine edge cases found in review:

- `bowl_bound/special_teams.py:364-366`: `field_goal` is always offered, but a miss from
  inside the offense's own 8 raises `ValueError("field goal hold is outside the field")`.
- `bowl_bound/regulation._can_adjust_offense:176-185` has no down check, so a spike is allowed
  on fourth down, contrary to the rules profile's "another down must be available".
- `bowl_bound/regulation.snap:358-360` returns the previous play's report when a runoff ends
  the period and silently discards the requested play.

## Resolution / verification

- Add failing synthetic regressions for each case.
- Either withhold the field-goal action or define the outcome; disable spike on fourth down
  through the engine's choice metadata; return a distinct period-boundary report or raise a
  specific exception so the API/UI never show a stale play as the response.
- Document the decided behavior in docs/rules-profile.md.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
Impossible field-goal holds withheld, spike absent on fourth down, and period runoff returns a no-new-play boundary response.
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
