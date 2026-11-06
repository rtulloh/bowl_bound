---
id: DATA-041
title: Generated charts lack a mandatory probability and tactical release audit
status: open
priority: High
milestone: 34a
created-at: 2026-11-05
resolved-at: null
closed-at: null
tags:
- reproduced
- release-gate
links: []
commits: []
---

## Description

The neutral generated defense cohort passed structural and complete-game checks despite equivalent A-F distributions. Require a synthetic-tested exact-dice tactical and provenance gate on the actual shipped candidate before build/publication.

## Resolution / verification

- Demonstrate failure for neutral and visually different equal-mass charts before implementation; valid authored controls pass.
- Recompute normalized probabilities and engine-resolved directional benefits/costs for actual pinned inputs; reject stale or missing source/model expectations.
- Require the audit in CI and packaging, preserve separate private source/OOB qualification and current-engine game/coaching validation.

## Comments

--- 2026-11-05 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-05 17:00 ---
Synthetic test-first controls reproduce the missing neutral rejection and native
freezer bypass, then pass with the durable semantic gate. Imported-resolver and
rejection-evidence identity controls also fail first and pass after fixes.
Implementation and phase references: [audit-gate notes](../../generated-chart-audit-gate.md).
The current neutral catalog deliberately fails the new gate; keep open until the
release owner reviews/integrates it and validates the corrected tiny/full cohort.
No historical chart fixtures enter unit tests; private source/OOB qualification
and full current-engine/coaching/statistics/clock/trace/replay remain separate
required publication evidence.

--- 2026-11-05 16:41 ---
Implementation checkpoint: 25 focused synthetic controls pass; relevant package,
native/smoke/installer/docs cumulative run passed 160 cases at its earlier
collection boundary, and the final gate+docs run passed 47 cases. Ruff lint/format,
index and whitespace checks pass; no skips or warnings. A separate ignored local
integration rejects all 116 old neutral generated defenses for equivalent physical
probabilities. Native inventories retain compact computed audit identities/report
hashes without adding assets or private runtime files. CI blocks the old cohort
until corrected charts and qualified expectations are integrated. Source/OOB truth
and full current-engine qualification are not asserted by this public gate.

--- 2026-11-05 16:43 ---
Independent release-owner review found no blocker. Final relevant cumulative
acceptance passed 165 tests in 14.00s, including 27 synthetic gate controls and
explicit QT/FUMBLE pending-class controls. The gate never infers completion from
the original passing call and never credits unresolved branches as completed
zero-yard plays. Terminal event/statistics and calibration observers remain a
separate release-owner verification. No skips or warnings; lint/format/index and
whitespace pass. Keep open until corrected-cohort/CI integration is accepted.
--- 2026-11-05 18:00 ---
Release integration reproduced a native staging blocker: the source engine digest
included two development audit modules intentionally excluded from runtime. Two
new synthetic regressions fail first (valid staged candidate rejected; unselecting
an existing runtime module accepted). The follow-up identifies the exact approved
runtime core, requires identical candidate selection and actual core bytes, and
retains foreign imported-module rejection. No engine rules, chart data, native
resource selection or release assets change. Regenerate final engine/auditor
report identities after integrating this follow-up.

Follow-up verification: 167 relevant cumulative tests passed in 13.41s, including
29 synthetic gate controls; lint/format/index and whitespace checks pass with no
skips or warnings. The release owner must rerun the exact corrected-cohort native
preflight and final full regression after integration.

--- 2026-11-05 18:30 ---
Corrected source and native stage both pass the mandatory recomputed 116-team gate after integration at b0d2942; canonical computed report SHA-256 is 9781e862f3ff06bfdf9fb23e25f2b1d45aa0681f45dca8d8dc02f6fb26a34ace. Source/staged approved runtime identities match. Final complete local regression passes 4,040 tests with 93.41% branch-inclusive coverage, plus lint/format/dependencies, 158 frontend tests/build/audit and 64 real-engine browser cases. Keep open until the committed corrected candidate and upstream native integration are recorded.
