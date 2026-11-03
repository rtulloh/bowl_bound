# Milestone 34 — two-phase college chart generator

Status: implementation and regression complete; ready for milestone review. The
owner requested independent parallel work with Milestone 33 on 2026-11-02. Engine baseline: `03d1992d3a3811cf89879bce985e23937e3a3dc0`.
No fit from this branch applies automatically after engine/coaching changes.

## Paydirt consultation

Reviewed `/Users/rtulloh/work/paydirt/docs/chart-generator.md`,
`docs/chart-generation-workflow.md`, `docs/dev-notes/statistical-chart-generator.md`,
`docs/dev-notes/chart-generator-tuning-tool.md`,
`docs/dev-notes/generated-chart-completeness-audit.md`, `generate_charts.py`,
`generate_nflverse_charts.py`, `tune_charts.py`,
`paydirt/chart_generator.py`, `paydirt/chart_tuning.py` and
`paydirt/nflverse_play_by_play.py` before implementation.

Adapt: immutable source baseline, explicit calibrated profiles, empirical weighted
quantiles, regularized opponent effects, paired candidate seeds, separate unused
validation seeds, joint outcome metrics and failure retention. Reuse Bowl Bound's
own codec, normalization, physical dice, engine, save replay and audit contracts.
Do not reuse NFL family classifiers, 10–39 probabilities, the 18-yard run cap,
NFL sack accounting, tactical cell layouts, coefficients or historical matrices.
Also reviewed the synthetic source/generator/tuning and runner tests in
`tests/test_chart_generator.py`, `test_chart_tuning.py`,
`test_chart_tuning_runner.py`, `test_nflverse_play_by_play.py` and
`test_generate_nflverse_charts.py`, including denominator, paired-seed,
source-precedence and opponent-adjustment cases.
There is no Paydirt runtime dependency. Reference studies and learned bounds stay
in ignored `private-data/chart-generator/`.

## Phase A acceptance

- Source identity/hash/scope and game completeness are explicit.
- Source-neutral evidence preserves penalties, turnovers, sacks, scoring yardage
  and special teams; uncertain play families remain inferred or unknown.
- All 810 cells and 30 PAT results load through the production codec.
- Determinism, weighted probabilities and safe private output have synthetic tests.

## Phase B acceptance

- Separate real-engine simulation/refinement command, bounded profiles, immutable
  candidates, paired training seeds and held-out validation.
- Joint completion/interception/sack/efficiency/fumble/special-team assessments;
  scoring/volume/clock/call diagnostics and uncertainty remain visible.
- Multi-seed completed-game reconciliation and save replay, both possessions;
  retain failures and best candidates. Distinguish mechanics study from a matched
  historical schedule fit. Repeated two-team games cannot establish historical fit.
- Synthetic tests, full regression and documented private play-test commands.

## Source selection

The public SportsDataverse ESPN-derived Parquet releases contain 2007 and 2008.
The initial file audit finds all 13 Ohio State and 14 LSU scheduled games, including
LSU's conference championship and the January title game under season 2007.
Game coverage has been checked against the official schedules. Event-level
coverage diagnostics and unresolved official aggregate deltas remain explicit;
source data is not silently replaced with revised totals.
NCAA-derived bulk data begins in 2013 and cannot supply this pilot.

