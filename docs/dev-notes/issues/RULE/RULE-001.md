---
id: RULE-001
title: Audit inherited turnover-return limitations before complete regulation play
status: resolved
priority: High
milestone: "15"
created-at: 2026-10-26
resolved-at: 2026-10-26
closed-at:
tags: [reproduced, synthetic-regression]
links: []
commits: [402f7d142c2cdc6920648250e5dbe29b548dc240]
---

## Description

Milestone 14 reuses the Milestone 12 turnover resolver for two-point tries. Review
identified inherited boundaries: consecutive return penalties raise an explicit
error, a penalty followed by a literal touchdown has no numeric return endpoint,
return-fumble recursion does not propagate its full policy context, and pending
return decisions may concatenate previously displayed trace entries twice.
Blank return results also require an explicit policy rather than an invented
zero-yard advance. These are code-read findings, not a claim that each was
reproduced during the current browser play-test.

## Resolution / verification

Synthetic regressions in `tests/test_return_audit.py` reproduced all five original
boundaries and additional cancelled-fumble and nested-recovery problems. Same-side
return fouls now offer separate alternatives; literal TD retains its endpoint;
recursion/hurry/recovery-team context propagates; pending traces contain each
observed roll once. Normalized NO_CHANGE explicitly means no advance. Accepting
a foul before a fumble does not roll cancelled recovery dice or leak points.
Conversion coverage proves acceptance does not award a defensive six or add a try.

Unsupported end-zone recovery-return columns are disabled before rolling, with
touchback available. Unrepresentable end-zone return-foul acceptance is disabled
with a reason, leaving decline legal. See `docs/dev-notes/milestone-15.md`.

Implemented and tested in `402f7d142c2cdc6920648250e5dbe29b548dc240`.
Rare branches still await manual play-test confirmation before closure.

## Comments

--- 2026-10-26 13:40 ---
Recorded inherited Milestone 12 limitations during Milestone 14 acceptance review.
Assigned to Milestone 15 hardening before full regulation play; ordinary PAT,
scoring, and conversion-return acceptance do not establish these rare branches.


--- 2026-10-26 14:00 ---
All original audit boundaries reproduced and covered by synthetic regressions,
including two-point conversion acceptance and nested end-zone recovery identity.
Full gate: 1,326 Python tests, 91.61% branch-aware coverage; nine browser tests,
including complete regulation. No manual confirmation of these rare branches yet.
