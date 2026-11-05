# Alpha 6 generated-chart release preparation

The owner authorizes integrating the existing generated 2007 cohort and publishing
Alpha 6 on 2026-11-05. This supersedes Alpha 5's sample-only scope for reviewed
generated outputs. It does not authorize distributing benchmark PDF charts,
source PBP/narratives, raw caches, private reference comparisons, logs, saves or
historical rosters. Recent-season generation and the web chart viewer are separate.

Tracking: [DEV-072](issues/DEV/DEV-072.md), Milestone 34a. Preparation is not release
acceptance or a claim that overall historical calibration is complete.

## Paydirt consultation

Reviewed local Paydirt `.github/workflows/release.yml` and
`docs/chart-generation-workflow.md` before this release phase. Adapt test-before-build,
native acceptance, exact provenance, immutable profiles, actual scheduled opponents,
and explicit distinctions among mechanical reconciliation, historical fit and Hard
coaching diagnostics. Do not copy automatic tag publication, unpinned dependencies,
optional installer failure, recursive team staging, NFL coefficients/layouts,
private reference data or a runtime dependency. Bowl Bound's pinned manual workflow
and exact reviewed manifest remain authoritative.

## Integration boundary

Work occurs in an isolated worktree from public `origin/main` at `9b02e58`, preserving
the owner's dirty checkout, Alpha 5 worktree/tag/assets and other research worktrees.
The research branch's current 116-team cohort loads with the unchanged release
runtime, so no research-tool implementation/history is merged into this chart
release. The independent research branch remains intact. Root's recent-season
planning commit `5fcc4e3` is integrated selectively with public-safe 34/34a roadmap
context; DATA-037 is correctly assigned to 34b and its index is regenerated.
The current release engine and AI remain authoritative.

The earlier retained 116-team season study used frozen baseline/v1/v10 coaching.
Its two 651-game seeds and exact repeat establish mechanical evidence for those
inputs, not current release AI validation, independent historical accuracy or a
calibrated national champion. Milestone 34a remains in progress.

## Exact catalog tooling

