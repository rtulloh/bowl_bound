---
id: DATA-001
title: College PBP does not directly identify Bowl Bound tactical chart cells
status: resolved
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: '2026-11-02'
closed-at: null
tags:
- tested
links: []
commits:
- 61dec6c
---

## Description

Public college play-by-play lacks reliable designed-call, defensive-formation and detailed direction/depth observations for every event. A complete chart generator must expose inferred and sparse categories, preserve unknowns and avoid treating tactical estimates as measured evidence.

## Resolution / verification

- Add synthetic classification ambiguity, completeness and missing-yardage tests
- Record source coverage, confidence and fallback evidence in generation manifests

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 20:51 ---
Classification ambiguity, sparse pooling, unknowns and centered optional tactical priors are covered by synthetic tests and manifests. This resolves tooling visibility, not the absence of historical tactical observations.
Focused cumulative gate at 9565398: 121 passed. Owner play-test confirmation remains unrecorded, so this ticket is not closed.
