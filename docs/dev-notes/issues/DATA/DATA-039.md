---
id: DATA-039
title: Correct positive-only out-of-bounds evidence conditioning in generated charts
status: resolved
priority: High
milestone: 34a
created-at: 2026-11-05
resolved-at: 2026-11-05
closed-at: null
tags: [reproduced, out-of-bounds]
links: []
commits:
- 388546e
- a95ded6
---

## Description

Owner reports generated ordinary offensive yardage cells carry out-of-bounds
markers far too often. Initial generator inspection finds that the source adapter
records explicit narrative OOB as true and otherwise leaves the fact unknown;
the family-rate estimator conditions on only non-unknown observations. A synthetic
pool with one true and many unknown observations therefore requests 100% OOB.
This can affect engine clock behavior as well as chart presentation.

## Resolution / verification

- Preserve source and current chart artifacts; audit before regenerating or changing
  accepted inputs. Distinguish unknown facts from explicit in-bounds observations.
- Quantify generated OOB probability using all 216 offensive dice combinations,
  separately reporting numeric-cell conditional and unconditional probability.
- Compare every available generated team/play with its actual weighted source pool;
  record source evidence coverage and avoid claiming unknown outcomes are in bounds.
- Write synthetic adapter/estimator/encoding regressions first, demonstrate failures,
  and review an explicit evidence/denominator policy before implementation.
- Test conditional support, pooling weights, branch/supplemental behavior and finite
  dice quantization; retain regression evidence outside public historical inputs.
- Renew relevant clock/scoring/statistics/trace/replay and chart-health acceptance
  after any corrected generation. Completed games alone do not validate OOB flags.

## Comments

--- 2026-11-05 00:00 ---
Initial read-only cause: `tools/chartgen/evidence.py` emits true-or-unknown from
positive narrative evidence; `tools/chartgen/generate.py` filters unknown records
out of the OOB denominator. Current `family_pool` preserves source weights, so
pooling does not prevent this degeneracy. Investigating in an isolated audit
worktree; existing charts and source records remain unchanged.

--- 2026-11-05 00:01 ---
Parent approved the scoped estimator correction, synthetic regressions and
fresh-root regeneration. See the [cause, policy and test-first record](../../college-chart-oob-evidence-audit.md).
Source unknowns remain unknown; positive incidence is an explicit lower-bound
model. Release/coaching/timing acceptance must be renewed on the fresh candidate.


--- 2026-11-05 00:02 ---
Research generator repair tested at `388546e`; final 132 cumulative tests, 11
focused OOB and 22 metadata/docs checks pass without skips/warnings. The new
116-team manifest is frozen separately; release-codec comparison confirms only
OOB facts/provenance change, preserving all other chart facts. Independently
reconciled 1,392 exact-dice diagnostics and renewed current-engine acceptance:
128 distinct games plus two exact repeats, 19,847 primary-snap reobservations,
midpoint/final strict replay, full scoring/state/statistics/clock reconciliation
and legal committed calls. The full local source gate also passes: 3,984 Python/93.35% coverage,
147 frontend/build/audit, 54 browser, lint/dependency/docs and isolated 118-team
game/save/load assembly. Fresh pinned native/artifact release gates remain;
keep this ticket open until final integration/qualification is recorded.

--- 2026-11-05 20:53 ---
Frozen generator `388546e` passes the final 132-case cumulative run (472.02s),
11 focused OOB controls and 22 metadata/docs checks. Corrected current-engine
integration at `a95ded6` passes all renewed semantic/dice/source-support, timing,
scoring/statistics/trace/replay and legal-call acceptance recorded above, followed
by the complete local gate and successful pinned three-platform native workflow
42099569172. Exact inspected corrected assets are published as Alpha 6 Latest.
Source unknowns and the lower-bound narrative-incidence limitation remain explicit;
this resolves the positive-only denominator defect, not historical calibration.
Await owner play-test closure.
