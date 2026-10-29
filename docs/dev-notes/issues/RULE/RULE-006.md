---
id: RULE-006
title: Accepting a return foul on an offensive fumble recovery resets to first and ten
status: resolved
priority: Medium
milestone: "18a"
created-at: 2026-10-26
resolved-at: 2026-10-26
closed-at:
tags: [gameplay, reproduced]
links: []
commits: [975ea48]
---

## Description

`bowl_bound/session.py:730-755` applies `enforce_return_penalty`, which always produces a
first down, then hard-codes `outcome=TurnoverOutcome.DEFENSIVE_RECOVERY`. When the fumbling
team recovered its own fumble and the opponent accepts the return foul, the original down and
distance should continue and the outcome label should remain an offensive recovery.

Synthetic reproduction: home third and eight, fumble recovered by the fumbler with a return
roll, own foul accepted by the away team -> `defensive_recovery`, home first and ten.

## Resolution / verification

- Add failing synthetic tests for accepted and declined return fouls on offensive recoveries
  that continue the original play, checking down, distance, outcome label and statistics.
- Preserve `continues_original_play` through penalty enforcement and derive the outcome from
  the actual recovering team.
- Check the browser log/result wording comes from the corrected engine labels.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
Accepted and declined own-recovery return fouls preserve down, original line to gain and statistics, including recovery past the marker. Saved pending foul resumes identically.
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