Primary references checked 2026-11-02:
[ESPN loader](https://cfbfastr.sportsdataverse.org/reference/load_espn_cfb_pbp.html),
[NCAA loader](https://cfbfastr.sportsdataverse.org/reference/load_ncaa_mfb_pbp.html),
[CFBD terms](https://collegefootballdata.com/terms),
[Ohio State 2007 archive](https://ohiostatebuckeyes.com/sports/2018/7/2/2007-football-season),
[LSU statistics archive](https://lsusports.net/fbstats).
Raw snapshots and audits remain private; software licenses do not establish
redistribution rights for all underlying sports content.

## Verification log

- Created isolated Python 3.12 environment; confirmed imports resolve inside this
  worktree, independently of the parallel Milestone 33 engine changes.
- Wrote source, complete-bundle, profile/seed, provenance, CLI and engine tests
  before implementation; missing-module collection failures demonstrated the new
  contracts. Source PAT precedence and accepted no-play penalty tests failed on
  the first implementation, then passed after the corrections.
- `python -m pytest tests/chartgen tests/test_issue_tracker.py -q`: 45 passed
  before later full replay/strength regressions were added.
- Four private pilot smoke games reconciled through the production local-season
  audit; their initial PAT source defect is tracked in DATA-003. Retained those
  artifacts and regenerated a versioned input rather than overwriting evidence.
- Every pilot source has no populated depth/direction observations; generic family
  estimates are explicitly pooled. Official aggregate mismatches remain DATA-002.
- Initial prototype docs: [generator guide](../chart-generator.md).
- Added optional midpoint restoration and final journal replay to the existing
  local-season development runner. The default runner behavior and runtime engine
  are unchanged. This avoids the legacy coaching audit's invalid assumption that
  every rendered trace cell must be nonempty (DATA-004); normalized blank cells
  remain blank. The structural local-season trace validator remains authoritative.
- The complete two-phase synthetic test checks immutable baseline retention,
  disjoint held-out seeds, real complete games, restored continuation, final replay
  and a separate `chart-v10` coaching-policy assessment. Insufficient statistical
  exposure remains a failed fit gate even when mechanics pass.
- At this initial boundary, full regression, bounded private refinement and
  acceptance review remained pending; later results follow below.


## Initial private pilot and overtime audit finding

Prototype commit: `55f530d`. Focused cumulative checks at that boundary:
`python -m pytest tests/chartgen tests/test_local_season_runner.py tests/test_issue_tracker.py -q`
— 79 passed. Ruff check/format passed. No runtime engine files changed.

The first 128-game baseline training batch completed every game, but four games
failed the development audit because lawful overtime series resets were treated
as disconnected states (DATA-005). The run was interrupted during the next
candidate; no held-out seeds were consumed. All artifacts were retained.

Added failing synthetic tests requiring exact engine-observed series boundary
state, chronology and OvertimeState order. Undeclared/stale boundaries still fail.
All four retained private seeds then passed the corrected audit with unchanged
charts and midpoint/final replay; one exercised four overtime rounds.
`python -m pytest tests/test_local_season_runner.py -q` — 34 passed.
The correction changes development audit evidence, not football rules or charts.


## Evidence and model review before renewed calibration

The simplify review retained the production codec/dice/priority engine and reused
one privacy guard across normalization, bundle output and refinement. Added red/green
coverage for resolved-path traversal, owner-only source files, non-return zeros,
unknown fumble evidence, source boolean validation, return fumbles and calibrated
family-specific yardage. Observed zero gains use white no-change boxes so engine
QB Sneak color behavior is preserved. Joint run/completion tails support pass B.

Neutral formations alone are not a convincing tactical play test. Added an optional
private pooled formation prior learned from the four authorized reference charts.
Every effect is centered per play to separate formation roles from team strength;
public defaults/tests remain neutral/synthetic. No cell rows/templates or private
coefficients are committed. Bounded 50% shrinkage is an explicit modeling choice,
not a claim that defensive calls were observed. Both phases record the profile hash.
Four latest private tactical pilot games completed and reconciled successfully.

Saved official school source files/hashes and schedule review privately, including
Ohio State's 13 games and LSU's 14 with conference/title games. Normalized source
versus official aggregate deltas remain visible; no hidden aggregate replacement
or historical-schedule fit claim is made. The private source/PAT/non-return fixes
use a new versioned evidence file. Earlier inputs and failed audits are retained.


Pre-calibration focused cumulative gate: 101 passed across generator,
local-season audit and issue tracker. Ruff check, format check (555 files),
`pip check`, frontend 128 tests, production build and npm audit (zero findings)
passed. npm reports the existing `whatwg-encoding` deprecation; no warning was
suppressed. No runtime engine files or packaging/sample allowlists changed.


## Full-gate findings and renewed observation coverage

The first full pytest run stopped at collection: the generator and terminal CLI
tests shared an unqualified module name (DATA-007). A package marker preserves
both suites; targeted collection then found all 30 tests. The full gate must be
rerun. Local Chromium could not start any of 33 tests because the macOS sandbox
denied MachPortRendezvous bootstrap (1100); this is not a passing browser gate.

Four additional failing synthetic regressions expose missing primary yardage in
calibration targets, independent-game uncertainty clustering, engine return-trace
section aliases and explicit current baseline policy selection (DATA-002/008/009).
The first pilot remains frozen; all candidate charts and game reports are retained.
Its baseline-v1 coaching always fair-catches punts, so a renewed pilot needs a
recorded current public-observation policy and a fresh held-out seed domain.
No football engine changes or tolerance widening are authorized by these findings.


The frozen pilot completed 384 training games, 512 held-out games, four
midpoint/final save-replay checks and four mixed coaching assessments with zero
reconciliation failures. All predeclared core efficiency gates passed in the
selected candidate and held-out batch. The original report honestly failed return
gates. Reanalysis of retained traces using the corrected observer and independent
game clusters leaves only the unobserved punt-return gate failing; the selected
candidate remains unchanged. Original reports and hashes remain intact.

The shared runner keeps its historical baseline-v1 defaults. Generator training
now explicitly selects public-observation baseline-v10 for both roles, retaining
team-independent legal choices and no chart lookahead. This covers punt returns;
a fresh paired training/held-out domain is required. Missing primary yardage fails
calibration before targets are constructed. Synthetic red/green checks cover
aliases, exposure-weighted game clusters and known ratio standard-error math.

`python -m pytest tests/chartgen tests/test_local_season_runner.py
tests/test_issue_tracker.py tests/test_build_workflow.py tests/test_tests_workflow.py -q`
— 120 passed. Ruff check/format passed (562 files). Reviewed and integrated
workflow-only DEV-059 so branch-scoped hosted browser regression can run without
native release builds. No engine behavior changed.


## Training-policy composition correction

The fresh training-only pilot identified that standalone baseline-v10 does not
punt: the modern chart wrapper supplies its fourth-down preferences. The initial
v10 replacement was therefore insufficient. Interrupted this run before held-out
validation, preserved all files, and added failing regressions requiring actual
punt/punt-return consultations and restored replay (DATA-009).

The development runner now optionally composes unchanged baseline-v1 situational
offense/defense with baseline-v10 pending-decision preferences, selecting only
engine-provided public legal choices for either side. Legacy defaults stay intact.
This is an explicit training preference, not a new rule or a chart adjustment.
The separate chart-v10 assessment retains its recorded mixed-policy scope.

Focused composition/cumulative regression: 121 passed across generator, shared
local-season runner, issue tracker and workflow tests. Ruff check/format passed.
The required synthetic integration now asserts nonzero actual punt and punt-return
exposure; the composition-specific full game verifies midpoint/final replay.


## Source terms and private comparison review

Rechecked the current primary provider documentation. The SportsDataverse
[release-store README](https://github.com/sportsdataverse/sportsdataverse-data/blob/main/README.md)
advertises CC BY 4.0; its
[LICENSE](https://github.com/sportsdataverse/sportsdataverse-data/blob/main/LICENSE)
grants MIT software permissions. These are not a finding that all underlying
sports content or generated historical charts can be redistributed. The
[upstream ESPN/Disney terms](https://disneytermsofuse.com/english/) separately
restrict uses and transformations, including AI-related uses. No distribution or
commercial-use clearance is claimed; historical artifacts remain local under the
owner's existing private comparison direction. Public tools/tests are source-neutral
and synthetic. Any publication needs a separate rights decision.

The local reference diagnostic enumerates all 810 normalized addresses across all
four authorized 2007/2008 teams, with numeric ranges and semantic kinds retained
privately. Both generated pilot bundles load through the strict production codec
and have a private address-level comparison. This is a structural diagnostic, not
a cell-by-cell cloning objective or a claim that four examples define legal bounds.


## Clock-adapter boundary regression

Training-only pilot04 exposed excessive clock:spike selections from the new
development override (DATA-010). Its first interpretation as missing calls was
wrong: calls were present under the full clock:spike ID. Production plan_turn
adds implicit normal timing and side ownership; the override had bypassed both.
This is a harness defect, not a production engine defect. Interrupted the pilot
and incomplete full-coverage run, retained evidence, and added a failing full-game
regression forbidding clock:spike/Spike under this training policy. The override
now excludes clock_choice entirely; production timing remains authoritative.
No held-out seeds were consumed and no chart strengths were changed.

The corrected boundary passes eight fresh private smoke games with zero spikes,
zero failures and actual punt/return exposure. Play-volume diagnostics stay private.
The synthetic replay fixture uses long kickoff fields, realistic punt distances
and asymmetric gains to require punts while avoiding an artificial deterministic
endless overtime tie; assertions remain intact. All previous pilot artifacts are
retained and superseded, not represented as current fit evidence.


## Final pinned-engine private pilot

At `1f84e56`, final pilot 05 selected candidate 02 using 384 paired training games,
then passed all 12 predeclared efficiency/turnover/kick-return/PAT gates over 512
separate held-out games. All 896 games reconciled; four additional midpoint/final
replay checks and four mixed-policy coaching assessments passed. Each team has
512 held-out games, not an assumed NFL season length. Scoring and play-volume
diagnostics are retained privately. Field-goal accuracy remains a
distance/mix diagnostic rather than an unqualified source-fit claim.

Both final local bundles were regenerated from the recorded profile/source/seed
and tactical prior: all10 chart/provenance files are byte-identical to the selected
candidate. The ordinary terminal catalog lists both generated teams. Private
operator instructions and full four-reference address comparisons are saved beside
the bundles. Reference charts and public release allowlists remain unchanged.

Full Python gate at `1f84e56`:3,183 passed in858.35 seconds,92.06% branch-aware coverage.
This run preceded the final strict overtime-audit guards; the final tree needs a
renewed full gate. Browser startup remains sandbox-blocked locally (33 tests);
branch-hosted Tests is required before final milestone acceptance.

Independent M33 review added strict rejection of reversed overtime boundary order
and untied/incomplete regulation. Synthetic red tests reproduced two acceptance
errors and the late incomplete-clock rejection; the narrow reviewed guards from
0a89a68 are adapted without M33 engine changes. The series-order fixture now has
tied regulation and sufficient reports/periods so it exercises the intended guard.

Strict auditor commit `1a0e76d`: 40 local-season cases and 126 focused cumulative
cases pass; Ruff check/format pass. A private adapter feeds retained serialized
engine facts back to production `validate_game`: all 904 retained final-pilot game reports,
including 17 overtime games, pass without changing any original artifact. The
adapter states that omitted pending/final flags rely on the original passing
validation; new guards use retained clock/period/boundary facts directly. It proves
the `_play_one` AST, generation-module bytes and engine hash are unchanged from
calibration. A separate strict-auditor identity/hash is recorded rather than
rewriting the original report. Final-tree coverage at `1a0e76d` passes: 3,188 tests
in 825.10 seconds, 92.06% branch-aware coverage. Fresh Ruff check, format check
(563 files), `pip check` and `git diff --check` pass. Hosted browser verification
remains pending because the local Chromium sandbox cannot launch.


Final operator smoke checks: both generated team IDs list in the ordinary
catalog, and the real web backend creates games in both home/away orientations
with legal engine actions. The private `PLAYTEST.md` records terminal and browser
commands, pinned engine and interpretation limits. Source generation and game
simulation code remain unchanged during hosted verification.


## Acceptance and review boundary

Both phases satisfy the acceptance criteria on the pinned engine. Phase 1 creates
complete deterministic bundles with explicit provenance, coverage and fallbacks.
Phase 2 preserves the neutral baseline, records bounded profiles and paired seeds,
selects using training only, and validates once against a separate held-out domain.
The final pilot passes all 12 fixed held-out gates; all 904 retained games pass
strict reconciliation, with four save/replay checks and four separate coaching
assessments. Private probability audits cover both generated offense/defense
pairings. All ten regenerated team/provenance files match the selected candidate
byte for byte. Private final charts are ready for owner play testing.

Full hosted [Tests run 41572345677](https://github.com/rtulloh/bowl_bound/actions/runs/41572345677)
passes at `3c1bb9b39e70b7085dc296693d256b62832dac6b`:

- Python: 3,188 passed in 1,596.20 seconds; 92.05% branch-aware coverage.
- Ruff check, format check (563 files) and `pip check`: passed.
- Frontend: 128 passed; production build passed; npm audit found zero vulnerabilities.
- Real-engine Chromium browser regression: 33 passed in 5.2 minutes; no skips.

The local full run also passed 3,188 tests with 92.06% coverage. Local Chromium's
MachPort restriction remains accurately recorded; hosted results provide the
browser evidence. Hosted frontend logs retain the existing `whatwg-encoding`
deprecation, React `act(...)` warnings and duplicate synthetic fixture-key warning.
Parallel work tracks those warning findings as DEV-044 and DEV-064 in Milestone 23;
none was suppressed or silently counted as a clean warning-free run.

Final self-review checked source/seed/profile identity, production-engine reuse,
quantization and state audit boundaries, command examples, private output guards,
tracked history and unchanged runtime/package sample allowlists. No historical
charts, source rows, numerical reference audits, learned profiles or generated
historical bundles are tracked. The acceptance commit changes only operator and
milestone documentation; executable files are identical to the hosted green head.
Applicable documentation/tracker checks are rerun before that commit.

DATA-001 through DATA-010 are resolved at tested commits. They remain unclosed
because owner play-test confirmation has not occurred. Source-versus-official
statistical deltas, unobserved families/formations, sparse categories, fixed +0
turnover locations and modeled special-team behavior remain disclosed limitations.
This is a two-team mechanics study, not a historical-schedule reconstruction or
redistribution clearance. Renew calibration after reviewed Milestone 33 engine or
coaching changes are integrated. Stop here for parent/owner milestone review;
Milestone 35 implementation has not started.
