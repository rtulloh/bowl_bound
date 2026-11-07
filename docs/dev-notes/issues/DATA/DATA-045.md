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
links: [DATA-037, DATA-046, DATA-048, DATA-049, DATA-053, DATA-055, DATA-060, DATA-063, DATA-064]
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
- Require separate per-team/source-fit assessment before stronger accuracy claims, reconciling official totals, definitions, eligible PBP coverage and missing values.
- Census every result family across offense, defense, supplemental and special teams: exact tokens, normalized mechanisms, rendered colors, runs/blocks, matching rows and cross-team templates. Check B, QT/QR, INC/BLACK, INT, penalties and numeric outcomes; retain supported repetition and exact physical weights rather than moving a problem cosmetically.
- Validate the frozen method on additional teams/seasons without developer references and explain strengths/weaknesses under baseline and Hard policies; benchmarks inform validation without becoming generation inputs.
- Record committed validation and play-test confirmation before resolving or closing.

## Comments

--- 2026-11-07 13:40 ---

Owner explicitly accepts a bounded experimental alpha using the existing 116 generated 2007 teams and two samples. Required release checks cover complete legal bundles, identity/probability accounting, current-engine mechanics, regression tests and packaging. Exact historical formations, reference-chart replication, optional defensive B placement and disclosed source micro-reconciliation are follow-up work rather than prerequisites. This scope does not relabel failed accuracy assessments as passes or close this issue.

The Alpha 9 preparation passes 4,040 runtime tests with 93.41% branch-inclusive coverage, 158 frontend tests/build/audit, and 64 real-engine browser cases. The integrated versioned audit and applicable package/codec/presentation suite pass 351 tests. Frozen-candidate and bounded game acceptance remain pending; see [release acceptance](../../release-alpha9.md).

--- 2026-11-07 — bounded Alpha 9 game acceptance ---

The frozen candidate at `41bbc40c21634a3c906b5bfd50487567db893200` passes 34 complete core/state/score/stat/clock/trace and strict replay checks, including two exact repeats. The bounded observer accepts 32 receipts; two fumbled-kickoff-return recovery cases remain explicitly UNVERIFIED. Their legitimate third recovery die follows two chart lookups, while the routine observer checks a two-draw exposure before excluding this unsupported branch. One meaningful synthetic failing reproduction and two numeric controls retain the observer limitation; four existing engine recovery controls pass. This is a development-observer coverage issue, with no reproduced gameplay defect and no assertion weakened for release. Keep the rare-component audit follow-up open.

Frozen panel manifest SHA-256 `8a192c8351ae8c20c42c4e54c4ddc77760f33bed600c76f64c72bdf442baa946` binds all 64 artifacts. Seven legal two-point fallbacks remain tracked by AI-034. One disk-full write is preserved separately from the 34 completed runs. See [release acceptance](../../release-alpha9.md) for exact boundaries, identities and the experimental publication disposition. No historical/full-season accuracy certification or ticket closure follows from these mechanical checks.