Synthetic regressions first fail against the unchanged implementation: the release
schema rejects an explicitly pinned generated bundle, and the native smoke has no
expected-catalog parameter. Extend the manifest with an optional exact
`generated_sha256` map. Permit only complete bundles (`team.yaml`, offense,
defense and special CSVs plus each team's generated virtual-cell provenance CSV),
verify every selected hash, and retain the original
fictional sample hash checks. Nearby rosters, source files and unselected teams
remain excluded. No wildcard seasons copy is introduced.

Native smoke derives the expected team IDs from the already verified artifact
inventory, rejects missing/extra/duplicate catalog entries, and exercises a real
snap and save/load for every packaged team. The installed Windows application uses
the same check before uninstall/personal-file preservation acceptance.

## Provenance and selected cohort

Root approves the scoped distribution basis on 2026-11-05 under the owner's
explicit Alpha 6 request. Independently checked current primary sources:
SportsDataverse's release-store README advertises CC BY 4.0 and describes data
releases consumed by its loaders; Creative Commons permits redistribution and
adaptation with credit, license link, modification notice and no implied endorsement
or additional restriction. The MIT file covers software and is not substituted
for that data grant. ESPN-source lineage and the existing upstream-terms caution
are retained; this is not a blanket assertion of upstream clearance or rights to
source narratives. Reviewed output scope consists of generated numerical/semantic
statistical facts and factual identifiers, with no expressive source play text,
private benchmark cells, historical rosters or logos. Distribution scope remains
separate from source availability and historical-fit claims.

Initial candidate cohort: corrected-v5 review phase-one 2007, frozen generation manifest
SHA-256 `6b22c460aa843fcd8f7bd9de51898c050554f9113188bd4c4810929ec7fa3a1a`,
source snapshot `1f8e553002c0299a2993eb533231053d6cf406dbe0e9d41ecc400267484bb1ba`.
All 116 normalized bundle hashes match the frozen manifest using the final release
codec before copying. Retained profiles are neutral; the 21-team refinement subset
is not substituted for the full cohort. The exact copy contains 464 chart files
and 116 required generated virtual-cell provenance CSVs. Those CSVs contain only
short generated cell evidence (maximum field length 19 characters in this cohort),
not historical narratives or PDF provenance. Private root reports and two historical
rosters were not copied. The two original fictional samples and their rosters remain.

The initial four-file manifest test exposes the required fifth codec resource;
further synthetic regressions fail before accepting explicit generated provenance
and before rejecting its absence. No runtime codec is bypassed. Every generated
resource is individually hash-pinned. Generated-content licensing/attribution,
coverage, modifications and calibration limits accompany the runtime.

## Initial current-engine acceptance and discovered follow-ups

The first current-Hard audit failed: 113 games completed and three aborted when a
penalty displaced a two-point try. Its zero-fallback assertion was also too broad:
bounded one-action estimates explicitly flag a hypothetical penalty that requires
another snap. Preserve those initial failed records; they are not acceptance.

Milestone 39 commit `e4bfa8b` corrects only the analysis factory's current
first-and-goal domain. Synthetic tests first demonstrated 14 expected failures and
two passing controls. The fix passes 85 focused and 456 cumulative coaching/try/
overtime tests; malformed inputs and prior two-yard deterministic/replay behavior
remain covered. No policy version, live scoring rule or gameplay dice changed.
The independent [bounded valuation follow-up AI-034](issues/AI/AI-034.md) stays open.

Before the OOB correction, every generated team was the current
Hard-v15 computer once, against a baseline-v15 opponent in deterministic cycle
matchups. All 116 games complete with midpoint and final strict replay. Twelve
additional seeds/pairs also pass; these are a bounded mechanics sample, not an
actual conference-schedule or stratified conference-coverage claim. Two complete
canonical game results repeat exactly. Independent stored-record/hash review and
primary-event reobservation reconcile 21,345 primary snaps across 128 distinct
games (130 executions including repeats). All recorded committed choices are legal.
All recorded Hard kick-selection roles have zero early-down punts and zero field-
goal choices beyond the public 55-yard policy limit. Ordinary offense uses all
nine calls plus QB Sneak/RZDZ, and defense uses A–F. Across 85 comparable-situation
groups with at least 20 calls, the largest observed single-call share is 45.8%;
this describes variety, not optimal coaching or historical calibration.

Retain 53 explicitly flagged legal comparisons: 29 offensive and 24 defensive,
all two-point tries. Diagnostic instrumentation, including strict replay analysis,
records only `EvaluationError: hypothetical try did not settle`; synthetic controls
confirm a hypothetical accepted penalty requires another snap, not a completed
zero/two result. There are no committed illegal calls or game aborts. Do not erase
these bounded-model flags or claim the AI-034 valuation limitation is fixed.

## Local release checks

- Focused release/metadata/launcher/docs/catalog tests: 104 passed.
- Frontend: 147 unit tests, production build and npm audit passed; zero vulnerabilities.
- Real-engine Chromium: all 54 checks passed in four minutes using a unique synthetic
  seasons fixture directory, preserving the owner's and other agents' fixtures.
- Fresh exact staging/build/runtime assembly passed with pinned Node 24.22.1/npm
  11.19.1. An isolated runtime (not checkout imports) reconciled exact 118-team
  catalog, UI/assets and a real snap plus strict save/load for every team.
- Repository-wide Ruff lint/format and dependency consistency passed.
- Full Python gate: `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`:
  3,983 passed in 833.45 seconds; 93.35% branch-inclusive coverage (75% floor),
  no skips or pytest warnings. All gates complete before the release-source push.

An initial frontend invocation picked up the shell's Node 18 and failed before
tests; reran with the pinned Node 24 path. An initial browser startup encountered
a pre-existing shared synthetic-fixture symlink; reran against a new isolated path
without deleting another task's fixtures. These failed attempts are retained.
Observed npm whatwg-encoding deprecation, Vitest jsdom performance advisory and
Playwright NO_COLOR/FORCE_COLOR warning. Existing DEV-044/DEV-064 warnings were not
emitted by the final local frontend run; do not claim suppression or closure.
The prior interrupted pre-fix Python run is retained separately, not counted as pass.

No remote push, tag, build dispatch or publication is recorded by this preparation
checkpoint. Native inspection, warnings and actual release URL follow.


## OOB data hold and corrected cohort

Owner playtesting identified near-universal ordinary numeric OOB flags before any
Alpha 6 tag or release was created. The native candidate at `9a2897f` passed its
mechanics/build checks after the bounded catalog-smoke repair, but those checks
did not establish correct conditioning of source flags. Publication was held; old charts, native artifacts and detailed
audit evidence are preserved. [DATA-039](issues/DATA/DATA-039.md) tracks the defect.

The canonical research generator repair `388546e` retains source True/False/None
and models weighted positive narrative mentions over all matching ordinary numeric
outcomes. It conditions B/QT/QR on their existing outcome supports, and records
unknown/explicit/positive counts, exact 216-combination achievement and unidentified
states. Unknown is not observed in bounds; this is a lower-bound narrative-incidence
model, not a fully measured historical OOB frequency. Synthetic controls first fail
on the old implementation, including irrelevant incomplete-pass mentions and the
empty-QT support guard. The [cause and reviewed policy](college-chart-oob-evidence-audit.md)
records the bounded correction. Generator implementation/history is not merged
into the standalone release runtime.

Corrected frozen manifest SHA-256:
`e0fddc5f0e888e5339a924a908a813766c729b195b8c6cf72e2e89cda0f88939`.
Source snapshot, seed 19 and neutral profiles/tactics are unchanged. Independent
release-codec comparison confirms all 116 teams preserve non-OOB semantics, colors,
source-token bases, PATs, recovery and team metadata. Only 116 offense CSVs and
116 required central provenance CSVs change; exactly 580 generated resources remain
pinned and all 15 original sample resources remain hash-identical.

Independent verification reconciles all 1,392 ordinary/supplemental columns: source
support counts and weights, positive/all-support incidence, exact physical dice
mass and independently nearest attainable numeric OOB allocation. Diagnostics
retain 1,266 partial-positive and 126 unidentified states. The source-pool crosswalk
separately checks all 1,044 ordinary columns. Frozen generator acceptance passes
132 cumulative tests in 472.02 seconds, 11 focused OOB tests and 22 metadata/docs
checks, with lint/format and no test skips or warnings.

Renewed corrected-catalog acceptance uses the current public engine/Hard-v15 and
baseline-v15 opponent: all 116 cycle games pass in 420.5 seconds, plus 12 further
seed/pair games and two exact complete-result repeats. Independent primary-event
review reconciles 19,847 snaps across 128 distinct games. Every committed call is
legal; all recorded Hard kick roles have zero early-down punts or field-goal
choices beyond the public 55-yard limit. All nine calls plus Q/RZDZ and A–F occur.
Among 68 comparable-situation groups with at least 20 calls, the largest single-call
share is 45.8%; this describes variety, not coaching optimality or historical fit.

Retain 53 legal bounded comparisons (22 offense/31 defense), all two-point tries.
Only `EvaluationError: hypothetical try did not settle` occurs in diagnostic
instrumentation, including strict replay (863 instances); these are hypothetical
estimates, not committed illegal calls or aborts. AI-034 remains open. Independent
timing review checks 23,514 standard charges, exact 3,600 regulation seconds in
every game, and ordinary late-half bounds semantics: OOB 10 seconds, in-bounds
20/30 seconds. Midpoint/final strict replay, scoring, state, statistics and structured
traces reconcile. Frozen source and staged resources remain hash-identical.

Fresh isolated source/runtime assembly passes the exact 118-team catalog, UI/assets
and every-team snap/save/load (catalog discovery 3.33 seconds). Frontend 147 tests,
production build and audit pass; all 54 real-engine browser checks pass in 4.1
minutes; Ruff/dependency/docs checks pass. Renewed full Python coverage passes
3,984 tests in 848.97 seconds, with 93.35% branch-inclusive coverage and no test
skips or warnings. All local gates complete before the corrected-source push.
Fresh pinned native/artifact acceptance remains pending. Prior old-catalog
game/build passes do not count as acceptance of the repaired catalog.
