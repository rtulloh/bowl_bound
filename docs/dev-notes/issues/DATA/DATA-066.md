---
id: DATA-066
title: Regenerate the 2002 generated cohort with the budget-aware model before release
status: open
priority: High
milestone: 34a
created-at: 2026-11-16
resolved-at: null
closed-at: null
tags:
- chart-generator
- release-blocker
links: []
commits: []
---

## Description

The 52 generated 2002 teams produced by the older college-chartgen-v1 pipeline are not release-quality and cannot be added to 1.1.0 as-is. They were generated from ESPN public core API play-by-play (normalized checksum 5162d0cc87b3..., 81,380 rows, 440 games) and load cleanly, but their defensive charts are sparse and fail the release audit gate. Only generated charts are in scope; the two PDF-imported 2002 teams (Ohio State, Miami FL) stay private and excluded.

## Resolution / verification

- Regenerate the 52-team 2002 cohort with the approved bb-chartgen-budget-alpha-v1 exporter and authored-bb-budget-aware-v1 model so it passes scripts/audit_generated_charts.py. Every team must satisfy the tactical-contrast and numeric-support checks, have no fully blank defensive chart, and carry complete provenance. Then pin the exact files in release/manifest.json, extend release/generated-chart-audit.json, update docs/generated-charts.md and docs/ATTRIBUTION.md, and add the cohort to the 1.1.0 scope. Keep PDF-imported 2002 teams excluded.

## Comments

--- 2026-11-16 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-16 — measured blocker evidence ---

The 52 generated 2002 bundles were produced by the older `college-chartgen-v1`
pipeline (generation manifests record `tool_version: college-chartgen-v1`,
`tactical_evidence: inferred-neutral`, and `family_evidence` observed counts of
zero for every play family). They load through the strict codec and the catalog
reports no problems, but they are not release-quality:

- **Tactical contrast: 0 of 52 teams pass.** The release audit requires strict
  directional run contrast across formations for gains 4, 10 and 18. Every 2002
  team returns identical primary values across the ordered formations (for
  example `[144, 144, 144]`), so `scripts/audit_generated_charts.py` would reject
  the whole cohort.
- **Blank defensive charts.** `california` and `oklahoma-state` are 100% neutral
  (`no_change`) across all 270 defensive cells, so every formation resolves
  identically. Twelve teams have under 10% non-neutral defensive cells; the
  cohort median is 44% versus 2007's 70–100% range.
- **Sparse defensive fill.** 32 of 52 teams fill under half of their defensive
  cells; the cohort minimum is 0.00 and median 0.44, against 2007's 0.70–1.00.
- **Model mismatch.** The release gate pins `authored-bb-budget-aware-v1`
  (`a46aaf83…`) and exporter `bb-chartgen-budget-alpha-v1`. The 2002 metadata
  records `source_filename: generated-model-v1.json`, which is not the approved
  model identity.

Offense and special-teams fill are comparable to 2007 (offense median 0.97,
special 0.86), so the defect is concentrated in the defensive generation.

The budget-aware exporter is not present in this checkout or its branches; only
the older `college-chartgen-v1` generator exists on
`origin/research/college-pbp-cohort`. Regeneration therefore needs the approved
exporter from the machine that produced the 2007 cohort.

Local-only verification: the 52 bundles were copied into the gitignored
`seasons/2002/` with their provenance CSVs for UI testing. Nothing was committed;
the two PDF-imported 2002 teams remain private and excluded.
