---
id: RULE-007
title: Offended team cannot decline a penalty when the prepared reroll is a turnover
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

`bowl_bound/session._decline_blocker:1389-1392` disables decline for any pending prepared
result, which includes interception and fumble results. After an offensive foul whose reroll is
an interception, the defense sees accept enabled and decline blocked with "the prepared result
is pending", so it can never take the interception. docs/penalties.md:38 still says the rules
for these cases "arrive in Milestone 12", which has shipped.

## Resolution / verification

- Add failing synthetic tests for declines whose prepared result is an interception, a fumble
  and an end-zone recovery; the decline must continue into the real pending turnover procedure
  with the already-rolled dice and no duplicate rolls.
- Allow decline for pending turnover results by chaining into the existing pending decision
  flow; keep the reason text for genuinely unsupported results.
- Refresh docs/penalties.md to describe the implemented decision rules.

## Comments

--- 2026-10-26 16:40 ---
Opened from the Milestone 18 full code review (engine, web, importer/tooling and
test-suite passes). Evidence uses synthetic charts only. Milestone assignment is
planned scope for review; re-scope with a timestamped reason if the roadmap changes.

--- 2026-10-26 17:02 ---
Owner approved moving this ticket from Milestone 19 into dedicated Milestone 18a.
Implementation and synthetic regression evidence: [18a acceptance](../../milestone-18a.md).
Decline continues already-prepared interception, fumble and end-zone recovery; exact traces and one committed play.
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
