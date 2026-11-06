---
id: RULE-045
title: Verify selected Bowl Bound turnover semantics against transferred raw-token hypothesis
status: resolved
priority: High
milestone: '34a'
created-at: 2026-11-05
resolved-at: 2026-11-05
closed-at: null
tags: [chart-audit, cross-project, regression]
links: []
commits:
- 5b25c82e92f26a541b7cdb69e7e9ba70f50e9903
---

## Description

A separate Paydirt audit reported that searching raw INT input tokens could replace
its selected fumble outcome. This is a hypothesis to check in Bowl Bound, not a
claim that both games have the same rule or defect. Consulted local Paydirt
`docs/dev-notes/college-chart-tactics-cross-project-findings.md` and the local
cross-project audit exchange. Adapt selected-result/terminal-conformance controls;
do not copy NFL denominators or Paydirt's priority winner.

## Resolution / verification

Bowl Bound's approved Priority matrix legitimately selects INT for ordinary
F2/INT5 conflicts in both input orders. Synthetic controls assert that selected
normalized operation/kind reaches the proper pending interception choice and
terminal incomplete statistics when declined. Separate Option-to-pass and
INT-versus-defensive-QR-to-QT branches discard a raw INT and select a later fumble.
Retained/lost fumbles preserve the correct completion, rushing or sack credit,
without an interception choice or interception count. Eight real-session controls
pass unchanged production code. Initial fixture misuse of the presentation trace
was corrected; no gameplay failing baseline is claimed and no engine fix is made.

Independent full-game review now reconciles 19,856 eligible committed scrimmages
with pass-plus-rush box totals across 128 current-engine games. Previous-spot
voids, offsetting plays and conversions are excluded; accepted end-enforcement
results retain credit where the engine provides it. Scoring, clock, structured
traces and strict midpoint/final replay pass. No analogous production defect is
reproduced; keep open until the tested public commit is recorded.

## Comments

Tracked transferred hypothesis without changing approved Bowl Bound rules.

--- 2026-11-05 18:53 ---
Eight committed synthetic selected-semantic/terminal controls and independent 128-game eligibility, box/stat/clock/trace/replay acceptance pass unchanged production rules. Full 4,040-test source and native release gates pass at the same commit. This resolves the bounded verification task as non-reproduced; no Paydirt priority winner, raw-token classification or NFL denominator is copied. Await owner play-test closure.
