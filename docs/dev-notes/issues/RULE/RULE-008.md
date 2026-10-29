---
id: RULE-008
title: End-zone recovery return is a weaker duplicate of the ordinary return path
status: resolved
priority: Medium
milestone: "18a"
created-at: 2026-10-26
resolved-at: 2026-10-26
closed-at:
tags: [gameplay]
links: [DEV-022, RULE-011]
commits: [975ea48]
---

## Description

`bowl_bound/turnovers.resolve_end_zone_recovery_return:199-223` raises on PENALTY,
NO_CHANGE and FUMBLE return cells that `_return_from_spot` already handles, so
`session.py:955-959` disables the Return choice whenever any cell in the column is
non-numeric, which is likely for every real chart. It also starts the return at the goal line
rather than counting end-zone depth (Basic VI-13 D(ii)/F(i)).

## Resolution / verification

- Add failing synthetic tests for end-zone recovery returns with penalty, no-change and
  fumble return cells and with depth greater than zero.
- Route the end-zone return through `_return_from_spot` with an origin/landing parameter,
  as `special_teams._misc_return` does, and keep touchback available.
- Confirm the browser offers the engine-provided Return choice with the real reason text when
  it is disabled.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
Ordinary/end-zone returns share processing, preserve depth and origin, and handle penalties, no-change and fumbles.
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
