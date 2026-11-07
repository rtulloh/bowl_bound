---
id: DATA-045
title: Establish all-team chart confidence gates and community play-testing
status: open
priority: High
milestone: 34a
created-at: 2026-11-05
resolved-at: null
closed-at: null
tags: [chart-generator, validation, planning]
links: [DATA-060]
commits: []
---

## Description

The owner cannot manually validate every generated team. Structural and complete-game checks support experimental testing but do not establish all-team historical accuracy. Automated validation and independent review must work without community participation; volunteer feedback is supplementary.

This public release summary retains the canonical issue ID. Detailed source records, reference comparisons and game evidence remain private.

## Resolution / verification

- Bind source, model, chart, engine, coaching and measurement identities to every assessment.
- Preserve known/unknown distinctions and correct probability/exposure denominators.
- Audit scoring, state, clock, statistics, traces, replay and legal AI decisions.
- Distinguish descriptive simulation results from independent historical evidence.
- Require separate per-team/source-fit assessment before stronger accuracy claims.
- Record committed validation and play-test confirmation before resolving or closing.

## Comments

--- 2026-11-07 13:40 ---

Owner explicitly accepts a bounded experimental alpha using the existing 116 generated 2007 teams and two samples. Required release checks cover complete legal bundles, identity/probability accounting, current-engine mechanics, regression tests and packaging. Exact historical formations, reference-chart replication, optional defensive B placement and disclosed source micro-reconciliation are follow-up work rather than prerequisites. This scope does not relabel failed accuracy assessments as passes or close this issue.

The Alpha 9 preparation passes 4,040 runtime tests with 93.41% branch-inclusive coverage, 158 frontend tests/build/audit, and 64 real-engine browser cases. The integrated versioned audit and applicable package/codec/presentation suite pass 351 tests. Frozen-candidate and bounded game acceptance remain pending; see [release acceptance](../../release-alpha9.md).
