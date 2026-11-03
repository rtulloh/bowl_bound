# Milestone 34a — expanded historical college cohort calibration

Status: in progress. Owner reviewed M34's engineering prototype and authorized
2007 and 2008 major conferences first on 2026-11-03. Completed M34 remains on its
original branch; this work is isolated on `research/college-pbp-cohort`.

## Engine integration

Merged reviewed M33 `f82ad47` into accepted M34 `20e5f73` as `335f8f6`. Preserved
M34 replay/training extensions and M33 strict overtime controls; regenerated the
issue index rather than choosing one branch's generated snapshot. The fresh
Python 3.12 environment imports this worktree. Existing focused generator,
runner, fumble, timeout, fourth-down and tracker tests: 294 passed in 45.35 seconds.
No new engine or coaching behavior is planned. Old M34 calibration remains pinned
to its earlier engine and is not represented as renewed evidence.

## Paydirt consultation before this phase

Reviewed `docs/chart-generation-workflow.md`,
`docs/dev-notes/chart-generator-tuning-tool.md`,
`docs/dev-notes/generated-chart-completeness-audit.md` and
`paydirt/chart_tuning.py`, in addition to the M34 references. Adapt actual schedule
weighting, per-team exposure gates, paired candidates, immutable profiles, unused
validation seeds, per-team diagnostics and full-source sampling lessons. Do not
reuse NFL schedules, full recursive chart closure, coefficients, row layout,
18-yard caps, historical matrices or packaging/promotion permissions. Bowl Bound
retains its own physical probabilities, codecs and real engine.

## Boundary and acceptance

- Audit historical membership and expected schedules for both years with exact
  source URLs/hashes. SDV/CFBD membership is not independent NCAA corroboration;
  primary NCAA confirmation remains pending after a failed source fetch.
- Game-ID presence alone cannot establish PBP completeness. Preserve coverage,
  sequence/field diagnostics and uncertainty; missing source is never a fake team.
- Use a bounded core, evidence-qualified one-hop outer opponents and explicit
  external/unresolved context. Do not recursively require every opponent's chart.
- Every excluded game has a reason. Restricted-slate targets use exactly eligible
  game IDs, separately for each team's offense and defense; full-season context
  remains separate and regularized. No full-season reconstruction claim follows
  from a restricted slate.
- Generate a concrete private coverage/batch checkpoint and send it for parent
  review before broad candidate simulations.
- Add batch/cache, deterministic schedule/seeds, bounded/shrunk per-team tuning,
  per-team/conference assessments, immutable checkpoints/resume and no-fit states
  with synthetic red/green tests and backward compatibility.
- Separate simulation-held-out seeds from source-game exclusion diagnostics. An
  unseen-source claim requires excluding those rows from every opponent fit too.
- Complete real-engine audits and full local/hosted gates, preserve all historical
  artifacts privately, and stop at a dedicated 34a acceptance commit for review.

## Source checkpoint

Versioned 2007/2008 PBP archives and selected M34 inputs were copied into this
worktree's ignored private storage; original references and pilots are unchanged.
Parent acquired versioned SDV membership/group/schedule snapshots with hashes.
Their coverage audit shows uneven availability; it is not completeness proof.
Independent primary-source corroboration and event-level qualification are pending.


## Owner-selected fixture/report contract

Latest owner direction supersedes optional balanced-cohort sensitivity ideas:
only actual recorded fixtures in the corresponding 2007 or 2008 season may be
simulated. Include qualified historical conference games, major interconference
games and available BCS/bowls. Repeated seeds replay those fixtures; no invented
pairings or cross-year opponents. Public synthetic fixtures remain ordinary tests.

Generate private Markdown and CSV/JSON matchup reports before large calibration.
Each physical fixture appears once with date, IDs, sides, historical affiliations,
neutral/postseason classification, evidence and inclusion reasons; team indexes
cross-link selected OFF/DEF IDs, opponents, exclusions and full/restricted coverage.
Freeze manifest/source/engine/profile hashes and prove reports, targets and actual
simulation fixtures are identical. The user requested review of this concrete
slate before broad runs; general authorization to implement does not replace that
review. Continue independent tests, generation and documentation meanwhile.

