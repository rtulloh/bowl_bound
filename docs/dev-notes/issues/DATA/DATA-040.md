---
id: DATA-040
title: Generated defensive formations have no tactical probability differences
status: open
priority: High
milestone: 34a
created-at: 2026-11-05
resolved-at: null
closed-at: null
tags: [reproduced, investigating, tactical-model]
links: []
commits: []
---

## Description

Owner reports repeated generated pass-defense columns across formations A–F.
The accepted generator uses an all-zero neutral tactical profile. Team defensive
strength differs between teams, but neither the neutral profile nor the source
observations identify tactical A–F tradeoffs. This removes meaningful defensive
formation choice from ordinary chart lookups. The issue is broader than display
formatting: probability distributions match even where individual rows differ.

Synthetic example: a modifier on defensive row 1 has mass 12/36; putting the same
modifier on rows 2 and 5 also has mass (11+1)/36. Visibly different columns can
therefore remain tactically equivalent. Compare normalized outcomes and exact
physical dice mass, not merely text uniqueness.

## Resolution / verification

- Preserve existing cohorts and immutable release tags; do not fix the viewer or
  invent chart coefficients during the audit.
- Quantify all nine defensive plays, A–F and all four pass columns using normalized
  semantics, priority, locations, color and exact 36-combination defensive mass.
- Separate measured team strength, unobserved formation/call data, modeled tactical
  structure and finite-row placement. Review ordinary and special engine paths.
- Review an explicit Bowl Bound tactical-policy authority before implementing a
  structural model; do not copy Paydirt/NFL templates or private reference values.
- For an approved correction, first demonstrate synthetic failures for meaningful
  direction-specific tradeoffs, team-strength separation and probability semantics;
  then review real-engine interactions and full-cohort calibration/coaching audits.
- Uniqueness, completed games and aggregate scoring alone are insufficient tactical
  acceptance. Preserve honest unidentifiable/source and modeled-policy labels.

## Comments

--- 2026-11-05 00:00 ---
Read-only audit reproduced the gap across the complete accepted cohort. All nine
plays have equal weighted outcome distributions A–F; all four pass columns are
equal in distribution within every formation. See the
[audit and correction boundary](../../college-chart-defense-formation-audit.md).
No generator, chart, engine, viewer or release-tag change was made. IDs were
checked across local worktrees and branch trees before reserving DATA-040.

--- 2026-11-05 00:01 ---
Documentation/issue validation passed: 22 existing checks, no skips or warnings;
index regeneration and `git diff --check` pass. Strict-codec enumeration of the
complete cohort agrees with the parent's independent CSV and engine audit. This
is an audit checkpoint only; no tactical correction was implemented, so the issue
remains open. Production source is unchanged from `b232fd9`.
