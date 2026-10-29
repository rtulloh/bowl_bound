---
id: RULE-004
title: Defensive end-zone fumble depth and variable defensive turnover locations are ignored
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

`bowl_bound/resolution.py:271-272` sets `defensive_end_zone_depth=1` with `yards=None` for
the F_ENDZONE operation, but no module reads `PriorityResult.defensive_end_zone_depth`.
`session._resolved_turnover_location:1418-1435` then falls back to the offensive F cell's own
yardage, so an offensive `F+3` against a defensive touchdown cell resolves as an ordinary
recovery near the line of scrimmage instead of a fumble one yard inside the defenders' end zone.

The same helper only matches source cells whose `kind is result.kind`, so INT_MIN, F_MIN and
F_DEF against a decorated variable defensive cell such as `(-X)` never roll the defensive
location and silently use the offensive number without a `turnover_location` trace.

## Resolution / verification

- Add failing synthetic regressions for F_ENDZONE against TD cells at several field positions,
  and for INT_MIN/F_MIN/F_DEF where the defensive cell is a decorated variable distance.
- Use `yards_to_goal + depth` for the end-zone fumble spot and roll decorated defensive
  variable cells through the same variable-distance helper as offensive cells; if a case stays
  unsupported, raise or mark it pending explicitly rather than choosing the offensive number.
- Remove the dead field if it is replaced; keep the structured trace complete.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
Independent INT_MIN/F_MIN/F_DEF distances, no unused operand rolls, F_ENDZONE depth consumed by the session.
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