Red/green scope checks: initial collection failed because the new contract module
was absent; four synthetic cases now pass. New cache and sparse-fallback tests
then failed as expected: no reusable model existed, and reversing source order
changed the sparse fallback from one extreme to the other. Full-distribution
stratified pooling and a reusable source snapshot are under focused validation.

Phase-one test-first checkpoint (2026-11-03): exact historical fixture/target
contracts, cached deterministic generation, private CSV/JSON/Markdown report hashes,
invalid opponent/year/neutral rejection, missing-team states and no-overwrite CLI
checks are implemented. New tests first failed for absent interfaces or biased
sparse sampling. Focused cumulative generator/runner/tracker run: 125 passed in
36.76 seconds; Ruff check and format pass. No broad simulation has started.

Source screening correction: repeated stale late-game snap clocks cannot establish
missing plays. A new synthetic regression failed before moving that condition to
an explicit uncertainty warning. Four-period, minimum-volume and known-primary-
yardage checks remain required; official event completeness is never asserted.
Initial strict-screen private audits are preserved unchanged.

## Concrete phase-one checkpoint

Both years now have private generated cohorts and proposed fixture reports:
2007: 116 generated charts, 345 selected actual fixtures, 449 explicit exclusions;
2008: 120 generated charts, 359 selected fixtures, 451 exclusions. These are
sequence-screened engineering candidates, not officially complete historical
reconstructions. Restricted exposure varies by team. Parent received exact local
Markdown/CSV/JSON paths, hashes and a bounded proposed run budget for owner review.
No broad simulations were started. Original M34 pilots/reference charts remain
untouched. Added maintained operator/source/report guidance in
`docs/college-cohort-generator.md`.

## Phase-two implementation checkpoint

Reconsulted Paydirt's tuning runner and tests before this phase. Adapt globally
selected paired candidates and immutable profiles, not its NFL sample schedule
or coefficients. New cohort runner uses the existing engine audit, actual
fixture sides/postseason configuration, distinct seed domains, at most two
submitted tasks, per-team OFF/DEF and conference summaries, atomic retained
results and checksum-verified resume. Complete synthetic two-phase integration
with generation/training/held-out saved replay/coaching assessment/identical
regeneration/resume passed in 35.65 seconds. Sparse metric Infinity serialization
was reproduced and tracked under DATA-015; explicit null/failed assessments
preserve the sample gates. DATA-013 also records the supported-Python buffering
regression caught by the two-worker test.

DATA-016's failing synthetic case showed offensive yardage refinement altering
defensive forced-completion responses. Defense now uses an explicit league
completion prior plus independent defensive effect. Separate bounded defense
residual knobs preserve offense. Revised private phase-one v2 cohorts retain the
same actual fixture sets and old artifacts. All 236 revised charts reloaded and
passed exact weighted physical priority audits, with zero failures.

DATA-017 records that provider neutral flags and championship labels can be wrong
even when related sources agree. Identity-matched primary-evidence overrides
preserve raw values and hashes. Parent is researching corroborating historical
labels; current proposed reports disclose unresolved classifications. No broad
historical simulation has started before the requested concrete-slate review.

Frontend/dependency checkpoint: fresh `npm ci`, all 130 Vitest cases, production
build and npm audit passed with zero vulnerabilities; Python `pip check` passed.
Install output retained the existing whatwg-encoding deprecation and optional
fsevents install-script notices; no scripts were approved or warnings suppressed.
A focused resume regression correctly rejected a run while tool source changed
during implementation; stable-source reruns are required. A later genuine CSV
LF/CRLF resume mismatch was reproduced under DATA-013 and corrected with an
explicit LF export contract, retaining exact content checks.

Stable-source phase-two cumulative gate: 139 generator/runner/tracker tests passed
in 76.92 seconds, including two-worker interrupted resume and exact final
matchup usage exports. Ruff checks/format passed. The existing runner expectation
adds only `game_type: regular`, reflecting a newly recorded audit configuration;
its default engine behavior is unchanged. Historical postseason runs now pass
the existing engine's postseason option explicitly. No runtime module or release
manifest change is needed: all changes remain development tooling/tests/docs.

This is a testable implementation boundary, not completed 34a acceptance. Full
regression, fresh hosted browser checks, concrete slate review and measured
historical calibration remain outstanding.
