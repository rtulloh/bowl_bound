---
id: DATA-037
title: Generate charts for recent college seasons starting with 2025
status: open
priority: Medium
milestone: 34b
created-at: 2026-11-05
resolved-at: null
closed-at: null
tags:
- planning
- recent-seasons
links: [DATA-045, DATA-054]
commits: []
---

## Description

Owner requests recent-season chart expansion, starting with 2025 and proceeding backward through 2024, 2023 and earlier years. Reuse the reviewed play-by-play generation pipeline with explicit per-season source coverage and distribution provenance. This is follow-up work separate from the current Alpha 6 release cohort; recent seasons cannot rely on a Bowl Bound benchmark chart being available.

## Resolution / verification

- Start with 2025, document the descending year order, and report any source-availability gaps before choosing the next season.
- Review source terms, provenance, team/game coverage and generation quality gates for each season; retain explicit rejected-team reasons and preserve source hashes and generator configuration.
- Assess the earliest supportable legacy years separately from the default 2025-backward order. Inventory aggregate/PBP availability, missing variables, source rights and changing rules; recommend a supported historical range and explain where a reduced-data method would require separate qualification.
- Validate without assuming benchmark charts: reconcile generated team behavior with approved real-season aggregate evidence and use deterministic multi-seed game and conference-season audits with scoring, clock, statistics, trace and save/replay checks.
- Use year-appropriate team identities, conference alignment, schedules and supported postseason/rules metadata; make approximations or unsupported season behavior explicit instead of inheriting the 2007 BCS profile silently.
- Use synthetic public regression tests for pipeline changes and keep private charts, raw caches, saves and detailed audit evidence out of ordinary test collection and publication.
- Record per-season coverage, outliers and known limitations, then obtain separate release acceptance for each expanded cohort; do not delay or expand Alpha 6 with new-year generation.

## Comments

--- 2026-11-05 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-05 11:00 ---
Planning only: assigned to new M34b so the existing M34a historical cohort and
Alpha 6 publication remain distinct. The requested default order is 2025, 2024,
2023 and backward. No new-year generation or release acceptance is claimed.
Paydirt consultation and validation boundaries are recorded in milestone-34b.md.
