---
id: RULE-005
title: Ordinary DS/X/T1-T3 variable yardage results replay the down instead of resolving
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

`bowl_bound/session.py:65-72` lists VARIABLE_DS/X/T1/T2/T3 in `_UNSUPPORTED_KINDS`; an
ordinary scrimmage play that lands on one of them returns `supported=False`, leaves the state
unchanged, charges no clock, and the next snap replays the same down. docs/web-demo.md:70
documents the limitation, but docs/rules-profile.md:23 names the full-feature variable yardage
method as the selected policy and no project-plan milestone owns it. Real charts contain these
tokens, so complete games with historical teams currently include free do-overs.

The supplemental distance roll is already implemented three times:
`penalty_yardage._variable_pi_yards`, `turnovers.resolve_turnover_location` and
`special_teams._distance`.

## Resolution / verification

- Extract one tested variable-distance helper (reference, multiplier, dice) and reuse it from
  penalties, turnovers and special teams, enumerating the supplemental faces in tests.
- Resolve ordinary variable yardage through that helper in play resolution, recording the
  supplemental roll in the trace per the rules-profile worked example; never substitute zero.
- Remove the "not yet supported" path for these kinds or make it an explicit error, update
  docs/web-demo.md, docs/priority-chart.md and the rules profile, and add full-game
  regressions with synthetic charts containing DS/X/T cells.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
All 216 physical offensive combinations for every reference; full synthetic regulation reconciles clock/statistics and saved continuation.
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
