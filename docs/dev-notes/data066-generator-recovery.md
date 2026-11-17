# DATA-066 generator recovery for v1.1.0

Owner direction: recover the weekend's generator work, use Python 3.12, publish
the generator source and regenerate the 2002 evidence locally. Generator code is
public; historical source snapshots and detailed output remain ignored.

## Provenance and preservation

Recovered the producer and its fictional tests from the November 12 backup's
`data060-alpha-budget-policy` worktree. Verified the complete project archive's
SHA-256 as `5087a5d5cbc3e7dbaa1d2c0399e6f500d18e30ec5d60213a9ad6472e25907d57`
and each selected file against the backup file manifest before copying. Original
backup files and an ignored recovery receipt are preserved. No Git directory,
historical chart, private source narrative or cache was restored over the checkout.

The recovered allocator's compiled model matches the released 2007 identity
`a46aaf83…`. Its old one-off driver hardcodes private paths and the 116-team 2007
scope, so the public integration supplies an explicit candidate pipeline instead.
The original contract stays unchanged; the cohort extension has its own identity.

The current local-season runner has release changes absent from the recovered
research runner. Preserve the current runner and recover the older research
runner beside the producer. Rebind research imports to that runner. Refresh the
reviewed engine inventory against `e218fd9`, including the added `rules_summary`
module and current catalog/CSV changes. Inventory tests now require 40 engine
files / 39 loaded modules rather than 39 / 38; this strengthens the census for
the new module. Coaching remains the explicit Hard-v15 / baseline-v15 reference.

## Paydirt consultation

Reviewed local Paydirt `docs/chart-calibration.md`, especially the bounded
calibration cycle. Adapt frozen source/model/engine identities, preserved prior
candidates, whole-cohort checks and evidence receipts. Do not reuse NFL chart
semantics, calibration thresholds, private charts or a Paydirt runtime dependency.

For blocked-punt source semantics, also reviewed Paydirt
`paydirt/fumble_source.py:FumbleGainFacts` and `project_fumble_gain`, which separate
credited yards, physical initial movement, loose-ball travel and recovery advance.
Adapt this separation of facts to Bowl Bound's BK recovery suffix; do not reuse
NFL yardage rules, return rules, historical thresholds or any Paydirt dependency.

## Verification record

- Before recovery, restored generator tests failed collection because
  `tools.chartgen` was absent.
- Recovered runtime tests then rejected stale source attestations. After binding
  the recovered research runner and current engine inventory: 58 runtime identity
  and reference-execution tests passed.
- New candidate-pipeline tests first failed collection, then exposed unsupported
  Event hashing and the new identity's absence from the independent audit. The
  resulting 10-test suite passes, including deterministic ordinary-file loading,
  exact pins, run contrasts, depth finalization and input refusal.
- New core-source tests demonstrate missing-module failures, then missing TD/FG
  behavior, before the conservative adapter implementation. They cover unknown
  yardage/flags/possession, kick-versus-return distance, source checksum binding,
  explicit scoring evidence and corroborated interception spots.
- Fresh acquisition checked 913 listed 2002 games and found 506 with play rows.
  This is a new snapshot, not the missing 440-game snapshot in DATA-066.
  An initial normalization/generation run correctly refused entirely unknown
  interception locations. The failure and candidate are retained; no zero-depth
  substitute was introduced.
- Corroborated core field-position/return evidence recovered 529 of 1,088
  interception locations. The next attempt correctly rejected unknown primary
  fumble support. All 37,244 rush, 17,084 completion and 1,657 sack rows lack
  the required annotations; separately labeled recoveries do not directly encode
  their primary mechanism. No missing flag was converted to false. The older public
  2002 Parquet contains just one game's 193 rows.
- Existing released-chart audit passes for all 116 generated 2007 teams.
- DEV-086's staged frontend import failure reproduced unchanged, then the exact
  two-component allowlist fix passed all 61 release-package tests. Frontend unit
  tests: 197 passed; checkout production build passed.
- The isolated exact-manifest frontend also builds successfully; npm audit finds
  no vulnerabilities. Browser launch fails before assertions on a macOS
  `mach-register` denial, including an escalated retry. This remains a validation
  gap, not a passing browser gate.
- The packaging regression now allows exactly the public research-contract JSON
  in the wheel. The separate prohibition on roster JSON/source documents stays
  intact, and every other unexpected JSON file is still rejected.

Final cohort results, cumulative checks and publication status are recorded here
as they complete. DATA-066 remains open until the actual candidate qualifies;
recovering code alone does not satisfy its release acceptance criteria.

## ESPN enrichment follow-up

Revisited [the source investigation](college-play-by-play-sources-2026-11-02.md),
especially its source inventory and proposed game/play reconciliation. cfbfastR's
ESPN adapter uses the same upstream provider as the fresh core snapshot. The
separate NCAA feed proposed for narrative enrichment is documented from 2013,
so the note does not establish an NCAA bulk source for 2002. CFBD's documented
historical play availability is another lead, but its enriched passing/rushing
coverage must not be assumed to apply to 2002.

Probed the public individual-play, drive, site-summary and CDN play-by-play
responses. The representative individual play and drive repeat the recovery
record, rather than supplying an inline primary-fumble flag. The sampled 2002
box scores have empty team/player statistic arrays; one postseason summary has
drive records but retains the same separate-row representation. These are sample
observations, not proof that every companion endpoint is empty.

The retained 506-game core snapshot has 1,565 fumble-labeled rows. A diagnostic
join requires a unique preceding sequence within the same drive, identical clock
and period, identical possession team, and an explicitly matching rusher,
receiver or sacked quarterback name. It identifies 995 candidate primary/recovery
pairs: 680 rushes, 195 completions and 120 sacks. Remaining rows include 344 with
no unique predecessor, 106 clock disagreements, 69 other predecessor types and
51 unmatched carriers. Input array order alone is unsafe: a recovery can appear
before its preceding drive's punt in the global response.

The ignored diagnostic receipt is
`private-data/data066-source/companion-probe/fumble-pair-research.json`, SHA-256
`43b07fed17ea19efa6400c9b8629d57a8f07c232e7ea95bdf205af4a4431df69`.
These positive links are a parsing lead, not a qualified rate: they do not
establish negative fumble observations or complete game accounting. The prior
[OOB correction](college-chart-oob-evidence-audit.md) explicitly warns against
silently applying its narrative-incidence denominator to the fumble estimator.
No missing flag, denominator or production fumble interpretation changed during
this diagnostic. A tested adapter change must preserve unresolved rows and
establish defensible positive and negative support before regeneration.

The exploratory full-coverage run was interrupted before completion; its log is
retained as `private-data/data066-recovery/full-regression-2.log`. It is not a
passing cumulative gate. Focused verification and the browser gap above remain
separate evidence.

## Upstream fumble-flag investigation

Continued at owner direction because DATA-066 blocks v1.1.0. Before this
investigation, consulted local Paydirt `docs/chart-generator.md:420–474` on
ordered fumble evidence. Adapt explicit event association, immutable source
hashes and refusal to treat diagnostic completion as fit acceptance. Do not
reuse its NFL actor rules, coefficients, chart semantics or private source data.

Pinned and inspected these upstream implementations:

- [cfbfastR R cleaner](https://github.com/sportsdataverse/cfbfastR/blob/11f4413c9880e7a1110c3dc93a8dae9667285724/R/pbp_clean_pbp_dat.R#L38)
  derives `fumble_vec` from a case-insensitive fumble mention and otherwise
  writes zero. Its attribution helper unions that flag with a muff mention.
- [SportsDataverse Python producer](https://github.com/sportsdataverse/sportsdataverse-py/blob/39e9f0e77c2c8c4a8522352fedb866b566e834f0/sportsdataverse/cfb/cfb_pbp.py#L4851)
  likewise derives the flag from the row's text and otherwise writes false.
  The inspected primary classification handles inline run/pass/sack language;
  it does not establish a primary/recovery join for the separate 2002 format.
  Upstream regression tests for fumble rush/pass flags also use inline narratives.

This corrects an overly strong explanation given during recovery: the published
2007 generator received explicit processed true/false annotations, not independent
observations proving the absence of every fumble. Its known-annotation denominator
and provider-completeness limitation are separate facts. The retained published
source summary (92,427 known eligible snaps, one unknown) does not itself prove
official completeness or explain every upstream transformation.

As a reproducible comparison, downloaded the **current** 2007 ESPN-derived bulk
asset, SHA-256 `96fe9bc5fde591273be59f84639eda8fff74143ab99e22add5fbe0259b7530e5`:
131,598 rows / 707 games; 1,875 true, 129,604 false and 119 null `fumble_vec`
values. Every nonnull value agrees with the presence of the fumble substring in
that row's text. `fumble_or_muff` agrees with `fumble_vec` throughout this asset.
This current asset differs from the frozen source SHA-256 recorded for published
Bowl Bound charts; it is comparison evidence, not a replacement or reproduction
of that original source. Copies, pinned upstream code hashes and the query
receipt remain under ignored `companion-probe/upstream/`.

In contrast, none of the fresh 2002 snapshot's 37,244 Rush, 17,084 Pass Completion
or 1,657 Sack rows mentions a fumble inline. A row-local substring annotation
would classify every one of those rows negative while leaving recovery rows
outside those primary categories. Blindly copying that rule therefore does not
solve the 2002 primary-fumble problem.

### Reproducible separate-row diagnostic

Added public `scripts/audit_espn_fumbles.py` and synthetic controls, demonstrating
the absent-module failure before implementation. The diagnostic leaves source
and estimator behavior unchanged. It binds each raw play response's SHA-256 and
reports candidate links and every unresolved fumble row. It reproduces the
995-link result above, while explicitly reporting no established negative
observations and `release_qualified: false`. Duplicate play IDs reject; duplicate
predecessors and missing clocks cannot silently create a link.

```sh
.venv/bin/python -m pytest -q tests/test_audit_espn_fumbles.py
.venv/bin/python -m scripts.audit_espn_fumbles \
  --plays private-data/data066-source/plays \
  --output private-data/data066-source/companion-probe/fumble-audit-v1.json
```

### Independent official-gamebook control

Retrieved Ohio State's official [Indiana gamebook](https://s3.us-east-2.amazonaws.com/sidearm.nextgen.sites/ohiostatebuckeyes.com/documents/2023/6/30/2002-5-Indiana.pdf)
and corresponding [HTML record](https://ohiostatebuckeyes.com/news/2002/9/28/box-score-from-ohio-state-vs-indiana-51).
The PDF SHA-256 is
`20a203ff4fb06c7eeb81a6ba4c53c7f9f1a27b3a8afe3a502b0953ee6feb0f35`.
The retained official totals and detailed play log disagree with the provider's
fumble accounting and a matched primary gain. One standalone primary action is
also distinct from the preceding play. Event IDs, individual sequences, names
and values remain in the private control. This demonstrates a source-accounting
discrepancy, not just a missing flag. No historical text, PDF, player rows or
gamebook-derived chart is published.

### Additional source leads and remaining boundary

Owner supplied CFBD (2001 onward), ESPN legacy endpoints, school archives and
cfbstats historical CSVs (2005 onward). [CFBD's current availability](https://api.collegefootballdata.com/data-availability)
confirms raw plays from 2001 with game/field gaps, but team/player box scores
start in 2004. Its [plays endpoint](https://api.collegefootballdata.com/api/plays)
requires bearer authentication and supplies play type/text; the schema alone
does not promise independent fumble-negative observations. No CFBD credential
variable is present in this session; asked the owner for an existing configuration
location without requesting a key in chat. CFBD response quality and early-season
coverage remain untested here.

cfbstats' historical exports are a useful possible independent 2007 check; a 2005
start does not fill 2002. Neither a third-party mirror nor common ESPN ancestry
establishes completeness or independent corroboration. Official school gamebooks
are now a verified 2002 control, but one game is not season/cohort qualification.

The immediate source repair must distinguish inline versus separate recovery
representation, retain unmatched/contradictory evidence, and reconcile event
counts and primary gains before defining negatives. Do not silently default all
missing flags to false or fit a rate from matched positives alone. The recovered
generator model and published chart pins remain unchanged. DATA-066 stays open;
this investigation establishes the normalization and source-accounting work
needed, not a qualified 2002 release candidate.

### Investigation verification

Python 3.12 focused run: **62 passed in 10.31s**, no skips or warnings:

```sh
.venv/bin/python -m pytest -q tests/test_audit_espn_fumbles.py \
  tests/test_issue_tracker.py tests/test_priority_docs.py \
  tests/test_release_player_docs.py tests/chartgen/test_espn_core.py \
  tests/chartgen/test_acquire_source.py tests/chartgen/test_release_pipeline.py \
  tests/test_packaging.py
.venv/bin/python -m ruff check scripts/audit_espn_fumbles.py tests/test_audit_espn_fumbles.py
.venv/bin/python -m ruff format --check scripts/audit_espn_fumbles.py tests/test_audit_espn_fumbles.py
git diff --check
```

All listed static checks pass. The 12 diagnostic controls include an initially
failing acquisition-directory selection test before the CLI was taught to select
only `plays-*.json` among inventory/scoreboard responses. The original raw-play
directory and the public acquisition command's raw directory both reproduce
the same counts. Reports remain ignored. The subagent's cumulative source gate
was collected before these new diagnostic tests existed; it is still running,
and these 62 focused checks are separate evidence. No full-gate pass, publication
or release acceptance is claimed.

## Paydirt historical attribution fallback

Owner pointed out that Paydirt already implements a simpler historical fallback.
Consulted the local implementation at `paydirt/historical_fumble_proxy.py`, its
synthetic tests `tests/test_historical_fumble_assumptions.py` and
`tests/test_historical_fumble_assumptions_v2.py`, plus
`docs/dev-notes/historical-source-completion-boundary.md` and
`docs/chart-generation-workflow.md:332–340`. Local Paydirt HEAD was `cedf6117`;
these references were read, not executed or added as runtime dependencies.

`historical_fumble_class_proxy_v2` is the relevant pattern. Explicit actions and
reviewed classifications take precedence. If the class is missing but ownership
and an actor-bound primary gain are available, it models RB/FB as rushing, WR/TE
as receiving, a center as a rushing snap, and QB gains as snap/sack/rush according
to bounded gain ranges. Unknown positions have a disclosed gain-based proxy.
Source facts stay unchanged; a separate modeled class, assumed role and reason
record the inference. Its tests explicitly reject borrowing a recovery return as
the primary gain. These NFL proxy thresholds are design input, not an adopted
Bowl Bound rule or model setting.

The companion `historical_isolated_fumble_exclusions_v1` policy retains every
source event but uniformly omits unsupported fumble projections from fitting,
with full/fitted counts, individual reasons, source hashes and team impacts.
The documented Paydirt census fits 712 of 727 events, excludes 15 (2.063%), and
keeps historical completeness false. Source conflicts are not suppressed by
that exclusion policy. The useful adaptation is this separation of observed
facts, modeled attribution and disclosed fitting omissions; perfect historical
attribution is not a prerequisite to evaluating an explicitly modeled candidate.

A feasibility scan of the 570 unresolved 2002 rows found 557 explicitly named
fumblers and 157 with a unique preceding Rush/Pass Completion/Sack record.
Thirty-one of those predecessors name the same carrier but disagree on other
link evidence. None of the unresolved recovery narratives independently supplies
the scanned primary-action language. These are potential evidence for a bounded
model, not permission to treat every preceding play or recovery advance as the
primary gain. Counts and limitations are retained in ignored
`companion-probe/paydirt-fallback-feasibility.json`.

For Bowl Bound, evaluate a separate, versioned attribution policy after applying
unambiguous source links. Preserve known action/gain precedence, label modeled
classes, and report every unresolved or omitted record and each team's impact.
Assess the resulting fitting denominator and simulated fumble behavior before
release acceptance. The 570 unresolved source rows are 36.4% of this snapshot's
fumble rows, so Paydirt's small-omission result cannot be transferred here.
CFBD remains useful corroboration, but its credentials are not a prerequisite
for this local fallback evaluation. No Paydirt thresholds, source facts or NFL
runtime behavior have been copied into the Bowl Bound generator.

## Historical fallback experiment results

Owner authorized evaluating the fallback. Added the standalone development
experiment `scripts/experiment_espn_fumbles.py`; no production generator, engine,
allocator or release pins were changed for this experiment. Paydirt references
and adaptation decisions are recorded immediately above. Ten synthetic controls
first failed on the missing experiment module, then passed. They verify source
immutability, primary gain preservation, one recovery count, opt-in clock
relaxation, refusal of missing carrier/gain/owner/period evidence, the disclosed
denominator assumption and normalized identity validation.

The two views share an explicit modeled narrative-incidence denominator: ordinary
primary rows become fitting-only negatives unless they are identified ambiguous
predecessors. This is an additional modeling assumption, not newly established
source observations. It avoids estimating fumble rates from positive links alone.
Unresolved recovery rows stay in the immutable input and detailed ledger but are
omitted from fitting. The optional fallback requires the same explicitly named
carrier, existing primary action/gain, possession and period, allowing only clock
disagreement. No Paydirt NFL role/gain thresholds are imported. This evaluates the
useful separation of source facts, modeled attribution and fitting omissions; it
does not claim to reproduce Paydirt's entire class proxy.

Ran on the retained 99,968-event, 506-game snapshot and selected 55-team cohort:

```sh
.venv/bin/python -m scripts.experiment_espn_fumbles \
  --source private-data/data066-source-v2/normalized.json \
  --plays private-data/data066-source-v2/raw \
  --teams private-data/data066-source-v2/selected-teams.json \
  --output private-data/data066-fumble-experiment-v1 --generate
```

| Measurement | Strict links | Clock fallback |
| --- | ---: | ---: |
| Source-supported links | 995 | 995 |
| Additional modeled links | 0 | 31 |
| Unresolved recovery rows | 570 | 539 |
| Modeled negative primary rows | 69,048 | 69,048 |
| Primary rows retaining unknown fumble presence | 157 | 126 |
| Completed chart teams | 0 | 0 |

The fallback links 65.56% of the 1,565 recovery rows; 34.44% remain unresolved.
Of its 31 additional links, 23 belong to 18 selected teams (one or two additional
links per affected team). Per-team primary coverage is retained in the report.
Selected-team unweighted modeled fumble incidence ranges from 0.54% to 2.63%;
these are input-view diagnostics, not simulated chart rates or historical fit.

Both candidate attempts get beyond the earlier primary-fumble guard and stop at
`no known kickoff yardage evidence; supply individual-play source evidence`.
Neither completes its first team; this is not a full-cohort success or a survey
of all later blockers. No missing gross kickoff distance was replaced with a
return distance or zero. The next source task is to recover or explicitly model
gross kicking evidence, then rerun candidate generation and statistical checks.
The official-gamebook source-accounting disagreement remains recorded and
unresolved; fitting omissions do not clear that conflict.

Ignored `private-data/data066-fumble-experiment-v1/experiment.json` has SHA-256
`9318049841192b3232464fa9ace3dc99a9de87e6209ff8ec7746d40ca12dcf1e`.
Both attempt directories retain generation failure receipts. The experiment
checks every raw-response hash against the normalization receipt and verifies
the normalized source bytes remain unchanged. Source truth, historical fit and
publication authorization remain false/unverified. Its process exits zero when
the comparison report is written; each nested generation result separately
records failure. DATA-066 remains open.

Focused validation: 44 tests passed across the new experiment, existing fumble
diagnostic, issue tracker and documentation controls. Ruff lint/format and
`git diff --check` pass. The separate cumulative gate was collected before these
new controls and is still pending; no full-gate pass is claimed.

## Cross-drive special-teams fumble correction

Owner reviewed examples of the 344 missing-predecessor rows and identified punt
and kickoff return fumbles. The earlier label meant no predecessor under our
same-drive rule, not necessarily missing football action. Owner requested both
reclassification and inclusion in chart-generation logic.

For this phase, consulted Paydirt's `paydirt/nflverse_fumble_ledger.py:131–155`
and `paydirt/pfr_fumble_source.py:23–42`. Adapted the separation of punt/kickoff
return origins from primary rushing/receiving and its explicit actor/gain
provenance. Did not reuse NFL runtime behavior, assume recovery advance is
return distance, or infer a muff versus fumble after possession.

Added shared `tools/chartgen/espn_returns.py` linking logic used by the diagnostic
and production core normalizer. Only a recovery at sequence 1 qualifies. Its
immediately preceding numbered drive must have a unique final punt/kickoff return;
period, receiving team and end/start yard line must agree. A named returner must
match name and team abbreviation, with clock elapsed between zero and 30 seconds.
The 30-second limit is a disclosed conservative association bound, not a Bowl
Bound rule. An unnamed punt explicitly marked no return requires the same clock
and position. Response array order is ignored. Duplicate terminal records,
intervening snaps, penalties, backward clocks and conflicting evidence refuse.

Core adapter v2 folds the positive fumble/recovery facts into the kick event,
which supplies return-chart evidence with the receiving team as fumbler. The
retained recovery row is marked `no_play=True` solely to omit duplicate fitting
evidence. Narratives, raw optional observations, source hashes and unknown gross
or return distances are preserved. Bidirectional event-ID provenance records the
association. Version-1 snapshots remain readable; v2 receipts require the new
return-fumble policy. The experiment uses the same enrichment and has its own v2
identity. A production fitting guard rejects positive-only return-fumble support
when other eligible return rows remain unknown, preventing sparse positives from
becoming a 100% fumble rate. It does not invent negative observations.

Reaudit resolves **226 of the 344 rows**: **131 punt-return** and **95 kickoff-return**
fumbles across 166 games. Of these links, 205 have matching named returners and
21 use the same-clock no-return punt association. Observed elapsed time is at
most 18 seconds. There are still 118 missing-predecessor cases.

After retaining the separate 31-link primary clock fallback, the total unresolved
count falls from 539 to **313**:

| Remaining reason | Rows |
| --- | ---: |
| Missing predecessor under the supported rules | 118 |
| Clock disagreement plus other insufficient/conflicting evidence | 75 |
| Non-primary predecessor | 69 |
| Carrier unmatched | 51 |

These categories are first failed checks, not proof every row has only that
problem. Across the full 1,565 fumble rows there are 995 strict primary links,
31 modeled primary links, 226 modeled special-teams links and 313 unresolved.
The known official gamebook conflict is retained; association is not source
qualification. No release pins changed.

Reran the same experiment command above using output
`private-data/data066-fumble-experiment-v2`. Both fresh candidate attempts still
fail before completing a team with `no known kickoff yardage evidence; supply
individual-play source evidence`. This occurs before the new return-denominator
guard can be reached. Report SHA-256:
`bdd439a2ad1ed746c785dc1efeb72bb614144a4a8d1b3a2ecb28f1c30865872a`.
Standalone diagnostic receipt `companion-probe/fumble-audit-v2.json` SHA-256:
`aa6ce4fef9685a04cf0bb2da00cc6f165ce854863781e2a67b90f2754de305c8`.

Test-first evidence: the three new return-link cases failed against the unchanged
linker; the production normalization control failed with missing fumble projection.
Synthetic tests cover named punt/kickoff returns, unnamed no-return punts,
reordered responses, identity/time/period/position conflicts, duplicate terminal
records and intervening snaps. A normalized round trip and ordinary generator
test verify retained provenance and exactly one return fumble. No historical
source narrative or chart is included in public tests.

The wider focused run initially reported 145 passes and 11 failures because the
research runtime contract correctly rejected the changed `generate.py` and
`source.py` bytes. Updated exactly those two runtime source pins; engine files,
engine anchor and reference execution options remain unchanged. The revised
contract SHA-256 is
`977442509108f734e2f57ad46952b6742d43b16d61c7dd280f19a0ac9b45cdc1`.
Independent review then found a team-totals bug: kick ownership remains with the
kicking team while the return fumble belongs to the receiving team. Added failing
both-team totals assertions for kickoff, punt and muff examples, then corrected
`summarize_events` to use explicit fumbling ownership while excluding duplicate
no-play rows and tries. All three controls now report receiving team 1 fumble/1
lost and kicking team 0/0. Return fumbles do not become scrimmage fumbles. The
reviewer independently verified iterator input, legacy ownership fallback and
no-play/try exclusion, and reported no further issues.

This adds a third changed runtime pin, `evidence.py`. The final contract SHA-256
is `a14d734bbebf0e4c75fa326c8ad73fffd977ee153d7fdcbeaf292f12ffa3fd4c`;
all engine and runtime pins match. Final stable validation passes:

```sh
.venv/bin/python -m pytest -q tests/chartgen/test_source.py \
  tests/chartgen/test_espn_core.py tests/chartgen/test_acquire_source.py \
  tests/chartgen/test_release_pipeline.py tests/test_audit_espn_fumbles.py \
  tests/test_experiment_espn_fumbles.py tests/test_issue_tracker.py \
  tests/test_priority_docs.py tests/test_release_player_docs.py \
  tests/chartgen/test_generation.py::test_normalized_cross_drive_fumble_supplies_return_chart_evidence \
  tests/chartgen/test_current_runtime.py::test_current_identity_binds_all_source_files_and_loaded_module_subset
.venv/bin/python -m pytest -q tests/chartgen/test_generation.py -k 'fumble or physical_dice'
```

Results: 90 passed in the first run; 13 passed, 80 deselected by the explicit
focused filter in the second. No skips or warnings. Ruff lint/format and
`git diff --check` pass. Longer focused runs were interrupted or failed stale
attestation when source changed during review; they do not certify the final
tree. The stopped broad gate recorded 754 passes and four mid-run adapter source
mismatch failures, with no completed coverage report. Its log is retained.
Full release validation, including the previously blocked browser checks,
remains incomplete.


## Interception-return fumble correction

The owner identified another cross-drive recovery as an interception-return
fumble. The shared return linker now accepts a terminal `Pass Interception`
with an explicitly named interceptor matching the next drive's fumbler. All
existing name/team, unique final sequence, period, end/start spot and 30-second
checks still apply. Production normalization preserves the interception and
its return yards, attributes the fumble to the returning opponent, retains the
recovery evidence and excludes the duplicate fitting row. The original optional
observations are unchanged. Version-3 core receipts bind return policy v2;
version-1 and version-2 snapshots remain readable under their earlier policies.

The fresh experiment under `private-data/data066-fumble-experiment-v3` uses the
same source and team selection as v2. It links 20 additional interception-return
fumbles, alongside the unchanged 131 punt and 95 kickoff links. With the separate
31 modeled primary clock links, the accounting is 995 strict primary + 31 clock
fallback + 246 returns + **293 unresolved** = 1,565 recovery rows.

| Remaining first-failed check | Rows |
| --- | ---: |
| Missing predecessor | 98 |
| Clock disagreement plus insufficient/conflicting evidence | 75 |
| Non-primary predecessor | 69 |
| Carrier unmatched | 51 |

The report keeps special-teams and interception-return counts separate. Both
candidate generation attempts still stop before completing a team with
`no known kickoff yardage evidence; supply individual-play source evidence`.
Receipt SHA-256:
`00267b24e9d864358a8617d2a7b82dad70a16670adb6d1bc17ff25019d78de1c`.
No released chart pins or authored allocator parameters changed. The sack and
standalone rushing examples reviewed by the owner remain separate follow-up
cases; this return rule does not borrow their predecessor's gain.

New synthetic controls first failed for missing interception-return linking,
missing production ownership projection and incorrect special-teams reporting.
The implementation now passes those controls, including both-team totals,
idempotence, normalized round trips and old-receipt compatibility. The same
cumulative focused command recorded above, with `tests/test_acquire_rosters.py`
added, passes **132 tests**. An earlier run's only failure was the unregenerated
issue index after DATA-067 creation; regeneration corrected it. This is not a
completed full release gate. The updated reader source pin gives runtime contract
SHA-256 `055de651321f65f76f1c5577e1f63ceaeea6799f8a6e1d9e5afdf5af9e973f34`;
engine pins and reference execution settings remain unchanged.

## Release roster acquisition

The owner explicitly authorized release commentary rosters on 2026-11-16;
DATA-067 records that scope separately from chart qualification. The public
Python 3.12 acquirer validates page season/sport, explicit positions and ordinary
roster syntax, retaining raw HTML and hashes in ignored paths. The current
18-team HTML candidate receipt and its 36 exact candidate file pins are under
`private-data/rosters-2002-v3/`. A separately curated official Michigan State
PDF supplies 101 explicitly positioned names under
`private-data/rosters-2002-curated/seasons/2002/michigan-state/`; its 102 source
rows include one unmapped snapping role. These are 19 acquired candidates, with
36 selected teams still outstanding before agent contributions.

The 2007 bulk roster release contains 8,738 names across 186 teams but no usable
positions. Current/empty official roster pages and a misleading Rutgers baseball
PDF are rejected. Scanned football sources require reviewed extraction. Names
and explicit positions are the only proposed release content; original PDFs,
page images, biographies and detailed evidence remain private. No historical
roster is added to the public manifest at this stage.


## Same-clock primary continuation across drive boundaries

The owner-reviewed sack is now linked by the shared primary normalizer, with
strict clock/period/carrier agreement and matching end/start possession, yard
line, down and distance. Both actions must be unique at adjacent numbered drive
boundaries and the primary gain must be known. This adds 33 links: 19 rushes,
10 sacks and four completions. The shared fold retains source optional
observations and the recovery row, preserves the original gain and marks the
duplicate fitting row no-play. It is idempotent and does not infer nonfumbles.
Version-4 core receipts bind primary policy v1 and return policy v2; versions
1–3 remain readable. Only the reviewed `source.py` reader pin changes in the
runtime inventory. Contract SHA-256:
`c4df6ce43579e50f00f021d70e79cf53c39937683a64e76397f104e51b53290f`.

The v4 experiment has 1,028 strict primary links, 31 modeled clock links and
246 return links, leaving **260 unresolved** recoveries. The remaining first
failed checks are 65 missing predecessor, 75 clock disagreement, 69 non-primary
predecessor and 51 unmatched carrier. Both generation variants still fail
before completing any team at missing gross kickoff distances. No recovery
advance or unknown gain is converted to a primary gain. The two standalone
rushing interpretations remain retained for follow-up with unknown primary
length; source identities and the owner's four decisions are preserved in
`private-data/data066-rosters/owner-reviewed-fumble-cases.json`.

Receipt `private-data/data066-fumble-experiment-v4/experiment.json` SHA-256:
`ec1accc6052480fdb7ac9d4e234bf0e32d0bb24d062955aa2a5a4186fe44bb1a`.
Audit `private-data/data066-rosters/fumble-audit-v4.json` SHA-256:
`e95beaac080b0ebba0de04cf4ce382439fae5f2a27f269ed7e949b151e88e2a5`.
The positive diagnostic and production controls failed before implementation;
conflicting context/name/gain controls continue to reject links. Validation
passes 145 cumulative focused checks plus 13 generation checks (80 deselected
by the explicit fumble/physical-dice filter). The full release gate remains
separate and incomplete for this generator/roster work.

Additional roster acquisition adds Baylor (132 named players) to the 2002
curated staging, bringing the main staged 2002 count to 20. An initial 55-team
HTML pass for the corresponding 2007 release teams acquires 23 candidates,
all through the ordinary roster loader, with 46 candidate file pins. The
remaining 61 release teams are being checked separately. These remain private
candidates; source review, role gaps and exact release integration are pending.
Temporary Python CPU OCR succeeds on image-only PDFs after native Vision fails,
but OCR output is retained as review evidence rather than automatically promoted
to release roster data. No OCR package is a project/runtime dependency.


## Official gross kickoff distance pilot

The official Illinois–Arkansas State gamebook at
<https://fightingillini.com/news/2002/9/14/NCAA_Football> contains full StatCrew
play-by-play and explicit gross distances for all 12 kickoffs. A retained
one-event pilot supplies a uniquely corroborated, explicitly stated gross
distance through the existing source-adjudication workflow. The event sequence
and distances remain private; no model prior or return-to-gross inference is used.
The manifest binds the source snapshot, exact event digest and retained official
HTML. Only `yards` changes; source bytes and return yards remain unchanged.
The corrected normalized file round-trips successfully. Existing adjudication
regressions pass (17 tests).

The pilot lives under `private-data/data066-official-pbp-pilot/`; its normalized
SHA-256 is
`1f8bc0b963e2d98e778c491d8e32886deea29c0a2e877ab717ff220769cdddfb`.
Evidence HTML SHA-256:
`680fdda3e13097de35be360a514dbe97d84e419ed1a98ed51ec7c74fc661b4fa`.
Correction manifest SHA-256:
`34d5691c0db2704f5cbe00e6d72e1eef7c37d28e71bbbe578e7d492d361e2e76`.
Other kicks disagree with ESPN about clocks, returners or return lengths; the
pilot leaves these untouched. This demonstrates a source route, not sufficient
season coverage or a completed candidate. Further official gamebooks and
explicit conflict reconciliation are required.

The first official HTML pass now covers all 116 published 2007 teams: 65 roster
candidates load successfully and 51 source gaps remain. The combined ignored
inventory pins 130 files and exactly matches existing release team slugs.
Inventory SHA-256:
`2b9124066c6485164387e15078e597f9ec3e207a26dc26bd730ab1f51ada39d3`.
No historical roster enters the public manifest before review and chart readiness.

The subsequent Oregon State extraction from the official bowl-summary PDF adds
56 explicitly positioned names for the 2002 Insight Bowl and 89 for the 2007
bowl. These are partial-season bowl lists. Main staged coverage becomes 21/55
for 2002 and 66/116 for 2007, before the subagent's eight-team work. Combined
private inventory hashes are respectively
`7276e573a56153784d7f1fe0e8846f6b5e9b0d3825c19508d584673e234eeae9` and
`ac99c745583fa0b7e567e1b7af0ff11d42f35680de2478d2207f3a4c17e5f648`.

Official Illinois gamebook acquisition now covers 11/12 games and 115 explicit
gross kickoff records. The September 7 Southern Miss game survives at the named
score article even though its legacy statistics URL is missing. The October 3
Minnesota game remains box-summary-only. Inventory
`private-data/data066-official-illinois-2002/combined-inventory-v2.json` has SHA-256
`15ce5a30f55f7c5435a45e9aed7fb0f13fb35e5cd2e3ef361684f0e3a3ab505a`.
This is retained primary evidence, not an automatically joined or qualified
source snapshot. Known clock, returner and return-length disagreements must be
reconciled explicitly; only the previously documented one-event pilot is applied.

## Official standalone rushing-fumble adjudication

Virginia Tech's official Arkansas State gamebook
<https://stats.hokiesports.com/football/box/?5921> supplies the missing primary
gain for an owner-reviewed standalone fumble. The surrounding official sequence
identifies the primary action. Individual names, positions and gains remain in
the private pilot. The provider clock, recoverer and recovery spot conflict with
the official book; those disagreements remain recorded without rewriting source
text or assuming all provider facts agree. Only `kind`, `yards` and
`event_phase` change through the evidence-checked adjudicator. The ordinary
normalized writer/reader round-trips the corrected primary facts.

Retained pilot: `private-data/data066-official-fumble-pilot/receipt.json`.
Normalized SHA-256:
`12684ce6dce3df2c12cb66dfcf73540778d0e7812f178a2f1a573c73f5ef59dc`.
Official HTML SHA-256:
`4193264252acbece7d87b8bd2fc5ead13d8ae9166055ad94fd05c50807cd5e51`.
Manifest SHA-256:
`721685bb640e801bb817d201f1ea0f3fbe936991235a70aa04bde9c7652ed7af`.
The earlier automated 260-row unresolved count is not silently decremented:
this isolated adjudication still needs incorporation into the fresh combined
source and experiment. Another standalone primary gain remains unknown.
The VT gamebook and its Boston College counterpart (`?5983`) also contain gross
kickoff distances, extending the official-source route beyond Illinois.

The complete official Virginia Tech 2002 schedule acquisition retains all 14
gamebooks, containing 139 explicit gross kickoff records before reconciliation
or deduplication. Inventory `private-data/data066-official-vt-2002/inventory.json`
SHA-256: `675e3affb6d7a98f6b9da1e69918bb297429e2e217dd59c37f5e899e89b22a2b`.
No automatic ESPN joins or whole-season correction claims follow from this count.

Repository-wide Ruff lint and formatting checks pass (891 Python files).
Dependency validation reports no broken requirements, with an unwritable pip
cache warning. Under Node 24.22.1, all 197 frontend tests, the production build
and npm audit (zero vulnerabilities) pass. The first frontend test invocation
used the shell's Node 18 and failed at startup; the corrected Node invocation
supplies the reported results. The full Python coverage suite has been started
and its result remains pending; these checks do not establish full release
qualification or success of the separately running upstream CI.

Fresh normalization from the retained, hash-verified raw responses now applies
the version-4 adapter to all 506 games and 99,968 events. The two individually
verified kickoff/rushing corrections are combined through one evidence manifest,
with unchanged per-event digests checked against their isolated pilots. The
original source snapshot remains untouched. The corrected cohort round-trips
through the ordinary normalized reader and is staged at
`private-data/data066-source-v4-adjudicated/normalized.json`, SHA-256
`5c2da563421bfd3499ba2ba6d6d2103a1aa3e621b7dea65a0cf04a4a0e602d22`.
Its manifest SHA-256 is
`a385eabf65d348a0cfb841498f89bd90acf45412acc685bc49c1ec2a4be2afb5`.
This consolidates source corrections; it does not establish missing distances,
negative fumble observations, historical fit or release qualification. The
earlier experimental fitting view has not been rerun on this adjudicated input.

## Bounded official-kickoff reconciliation before shutdown, 2026-11-16

The owner allowed approximately 20 more minutes from 22:08 UTC before stopping
for shutdown. Revisited local Paydirt `docs/chart-calibration.md` (bounded
calibration cycle): freeze evidence, run a limited comparison and retain the
outcome. No NFL model, coefficients or private Paydirt data are reused.

A private evidence pilot checks all four quarters of each retained Virginia Tech
book, with the book SHA-256 verified against the acquisition inventory. It maps
official calendar dates to the retained ESPN scoreboards, then requires matching
game, period, exact following-drive clock, receiving team, full returner name,
return distance and receiving-side end spot. It accepts only a unique match and
fills only missing gross kickoff distance. It rejects penalties, named onside
kicks, absent named returns and conflicting source facts; no ordinal or fuzzy
clock join is used. Of 139 explicit kickoff records across 14 books:

- 29 match exactly across 11 games and eight kicking teams.
- 56 fail the unique exact-evidence match.
- 40 lack an explicit named return.
- 14 involve a penalty, onside kick or no-play text.

The existing two individually reviewed corrections are retained. A fresh
normalization from all 506 hash-verified raw games produces 99,968 events; the
existing public adjudicator applies the combined 31-correction manifest, and
ordinary normalized write/read comparison passes. There are now 30 known gross
kickoff observations, including the earlier Illinois correction. This selected
set emphasizes Virginia Tech and named returns; it is not representative league
coverage or a qualified season distribution. Clearing a minimum-data guard with
this pool would not establish historical fit.

Ignored reproducibility files:

- `private-data/data066-kickoff-pilot/analyze_vt.py` and `matching.json` retain
  exact matches and first-failed rejection reasons.
- `private-data/data066-kickoff-pilot/build_source.py` starts from retained raw
  bytes, not an already adjudicated source. Its exclusive-create output directory
  protects the completed run; choose a new private destination before repeating.
- `private-data/data066-kickoff-pilot/source/normalized.json` has SHA-256
  `5eacba86e472f65d23e83c878fad6e75ae688ef4869a59506677922c9bbb3305`.
- The combined manifest SHA-256 is
  `404f5084497bd8b5ac9af77c53a24d5cc55a59dbab8d8c8349553e0ba21991b5`.

The bounded rerun selects Virginia Tech while retaining the full input pool:

```sh
.venv/bin/python -m scripts.experiment_espn_fumbles \
  --source private-data/data066-kickoff-pilot/source/normalized.json \
  --plays private-data/data066-source-v2/raw \
  --teams private-data/data066-kickoff-pilot/source/teams-vt.json \
  --output private-data/data066-kickoff-pilot/generation-vt --generate
```

The experiment still labels modeled primary non-fumble observations separately
from source evidence. No authored allocation parameter, engine source, public
chart pin or released artifact changes in this pilot. The nested generation
result determines success or failure; the experiment command's exit code alone
does not. Results and the remaining stopping point follow when the run completes.

The eight-team roster acquisition is incorporated into an exact private
candidate inventory: **29/55** selected 2002 teams now load, with 26 acquisition
gaps. Inventory SHA-256:
`20b8382be0222f33668636c6b127c11de46471020fb008a2c57811f0b9b55106`.
The 2007 count remains **66/116**, with 50 gaps. Source/role review and exact
public release integration remain separate required steps under DATA-067.

Focused Python 3.12 source/adjudication/fumble/roster validation passes **212
tests**, with no skips or warnings. Command:

```sh
.venv/bin/python -m pytest tests/chartgen/test_adjudication.py \
  tests/chartgen/test_espn_core.py tests/chartgen/test_source.py \
  tests/chartgen/test_primary_fumbles.py tests/chartgen/test_evidence.py \
  tests/chartgen/test_optional_flag_receipts.py tests/test_acquire_rosters.py \
  tests/test_experiment_espn_fumbles.py tests/test_audit_espn_fumbles.py --no-cov -q
```

This focused run does not certify the full dirty generator integration. The
separate isolated DEV-086 fix at `a37190f` passed its full Python suite: 5,609
tests and 92.21% branch coverage; its upstream frontend/browser result remains
pending. The fix's receipt explicitly excludes DATA-066 validation.

### Completed pilot results and resume point

Both variants in `generation-vt/experiment.json` fail before any team completes
with `no known punt yardage evidence; supply individual-play source evidence`.
Its SHA-256 is
`c985ede4359b27a556759575cdbf1337b4814e31c1750b42e2f85d11a3e0380e`.
The kickoff guard is therefore cleared for this bounded input, without claiming
that its sparse gross-distance pool qualifies for release.

A separate exact punt-return pass checks 142 official rows with explicit
pre-punt down/distance/field position and gross yardage. One row uniquely matches
period, punter, returner, return distance, receiving-side end spot and the exact
pre-punt down/distance/field position. Fifty-one fail those match requirements,
71 have no explicit named return, and 19 involve a penalty, block or no-play.
Clock agreement is not asserted for this punt join. Its individually matched
gross distance is explicit in the book, not derived from return gain or a default.
The private `analyze_punts.py` verifies retained gamebook hashes and writes the
match/rejection ledger to `punt-matching.json`.

A second fresh normalization incorporates that additional observation through
the public adjudicator. It retains 32 corrections, 30 known gross kickoffs and
one known gross punt. Normalized reader round-trip passes. The separate snapshot
`private-data/data066-kickoff-pilot/source-with-punts/normalized.json` has SHA-256
`f3314e3ba033f377b12f1cd8e4c1600a898c8fc4e9938a9c7dd231b48ba462bc`;
its manifest SHA-256 is
`407bddb0b17cdd637e7ac2d9f78a15a88a8afb52c095b10ed22c283e033b5e4e`.
The build command adds `--include-punts --output
private-data/data066-kickoff-pilot/source-with-punts`; use a new destination for
another run. The normalized outputs are retained on disk and need no reacquisition.

The same generation command, substituting this second snapshot/team file and
output `private-data/data066-kickoff-pilot/generation-vt-with-punts`, finishes
both variants with **`no known BK location evidence`** and no completed teams.
Its experiment SHA-256 is
`2ba3a8ff1185a33b8988c7b5e7670ccbe241a743798df6e363bdf8eb5926866e`.
VT has two blocked punts and neither has known gross distance in this snapshot.
The ordinary-punt observation clears the generic punt guard; it supplies no
blocked-punt location. Known FG evidence is 23/23 and PAT outcomes are 53/53.

For the next reconciliation pass, retained review candidates identify two
blocked-punt games and official rows. One has explicit statistical punt credit
but disagreements about timing and recovery position; it is not applied here.
The other has a recovery location without explicit gross distance. Individual
sequence evidence remains private. Neither recovery advance nor an unknown
distance supplies an invented statistical zero.

A direct call to the existing return-fumble guard independently rejects VT's
punt-return sample: **3 annotated positives, 33 unknowns and zero explicit
negatives**, error `positive-only return fumble support; supply a qualified
denominator`. This is a direct guard check, not a claim that full generation
reached that later branch. Its receipt is `return-denominator-guard.json`.
VT kickoff and interception return samples also lack observed negatives. Their
absence of annotated positives does not establish historical zero-fumble rates.
No missing return flag was converted to observed false.

The automated link ledger remains 1,028 strict primary + 31 modeled clock + 246
return + 260 unresolved = 1,565. Correcting a standalone play's kind/gain does
not change the automated link count. Both new generation attempts preserve this
accounting and disclose 68,995 modeled primary negative rows separately.

Next work, in order:

1. Reconcile broader official gross-kick/punt evidence, including the two blocked
   punts and recorded provider disagreements. The 30-kickoff/one-punt pilot is a
   guard diagnostic, not a representative season distribution.
2. Evaluate and test a fitting-only return-fumble denominator policy, with the
   same explicit separation of modeled absence from observed source flags used
   by the primary experiment. Quantify unresolved recovery and selection bias;
   do not bypass the positive-only guard or mutate source flags.
3. Rerun the selected 55-team cohort, audit final ordinary files, contrast and
   numeric support, then perform source/statistical and real-engine validation.
   No new 2002 output has qualified or entered the release manifest.
4. Finish the 26 missing 2002 and 50 missing 2007 roster acquisitions, source/role
   review and exact release pins. Complete the shared full regression gate before
   committing/pushing the generator integration. Its source is prepared in public
   repository paths but remains uncommitted and unpublished at this checkpoint.

Additional focused checks pass: 13 generation controls (80 explicitly deselected),
one current-runtime source-inventory control, and 22 issue/documentation checks.
Together with the 212 source/roster checks, this is 248 passing focused checks,
no skips or warnings; it is not a full coverage gate. `git diff --check` passes.
The issue index is regenerated after the ticket updates. FLOW-007's requested
recommendation is in its local Markdown ticket; its status, priority and milestone
remain unchanged, and no feasibility spike was run.

## Resume after shutdown, 2026-11-16 evening

The saved working tree and all pinned private snapshots remain intact. The
upstream DEV-086 fix at `a37190f` completed the entire Tests workflow successfully
at 22:33 UTC, including Python/lint, frontend/build/audit, generated-chart audit
and real-engine browser regression. DEV-086 is resolved with that tested commit;
this does not validate the separate uncommitted generator integration.

Consulted local Paydirt `docs/chart-calibration.md:74–102` and
`paydirt/nflverse_fumble_ledger.py:131–155`. Adapt separation of primary and
return origins, nullable evidence, frozen source receipts and a bounded paired
experiment. Do not inherit NFL defaults, coefficients, rosters or runtime code.
The owner removed the earlier budget constraint; no prior sample-budget rule is
introduced as a new restriction on this session.

Fifteen synthetic controls first fail against the unchanged experiment: missing
return-model option, an interception incorrectly receiving a primary non-fumble
flag, and a verified standalone primary fumble being omitted as a recovery row.
Experiment policy v5 adds opt-in return narrative-incidence negatives, separately
reported from the primary denominator. Possible predecessors of unresolved
recoveries stay unknown. Missing ordering protects all returns in the period,
or the game when the period is unavailable. A further missing-normalized-origin
control first exposed an overly narrow ambiguity scope; it now protects that
scope too. Existing positive/negative annotations remain intact.

The standalone primary correction is retained for fitting instead of receiving
`no_play=True`. This changes fitting inclusion, not the automatic link ledger;
its unresolved association remains visible. Removing interceptions from the
primary negative model fixes the earlier conflation of a throwing play's fumble
absence and an interceptor's return fumble. The new option alone models return
absence. All 32 experiment controls pass; cumulative experiment/diagnostic/core
checks pass 89 tests. No engine or authored allocator source changed.

An official gamebook explicitly supplies one missing statistical blocked-punt
distance, with a named recoverer corroborated across sources. A manual one-event
correction fills only that fact, retaining clock, end-spot and omitted-play
disagreements. Individual names, sequence and values remain private; no distance
is inferred from recovery advance. Fresh raw normalization combines 33
corrections and round-trips 99,968 events across 506 games. Its 30 known kickoffs
and two punts still represent a sparse diagnostic pool.

Private snapshot:
`private-data/data066-kickoff-pilot/source-with-blocked-punt/normalized.json`.
SHA-256: `49d654ffbfc6fbf0d30f9bb5c67202c924d675eac422cfb633f4a9afd3ab2953`.
Manifest SHA-256:
`dd8093fd28d1146edf74cb644f83cb8ff99e4023c3dfa14e09f46451a7e40aa5`.
The opt-in VT rerun writes separately to
`private-data/data066-resumed-vt-return-model/`; its measured outcome follows.

Both VT variants complete generation and ordinary-file, budget and contrast
checks. Their fitting views retain one standalone primary, model 67,927 primary
and 6,747 return negative rows, and retain 291 strict / 260 clock-fallback
unresolved associations. This establishes a working pipeline, not source truth.

## Physical blocked-punt locations and full candidate, 2026-11-16

The first whole-cohort baseline preflight completes 19/55 teams. All 36 failures
stop at missing BK locations. Inspection confirms that the engine consumes the
suffix as physical distance before recovery; statistical punting credit cannot
locate that point. The released 2007 files contain 136 `BK 0` cells, whose
event-level accuracy remains a separate review under DATA-068. Existing released
bytes and their approvals are not rewritten.

`Event.blocked_kick_yards` now stores physical initial movement separately from
`yards`. Normalized schema 6 retains it, while old checksummed schemas upgrade
with this fact unknown. Narrative parsing requires a distance and field destination
without a separate recovery clause. A bare zero-credit statement or conflicting
recovery clause stays unknown. A source-bound adjudication can supply an explicit
official initial recovery spot without changing statistical credit or later
advance. Synthetic controls demonstrate 15 initial failures, three missing
pooling behaviors and two ambiguous-narrative failures before their respective
changes. Genuine explicit physical zero, negative and positive movement remain
valid.

Location fitting now follows the existing team-then-league pattern used for
other rare locations: use known own blocked-punt movements, otherwise known
blocked-punt movements in the supplied live league source. Each team's own block
rate stays unchanged. Ordinary punt distances, statistical zeros and recovery
advances never populate this pool. Receipts expose the method and known/unknown/
modeled sample counts. Missing evidence in the entire blocked-punt pool still
fails; individual unknown source rows remain unknown.

The expanded official-source snapshot contains 44 checked corrections, including
eight further ordinary gross punt distances and four known physical blocked-punt
locations across three teams. All eight ordinary-punt return-gain disagreements
remain visible and unchanged. The physical-location corrections use explicit
gamebook scrimmage/recovery points. Mirrored provider terminal metadata and a
named-recoverer disagreement are preserved as conflicts, not corroboration.
The initial private build's assertion caught the mirrored-coordinate discrepancy;
its failed output/log is retained, and the next build round-trips successfully.
Schema-only rebasing of old adjudication hashes first verifies every original
event differs solely by the new null field; original manifests remain intact.

Source: `private-data/data066-source-v6-physical-v2/normalized.json`.
SHA-256: `1dac3850a0cc864567e601b0dbdf89ca324f02ed0bda6632c4566cc23ef281b4`.
Adjudication manifest SHA-256:
`1de0c570c0e82705bf5962bfdc2a15606ffb5ade3f100f8e1f3eff8b20a34612`.
It retains 506 games / 99,968 events, 30 known gross kickoffs and ten gross punts.
These small, selected distance pools are not representative season distributions.

All **55/55** selected teams now pass baseline generation and the full candidate
pipeline under the modeled-clock/return-denominator fitting view. Candidate v3
retains 275 final files and 275 baseline files with exact pins, and passes final
ordinary loading, budget, contrast and catalog checks:
`private-data/data066-all-team-preflight-v3/candidate/generation-receipt.json`.
Its input semantic identity is
`bf086ff5b158e809d671fe011e8119510d8d4e450238be689980f138f813d7b2`.
Location methods are 18 teams without observed blocks, three using own physical
evidence and 34 explicitly pooling league evidence. Across selected teams, four
own block locations are known and 65 remain unknown. The 260 unresolved fumble
associations, source coverage, denominator assumptions and sparse pool selection
still require independent review. No 2002 candidate has release approval.

The final conservative narrative guard is rechecked against the same frozen
source in candidate v4; the generator/engine receives the same normalized facts.
The generator is now `college-chartgen-v9`. Research attestation preserves the
engine/coaching inventory and changes only the three modified source-module byte
identities, with final contract
`7a4988db3f13bf39623dfdf28fbcd633c14ed00acff9d31ccf727c669dd9fa9a`.
The parent allocator identity is unchanged. Interim research receipts remain
distinct and do not attest the final source tree.

Validation before the final narrative guard passes 228 focused tests, Ruff,
formatting, packaging/index checks, and the existing 116-team release audit.
Frontend validation earlier in this resumed work passes 197 tests, production
build and a zero-vulnerability dependency audit; frontend source is unchanged.
Full shared Python coverage was interrupted before production source changed;
112 tests passed in that incomplete run. A later cumulative run was also stopped
before changing the pooling policy (84 passed). Neither is a full regression
receipt. The initial cumulative 11 attestation failures were expected stale
source-identity refusals, fixed by reviewing and refreshing only changed module
pins, not bypassing verification. Final focused receipts follow below.

Next: independent source/coverage and statistical review, source-linked handling
of remaining recoveries, broader gross/blocked-distance evidence, real-engine
panels, the remaining 26/50 roster candidates and roster review, then exact
release qualification. Generator-source publication can proceed separately after
the established full regression gate; it need not wait for historical data to be
cleared. The public-path integration remains uncommitted/unpublished at this
checkpoint. FLOW-007's local recommendation is complete; its exploratory spike
is not current release scope. DEV-086's upstream workflow is confirmed green.

## Final verification and stopping point, 2026-11-16 evening

The final source tree passes **315 focused tests**, including normalization,
adjudication, blocked-location pooling, runtime attestation, full synthetic export,
fumble experiments, roster acquisition, packaging/index and engine special-teams
regressions. No skips or warnings appear in that run. Exact command receipt:
`private-data/data066-recovery/full-cohort-validation-receipt.json`; output:
`private-data/data066-recovery/physical-final-focused-v2.log` (Python 3.12.8,
`--no-cov`; this is not the full coverage gate). The issue tracker check passes
another 18 tests after the final documentation changes. Ruff check, formatting
(893 files) and `git diff --check` pass. The earlier dependency check reported no
broken requirements and an unwritable pip-cache warning. The previously recorded
local browser-launch limitation remains a gap; upstream browser CI is green.

Final candidate:
`private-data/data066-all-team-preflight-v4/candidate/`.
Independent verification:
`private-data/data066-all-team-preflight-v4/candidate-verification.json`.
All **550** baseline/final file pins match, the final ordinary loader and semantic
identities pass for all 55 teams, and both baseline and final pins are identical
to the preceding complete generation. The retained generation receipt itself
also repeats exactly, SHA-256
`9bd679723e64e117c46b47d9b4cc4a9412ac6bd9c9ea7cf3a81dd01d9849d1e3`.
Publication authorization, source qualification and the full regression gate
remain explicitly false in the verification receipt.

The verified shutdown backup is
`private-data/data066-recovery/checkpoint-20261116-full-cohort/`:
tracked patch, byte-checked archive of all nonignored untracked public files,
base commit, working-tree status and key private artifact hashes. It supplements
the earlier shutdown checkpoint without overwriting it. Original source snapshots,
roster candidates and all intermediate evidence remain in their ignored paths.
All local commands have completed; shutdown requires no surviving generator job.

## Continued release qualification, 2026-11-16

Owner directs continued work until a season is releasable. The final Python
source tree remains frozen while the full coverage regression runs. A fresh
72-test browser run and the required escalated retry both fail before any
application assertion: Chromium aborts at macOS `bootstrap_check_in` with
MachPortRendezvous permission denied (1100). This is a retained host validation
gap, not a passing browser check; upstream CI's previously green browser job
covers the upstream fix, not the dirty generator integration.

Private positional-roster recovery now covers 39/55 selected 2002 teams and
67/116 published 2007 teams. See DATA-067 for source limits and exact inventory
pins. Reviewed local Paydirt DATA-049 again for this phase; adapt narration-only
season-correct names and packaged commentary validation, while deliberately
retaining Bowl Bound's exact allowlist instead of copying whole season trees.

Started a frozen-candidate complete-game mechanics panel over all 55 selected
2002 teams, using the reviewed current reference coaching configuration,
deterministic seeds, balanced home/away exposure, midpoint save/load and final
journal replay. Its 55 scheduled games are a mechanics panel, not historical
schedule calibration or a claim of source accuracy. Results will be recorded
when the actual run completes; no measurements or passing result are assumed.

## Continued season qualification, 2026-11-16

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md` again for this phase.
Adapt its season-specific names/positions, ordinary loader checks, private
historical verification and actual packaged CLI/API commentary review. Do not
reuse its whole-directory roster packaging: Bowl Bound needs exact file pins.
Rosters remain narration only and must not alter chart results or RNG.

All 55 selected 2002 teams now have private roster candidates. The v5 inventory
`private-data/data066-rosters/rosters-2002-candidate-inventory-v5.json` pins 110
files across retained source roots; SHA-256
`d013d2de3bee3f3e87b1e2c30d5552d38007847e66af8336cbddeeee28065574`.
Partial lineups and spring/bowl coverage are explicitly identified; ambiguous
positions remain unmapped and missing roles stay generic. Third-party mirror
sources remain identified for final corroboration. The 2007 inventory remains
67/116 and must not be described as complete. Rejected evidence includes a
Rutgers baseball guide and a mixed-season Oklahoma roster archive page.

`private-data/data066-game-panel-v1/` retains 55 complete current-engine games
against the byte-frozen v4 candidate, balanced at two games per team. All pass
score/state/timing/statistics reconciliation and checkpoint/final strict replay.
This is a mechanics panel, not historical-schedule or historical-fit validation;
coaching mix and per-team source-fit effects still require review. New chart
inputs require renewed panel evidence.

The fresh expanded kick snapshot under
`private-data/data066-source-v6-kicks-v3/` contains 99 corrections (56 kickoff,
39 punt, four physical blocked-punt locations). Its normalized SHA-256 is
`ab7dd283c6536d14e5ed1e52c3b6d06ca8aed8b64bf8d49d46440a4dbb3f1b09`.
The adjudication manifest is
`edd005e852a6bd319c7ad006d300dcea71243761592abf73c0c5e3f13814592d`.
Independent verification confirms exactly 55 new distance facts and four
location-evidence manifest-reference refreshes, with other event facts unchanged.
The private build helper's initial post-write audit incorrectly expected an
unused evidence field; that audit was corrected and the existing output was
independently verified. The source was not silently rewritten to pass it.

The new kickoff touchback joins require unique game/period/exact clock/receiver
and agreement on official terminal spot, next primary snap and provider spot.
Unreturned punt joins require unique named punter, game/period, down/distance,
scrimmage/terminal position, receiver and next primary snap; retained clock
conflicts are not claimed as matches. Both require explicit official gross
lengths and reject ambiguous/penalty/blocked/recovery rows. Unknown return
lengths stay unknown. Source evidence is still sparse and concentrated; more
facts do not independently qualify league distributions.

Current commands (Python 3.12):

```sh
env PYTHONPATH=. .venv/bin/python private-data/data066-preflight-all.py \
  --source private-data/data066-source-v6-kicks-v3/normalized.json \
  --output private-data/data066-all-team-preflight-v5 --generate-ready
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
```

The second command's log is
`private-data/data066-recovery/full-regression-final-tree.log`. Preserve the
running gate; do not confuse partial progress with a passing receipt. Local
Chromium fails before app assertions with macOS Mach-port bootstrap permission
denial, also on the escalated retry. Keep this gap explicit until an actual
supported-runner browser check passes. Frontend 197 tests, production build,
zero npm vulnerabilities and Python dependency consistency have already passed.

## Exact multi-season package qualification follow-up, 2026-11-16

The final expanded-source generation completes all 55 selected teams. An exact
private staging helper copies 275 chart/provenance files and 110 reviewed roster
candidate files into `private-data/data066-season-candidate-v1/`, without copying
a seasons directory. Its staging receipt SHA-256 is
`b399c53110876f250d70625374ec5334231f1edb3f8f6a950c8fdd435b59f3d8`.
A renewed 55-game mechanics panel loads these roster bytes as well as the charts.
No new data entered the public manifest.

Reviewed Paydirt `paydirt/packaging.py` and
`tests/test_release_chart_packaging.py` before this follow-up. Adapt its explicit
preservation of existing released seasons and installed source notices. Do not
reuse broad season-directory copying or NFL runtime behavior.

Two missing packaging capabilities are being developed in the isolated ignored
copy `private-data/data066-package-work/` while the original integration coverage
gate runs: exact hash-pinned roster/provenance pairs for already selected generated
teams, and a versioned season envelope retaining each cohort's existing model,
source/OOB and conditional-depth qualification. Synthetic positive controls first
fail on the unchanged packager/auditor. Negative controls cover stale source pins,
missing/overlapping seasons, nested/unknown contracts, changed chart semantics,
unselected/wrong-team/wrong-year roster files, malformed/empty rosters and changed
bytes. The existing 2007 qualification must remain intact inside its own cohort;
it must not be relabeled as a 2002-source review.

A private raw-adapter/adjudication replay and per-team source/OOB review is also
being recomputed against the final snapshot. Consistency verification is not
provider truth or historical-fit certification. Publication rights and exact
release inclusion remain separate from passing technical checks.

## Final source review and exact package candidate, 2026-11-16

Replayed the current conservative normalizer against all 506 retained game-response
hashes, reapplied the 99 event-bound adjudications and reproduced all 99,968
normalized events and their source metadata. This establishes adapter consistency
against retained bytes, not independent provider truth. All 550 final/baseline
file pins, all 55 semantic identities and the independent budget checks pass.
Provider inventory coverage is 11–14 games per selected team; this does not imply
complete play metadata. All 70,887 selected source events retain unknown OOB
status. No qualifying designed-call/catch-depth observations were found, so the
conditional depth shapes remain explicitly authored assumptions.

Private source review:
`private-data/data066-final-source-review-v2/source-review.json`,
SHA-256 `1b06a4d17152bd143d6b38f8ad622c60b88e09c88a0fe53961c554ba2cb6689e`.
OOB review SHA-256:
`c259a8d8e525b5b9eb0cb60229b82598fff9164089be074e060a751a4476682f`.
Generation and these reviews leave historical fit unverified.

The combined private review package builds its real production frontend and
passes the staged audit for 171 generated teams: the new 55-team 2002 candidate
plus the unchanged 116-team 2007 cohort. With the two fictional samples the normal
catalog contains 173 teams. Its exact roster map selects 110 files, paired
`roster.json` and `roster-sources.md` for the 55 new teams. No source archives,
narratives, PDF imports, logos or detailed audit/game logs enter the runtime.
The unpublished review archive SHA-256 is
`79acbecdc00fac4e2158fd4a9cce69a06a320ae4db8a21cf706000c2f6cb3102`;
runtime manifest SHA-256 is
`e71d277840a474954deef9387d52131fdfb2f4833e436cccaf1ce4ed0eb0f3b6`.
This is a local review artifact using the current version metadata, not a
published v1.1.0 asset or redistribution clearance. Frontend build passes;
npm reports zero vulnerabilities and the existing whatwg-encoding deprecation.

The isolated packaging extension first fails synthetic positive controls against
the unchanged implementation, then passes 155 packaging/audit regressions. It
accepts exact roster pairs only for selected complete generated-team bundles.
Its version-four audit envelope partitions qualification by shipped season,
preserving each cohort's model, baseline and source-review identities. Missing,
overlapping, stale or nested cohort contracts fail closed. These implementation
changes remain in `private-data/data066-package-work` while the main full
coverage gate runs against frozen production/test inputs.

Normal API and CLI checks import the assembled runtime itself, cover all 55 new
teams and find names in commentary. Repeated reads and roster loading preserve
commands, rolls, RNG state and state digest; generic and named games have equal
semantic reports, and API/CLI save/load reproduces narration. Missing positions
retain generic wording. Receipt:
`private-data/data066-packaged-roster-check-v1/receipt.json`.

The first attempted roster-loaded game panel (v2) used a private setup hook.
Although its games completed, final runtime attestation correctly rejected that
replaced callable; there is no qualifying v2 summary. The replacement v3 uses
the unchanged canonical runner and passes all 55 games with checkpoint and final
replay verification. It does not load rosters; the ordinary application checks
above cover that separate presentation path. The panel independently reconciles
scoring, clock, state, statistics and structured traces. Its measured rush mean
is 3.511 yards per non-sack rush, which requires the larger source-matched review
before any fit claim. No historical-accuracy certification follows from these
mechanical checks.

A separate actual-matchup panel covers the 251 2002 fixtures for which both
participants are selected, not every team's full historical schedule. Its
private v1 driver incorrectly labels postseason games `bowl`; the engine
accepts `postseason`. A new explicit continuation contract will retain only
verified regular-game results and execute those postseason fixtures correctly.
This private driver correction does not change engine behavior or source facts.
The main full Python coverage gate and browser gate remain outstanding; this
host rejects browser startup before application assertions.

## Browser retry limit and actual matchup review, 2026-11-16

The owner reports browser launch attempts are producing dialogs requiring
dismissal. Stop local browser probes on this Mac. Chromium, installed Chrome,
macOS launch-services and the separate pinned WebKit startup attempts have all
failed before application assertions; their child processes have exited. Owner
permission to run Playwright is established, but permission has not solved this
host failure. Preserve the browser validation gap and use a working validation
environment when available; do not keep triggering dialogs or waive the gate.

The explicit v2 actual-matchup continuation preserves the 238 individually
verified regular games and executes the 13 postseason fixtures with supported
`postseason` configuration. All 251 pass with checkpoint/final replays. Review
covers 47,026 supported completed engine reports, 46,896 timing entries, nine
overtime games, period-score reconciliation, legal choices and zero coaching
fallbacks. Across 1,214 repeated offense/defense context buckets with at least
eight choices, the largest observed single-choice share is 62.5% (eight choices);
this is a descriptive repetition review, not a newly invented threshold.

Independent matched-source review finds pooled non-sack rushing at 3.564 versus
4.502 source yards per attempt, outside the existing experimental 0.5-yard
reference tolerance. Equal-team means show the same direction. Completion,
interception, sack, passing yardage, fumble, known kick/return distance and PAT
comparisons stay inside their existing cohort-level reference tolerances.
This does not establish per-team precision or cure sparse kick exposure. Rushing
bias is under investigation; no fit gate is relaxed. The net raw-result versus
statistical-credit difference is about 0.181 yards per simulated rush and includes
both field clipping and recovery advances. Source facts, rules and the allocator remain
unchanged. Private review: `private-data/data066-final-game-review-v1/review.json`.

## Rushing decomposition and remaining roster review, 2026-11-16

Read-only review of the 251-game panel separates fixed engine calls from ordinary
chart draws. Of 19,454 non-sack rushes, 2,324 are QB Sneaks, averaging 0.880
credited yards; another 137 are kneels at minus two. Across all rushes, the
raw engine result averages 3.746 versus 3.564 credited yards. Neither
discarding fixed calls nor replacing credited yards with unbounded results is a
valid way to relabel the inclusive historical comparison a pass: the supplied
2002 designed-call mixture is unknown.

A subsequent reconciliation corrects the initial attribution of that entire net
difference to clipping. All 18,799 non-fumble rushes match the exact field-limit
formula, with 593 clipped results reducing credit by 4,015 yards. The 655
recovery-chain rushes are separate: 26 have different raw/credited yards, with a
net additional 486 credited yards; 22 do not equal a simple clip of the initial
result. Recovery advances must not be called clipping or zeroed. The resulting
whole-panel net difference is 3,529 yards. This is an accounting decomposition,
not a historical fit pass or a new engine/statistics defect. Exact frozen-game
pins and checks are retained in
`private-data/data066-rushing-credit-review-v1/receipt.json`.

The 16,679 ordinary numeric primary pairs have mean offense draws of 4.587 and
defensive modifications of minus 0.336, giving 4.252 before field limits and
4.011 credited yards. Their exposure-weighted conditional source/encoded means
are 4.675/4.451. These conditional diagnostics exclude pending, fumble and fixed
play mechanisms; they are not source yards per rushing attempt and are not
additive causal corrections to the whole-panel discrepancy. No generator or
engine coefficient was changed on their basis. Private diagnostic SHA-256:
`e73e246cec654d0c0e354260c35d0dc76d75c1e93fa18e4f2de7ad12ec7a2bcd`.

The existing [published-chart diagnostic](../generated-charts.md#retained-alpha-8-source-fit-diagnostic)
already retains a similar failed rushing assessment (3.791 versus 4.773) and
explicitly distinguishes experimental gameplay charts from historically
calibrated charts. This is useful comparison evidence, not approval to waive the
new cohort's discrepancy or extend the 2007 distribution grant. Exact probability,
identity, state, replay and packaging checks remain required.

Official Oklahoma State alphabetical roster rows corroborate all 99 selected
names and mapped positions. Kansas State's official preseason numerical roster
corroborates all 48 selected names; one player is WR there but DB on the dated
November depth chart, whose later explicit position is preserved. Returner roles
continue to rely on the explicit depth chart. These checks change source notes,
not either team's roster JSON.

For Ole Miss, a separately retained school-produced 2002 bowl depth chart
supports a bounded 54-name roster, including explicit KR/PR memberships.
Two dated school notes additionally support a running-back role and a defensive
lineman's spelling/role. A spelling variant and an anomalous second TE row are
disclosed; the latter supplies no TE role. The selected
partial roster replaces the mirror-only 137-name preseason candidate, which is
preserved unchanged privately. It is not presented as a complete season or
bowl-availability roster. The linked legacy school PDF currently fails; the
retained document is identified truthfully as a school-produced PDF from a mirror.

All earlier candidates and pins remain intact. The updated 55-team roster
inventory is `private-data/data066-rosters/rosters-2002-candidate-inventory-v6.json`,
SHA-256 `84d52ce2ee5b5bca43250f30762e5075b52005b6ddae8be165ad6778a6ad6434`.
The updated exact package is `private-data/data066-full-release-review-v2/`;
its archive SHA-256 is
`c4c5bdf8d6693362b2d2e5a8d5b79dbc3199b987cd0b82fb2a8f1a8cd41e0472`.
The runtime manifest SHA-256 is
`e7c2a783f8e2f6028b307a07dc1ee76aa4a1ec3fb0bb97e0767968323c1c703f`.
It preserves all 2007 chart pins, passes the 171-generated-team chart audit and
fresh production frontend build, and discovers all 173 catalog entries. All 55
updated roster pairs again pass normal packaged API/CLI commentary, save/load
and RNG-equivalence checks; receipt:
`private-data/data066-packaged-roster-check-v2/receipt.json`.

The separate staging/audit extension has 155 focused checks and 88 native-build,
notice, archive, version and workflow regressions passing. These are unit and
staged-runtime checks, not a newly frozen native build or a browser pass. That
extension still awaits integration into the maintained tree after the running
full Python gate. The initial restaging attempt used the wrong working directory
for relative roster roots and failed before creating the combined package; its
partial private season staging and failure log are retained. The successful new
season staging is `private-data/data066-season-candidate-v3/`, receipt SHA-256
`19d903aa0ea6a985bfa98c3f3417f32cadadbf86e2066af6c71dc1817e665698`.
No chart or engine behavior changed. Source facts/positions remain private;
no source layouts, narratives or newly selected historical files are public.


## Native roster archive regression, 2026-11-16

Review of the final native path found a guard still limited to the two fictional
sample roster paths. Three synthetic positive controls reproduced rejection on
macOS ARM64, macOS x86_64 and Windows x64 before implementation. The isolated
packaging prototype now accepts only canonical season/team roster paths present
in the already verified assembled inventory; unchanged resource hashes remain
mandatory. Five negative controls cover other teams, other years, files outside
the resource tree and changed roster/source-note bytes. Archive extraction and
Windows installer file lists preserve the exact pair. Four further controls
reproduced unselected source-note leakage outside the resource tree; both roster
filenames now require the exact canonical, verified resource selection. All 255 combined
packaging, chart-audit, native-notice, archive and workflow regressions pass;
lint and formatting pass. An intermediate missing-comma edit failed collection
before validation, was corrected, and the final complete focused run passed in
29.19 seconds. These synthetic checks do not claim an actual native
build or platform play-test.

Paydirt references rechecked for this packaging phase:
`scripts/stage_chart_sources.py` and
`tests/test_chart_source_bundle.py:156-215`. The applicable pattern is exact
hash-bound selection and negative mutation controls. No equivalent historical
roster native archive guard was found; Bowl Bound's selector and privacy rules
remain authoritative. No Paydirt runtime or NFL data is reused. Changes remain
in the isolated packaging copy until the main coverage run completes.

A pinned local Ubuntu ARM64 container has started preparing the unchanged
72-test browser suite. This avoids further Mac browser launches and retains
local save-download behavior. Installation or collection is not a browser pass.


## Linux browser gate and exact catalog follow-up, 2026-11-16

The unchanged 72-test browser suite passes in 4.7 minutes inside a local Linux
ARM64 container using Python 3.12, Node 24.22.1, npm 11.19.1 and Playwright 1.61.1.
All 498 staged public source/test pins match the unchanged main tree before and
after the run. Save/download/load, complete regulation games, overtime, coaching,
halftime, timing and roster narration checks execute with the real engine. No
Mac browser was launched. The container uses the host's existing trusted public
Cloudflare CA bundle with certificate verification enabled. This is a portable
browser regression result, not a Mac/Windows native artifact or default-browser
launch certification.

Private receipt: `private-data/data066-linux-browser-gate-v1/receipt.json`.
Browser log SHA-256:
`14b9e78f5cae44b54c9a291abc285991f6ef3fd60fecd973179de3d1057355c5`.
The originally proposed large Playwright image was abandoned; the actual pinned
Ubuntu base and installed versions are recorded in `browser-environment.json`.

The separate actual-candidate check verifies the rendered 173-team catalog and
then exercises each new team's roster narration and UI save/download/load.
Its first attempts exposed a private harness selection error: a substring search
for Kansas also matched Arkansas, and the existing synthetic-test helper chose
the first result. Direct packaged API evidence remains correct. The private
driver now clicks the exact engine-provided team label and checks both selected
IDs before game creation. Earlier failed attempts are retained; no chart, roster,
engine, UI production code or public browser-test input was changed. The fresh
55-team run is pending, not yet a pass.


## Exact candidate browser completion and schema assertion, 2026-11-16

The corrected private driver passes all 55 selected 2002 teams through the actual
assembled runtime: exact visible labels and both canonical team IDs, one real
engine snap with roster narration, UI download/save/reload, and preserved view.
The API and rendered pickers match all 173 catalog entries. First/last-team
mobile checks have no horizontal overflow; server shutdown exits normally with
no browser errors. This panel uses the supported drive mode and does not claim
55 default-regulation complete games. Separate unchanged browser and game panels
provide that coverage within their recorded scopes.

Receipt: `private-data/data066-browser-container-work-v1/candidate-browser-review-v3/receipt.json`,
SHA-256 `665b8a77435008454cd8d4a0b40758c647ceb51ea0e52d1e3ee9b0e997c50a6e`.
The actual runtime manifest remains
`e7c2a783f8e2f6028b307a07dc1ee76aa4a1ec3fb0bb97e0767968323c1c703f`.
Earlier private harness failures remain retained. The Linux container has been
stopped normally and preserved; no Mac browser was launched.

The still-running full Python coverage gate found an obsolete schema assertion
in `test_import_receipt_binds_raw_input_adapter_policy_and_event_observations`:
expected 5, actual 6. Focused unchanged reproduction fails at that exact assertion.
Schema 6 intentionally preserves physical blocked-punt movement; the source
round-trip test already requires 6 and the reader retains schemas 1–5. The
isolated correction changes only this exact expected version, retaining raw
source binding, observation policy, round-trip equality and legacy-negative
controls. Its focused validation and maintained-tree integration remain pending;
the full run continues to collect any other failures and coverage.


## Final review and source-gate allowance, 2026-11-16

The simplify review checked source acquisition, correction evidence, candidate
export and the exact package/native/cohort additions for reuse, quality, cost and
clarity. Shared private-output validation, ordinary roster loading and existing
cohort audit contracts remain reused; no engine or UI rule logic is duplicated.
No additional production cleanup is justified by this review. The schema-version
expectation correction passes all 35 receipt/source checks plus 22 blocked-location
checks. Evidence and legacy assertions remain exact.

The 6,850-test coverage run started at 01:06:37 UTC November 17 and was still
running beyond 03:07 UTC. This locally exceeds the shared CI job's 120-minute
allowance before frontend/browser steps; hosted timing is unmeasured. DEV-083
records a bounded 240-minute allowance for the expanded source gate. Two updated
exact workflow assertions fail against the unchanged 120-minute configuration.
The isolated change retains every command and coverage threshold and leaves the
native builds at 45 minutes. Focused workflow checks and final integration are
pending. The earlier 5,543-test timing is no longer the basis for this allowance.

## Final source-order corroboration and pinned readiness, 2026-11-16

A separate read-only check verifies all **524 inferred interception spots** in
319 retained games against each raw interception's terminal drive position and
the unique first play of the next numbered drive. Raw field coordinates,
possession owner, period and clock agree. Thirty-one provider-array successors
were later than that first play; checking the actual next-drive start resolves
those ordering questions without changing normalized events or candidate files.
This establishes provider consistency, not independent official historical truth.
Private receipt: `private-data/data066-interception-lineage-v3/receipt.json`.

The independent current-release audit also passes all 116 published 2007 teams.
The readiness receipt at `private-data/data066-release-readiness-v1/receipt.json`
rechecks all 1,045 actual runtime file pins, exact 275 new generated files and
110 roster/source-note files, all 580 unchanged 2007 pins, and matching
API/CLI/browser runtime identities. The 385 proposed new destinations do not
collide with existing local files, preserving private imported benchmarks.
The public file-selection scan contains only the two approved fictional roster
pairs; new historical rosters, sources and charts remain ignored.

All 17 isolated workflow contract checks pass after the two expected failures
against the earlier timeout. Final integrated coverage is still running in its
frozen tree. The readiness receipt explicitly leaves release qualification and
new-chart publication false and preserves the failed rushing assessment; it is
not a waiver of remaining gates or distribution review.

## Public generator publication preparation, 2026-11-16

Consulted Paydirt's `docs/dev-notes/chart-release-preparation-2026-11-06.md:149-161`:
adapt its exact nonignored public snapshot and separate mechanical/source/fit
claims; do not copy its data, NFL behavior or its acceptance exceptions. A clean
`data066-generator-release` worktree starts at the already-pushed `a37190f` build
fix and copies only intended public files. All code/test/config bytes match the
frozen integrated coverage inputs. It excludes the unrelated FLOW-007 plan and
all new historical data, regenerates its own ticket index, and preserves the
original workspace. Preparation receipt:
`private-data/data066-publication-preparation-v1/receipt.json`.
No generator commit or push has occurred; full coverage remains a prerequisite.
The [candidate review](data066-release-review.md) also records primary factual-
copyright/source-access references and the remaining exact-cohort decision.

## Exact season-scope regression preparation, 2026-11-16

Consulted Paydirt's `docs/dev-notes/chart-release-preparation-2026-11-06.md:149-161`
and `1977-calibration-release-goal.md:91-100`: adapt exact frozen selection and
separate mechanical/source/fit claims; do not inherit its statistical exception,
NFL thresholds or private data. The existing install validator intentionally pins
118 public teams. Against the private expanded manifest, it first fails with
173 versus 118. A precise proposal-only change pins 173 and retains sample
membership; no catalog requirement is removed or inferred from observed archives.
All 69 focused install, packaging and documentation checks then pass.

The separately frozen `private-data/data066-season-validation-v1/source/` holds
1,987 pinned files, including exactly 275 new generated files and 110 roster/
source-note files. Its only code/config differences from the integrated source
gate are the two release manifests and this catalog assertion; all engine and
generator bytes match. Its complete coverage run started at 03:48 UTC November 17
while the source runs continue. Main seasons and production/tests remain
untouched. Proposed attribution/license wording is explicitly unpublished and
requires the exact-cohort decision; it is not an asserted new upstream grant.

## Parallel validation without changing project tests, 2026-11-16

The serial source gates remain intact. An isolated local pytest-xdist 3.8.0 /
execnet 2.1.2 installation leaves the shared Python 3.12 environment unchanged.
The first distributed probe exposes concurrent checkout wheel-build errors;
a private marker-group attempt also fails its runner checks. Logs are retained.
Using the documented file scheduler keeps all seven wheel tests in one worker:
all 69 smoke checks pass in 3.08 seconds, with worker receipts confirming the
assignment and correct imports. No project test, assertion or skip is changed.

The [xdist file scheduler](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)
and [pytest-cov distributed mode](https://pytest-cov.readthedocs.io/en/latest/xdist.html)
provide file grouping and combined worker coverage. These primary references
were checked before use. No xdist configuration was found in Paydirt's TOML
files; no Paydirt concurrency policy or data is reused. Private read-only hooks
record actual executed node IDs, import roots and frozen source pins.

Independent copies under `private-data/data066-parallel-validation-v1/` each
collect exactly **6,886 tests** through an ordinary serial collection. Separate
three-worker full runs now exercise the source-only and expanded-season trees,
with unchanged branch coverage enforcement, no worker restarts and all source
pins retained. Their results are pending. These additional runs do not turn any
earlier partial or failed run into a pass or authorize historical publication.

## Serial control completion and publication review, 2026-11-16

The original maintained-tree control completes with **6,849 passed and one
failed** in 11,333.72 seconds, with branch-enabled coverage of **91.01%**. Its
only failure is the previously reproduced exact schema-5 expectation against
schema-6 output. This is a failed run, not a release gate pass. The precise
schema assertion correction and additional packaging controls are included in
the frozen integrated source and season runs. The original log and coverage
bytes are preserved in `private-data/data066-original-serial-completion-v1/`.

The two redundant serial copies are explicitly interrupted after 638 and 251
passes, respectively; neither is a completed gate. The complete three-worker
source and season runs continue with their unchanged 6,886-test inventories and
coverage enforcement. One season-run failure remains under investigation.

Before publication, the complete investigation note is preserved under
`private-data/data066-public-note-preservation-v1/`. Individual historical source
sequences, player names and event values are removed from this unpublished
public draft; aggregate findings, citations and reproducibility hashes remain.
The frozen private source/season inputs and prior receipts are unchanged.

## Exact roster selection assertion and second season gate, 2026-11-16

Interrupting the already-failed first season run exposes its cause after 4,124
passes: `test_real_manifest_selects_exactly_the_two_original_rosters_and_sources`
still requires every runtime roster to be a fictional sample. This expectation
is correct for the unchanged public manifest, so that source-gate test remains
untouched. It is obsolete for the private expanded proposal's approved roster
selection. An unchanged isolated rerun first fails in 0.08 seconds.

Reconsulted Paydirt `tests/test_chart_source_bundle.py:156-195`: adapt exact
inventories, byte pins and explicit non-certification; do not reuse NFL data or
runtime behavior. The fresh private v2 proposal preserves all 1,987 parent pins
before changing this one test. Its replacement keeps the exact two original
sample pairs, requires exactly 55 new 2002 generated teams and 110 paired roster/
source-note files, rejects overlap with sample pins, and verifies every selected
file hash. No production or candidate data bytes change. Both affected packaging
and install modules pass **112 tests**; Ruff lint and formatting pass.

A private four-worker scheduler uses the documented
[xdist scheduler hook](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html)
and the pinned [3.8.0 scope subclass pattern](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py).
It keeps the seven shared wheel tests together and distributes other original
node IDs independently. Its 47-test smoke passes in 5.40 seconds: all seven wheel
tests run on one worker, other tests on the remaining three, with no modified
IDs or assertions. Read-only worker receipts and immediate failure records remain
private; no public dependency or hosted workflow command changes.

The full v2 run starts at 04:23 UTC November 17, with the same 6,886-case count,
unchanged coverage floor and failure-on-first-error. Its frozen inputs are under
`private-data/data066-season-validation-v2/`. The only code/config differences
from the source gate are two release manifests and the two precise catalog/
roster expectation updates. The first failed/interrupted season gate remains
preserved and is not relabeled passing. New-chart distribution remains pending.

## Complete expanded-season regression, 2026-11-16 23:14 CST

The corrected private v2 proposal completes its full Python 3.12.8 gate:
**6,886 passed in 3,034.69 seconds (50m34s), 90.77% branch-enabled coverage,
zero skips and zero warnings**, exit 0. This is a completed gate, unlike the
preserved interrupted v1 runs. No further production or candidate-data change
was needed after the precise real-manifest roster assertion correction.

The command runs from `private-data/data066-season-validation-v2/source`, with
the private validation tools directory on `PYTHONPATH` and the pinned
`BB_VALIDATION_ROOT`, `BB_VALIDATION_INPUTS` and `BB_VALIDATION_OUT` recorded in
that run's inputs:

```sh
env PYTHONPATH=/Users/rtulloh/work/bowl_bound/private-data/data066-validation-tools-v1 \
  BB_VALIDATION_ROOT=/Users/rtulloh/work/bowl_bound/private-data/data066-season-validation-v2/source \
  BB_VALIDATION_INPUTS=/Users/rtulloh/work/bowl_bound/private-data/data066-season-validation-v2/inputs.json \
  BB_VALIDATION_OUT=/Users/rtulloh/work/bowl_bound/private-data/data066-season-validation-v2/workers \
  /Users/rtulloh/work/bowl_bound/.venv/bin/python -m pytest \
  -p bb_validation_v2 -n 4 --dist=loadscope --max-worker-restart=0 \
  --cov --cov-report=term-missing -q -x
```

The recorder separately
checks all 1,987 frozen input hashes, all four successful worker receipts, the
exact union of 6,886 unchanged node IDs, no duplicate calls, all seven wheel
checks on one worker, and 135 branch-measured source files under the qualified
root. It verifies the documented scheduler receipt and the absence of recorded
failures. Completion receipt:
`private-data/data066-season-validation-v2/completion.json`.
Log SHA-256: `8cf32fbc22549629f32c634c189aba44d705501b597d05e5d7c097f8812a8fa3`.
Coverage SHA-256: `747d88f97c09d5c4dcad8c9b2885e27040e7b5b4b1ac611829b91203f515d91e`.

The separate public source snapshot passes Ruff lint/format and its unchanged
116-team generated-chart audit. A first direct-script invocation correctly
rejects shared editable-checkout imports; the corrected invocation uses the
public root on `PYTHONPATH` and `python -m scripts.audit_generated_charts`.
Both reports are retained privately. No import-root guard is weakened.

The source-only full gate is still completing its independently repeated real-
engine simulations. Maintained integration and source publication await that
result. Historical fit remains UNVERIFIED, the retained rushing reference
remains FAILED, and new-chart distribution remains unapproved. This successful
regression is not a native-build or published-asset receipt.

## Complete source gate and maintained integration, 2026-11-16 23:26 CST

The independent source-only gate completes with **6,886 passed in 5,198.89
seconds (1h26m38s), 90.77% branch-enabled coverage, zero skips/warnings**, exit 0.
All three workers finish successfully. Its recorder verifies every original
node ID exactly once, all 1,601 frozen source pins, all seven wheel cases on one
worker and all 135 measured source files under the qualified root. Command,
from `private-data/data066-parallel-validation-v1/source/tree`:

```sh
env PYTHONPATH=/Users/rtulloh/work/bowl_bound/private-data/data066-validation-tools-v1 \
  BB_VALIDATION_ROOT=/Users/rtulloh/work/bowl_bound/private-data/data066-parallel-validation-v1/source/tree \
  BB_VALIDATION_INPUTS=/Users/rtulloh/work/bowl_bound/private-data/data066-integrated-validation-v1/inputs.json \
  BB_VALIDATION_OUT=/Users/rtulloh/work/bowl_bound/private-data/data066-parallel-validation-v1/source/workers \
  /Users/rtulloh/work/bowl_bound/.venv/bin/python -m pytest \
  -p bb_validation -n 3 --dist=loadfile --max-worker-restart=0 \
  --cov --cov-report=term-missing -q
```

Completion receipt: `private-data/data066-parallel-validation-v1/source/completion.json`.
Log SHA-256: `b517a46cabdcce13e296f453f84b1a73166c50d95bdc203edf6e5c205717b606`.
Coverage SHA-256: `cae32acc6bf70b482e11155f7e9d4d534a69328ab842839d55d3d31f97bf6fd5`.
The separate expanded-season result above is also complete; neither passing
receipt relabels the preserved earlier failures or interrupted runs.

The guarded integration then copies exactly the 12 reviewed packaging/audit/
workflow/test/documentation changes into the maintained checkout, after checking
all original destination pins and preserving backups. Every production, test
and configuration byte matches the qualified source snapshot. Receipt:
`private-data/data066-maintained-integration-v2/receipt.json`. No historical
chart/roster file or FLOW-007 content is touched. The source publication snapshot
retains the unchanged 116-team chart audit, Ruff checks, prior 197 frontend tests
and 72 real-engine Linux browser checks; the exact private candidate separately
passes all 55 catalog/roster/UI save-load checks. Mac browsers are not launched.

Publication covers the generator code, synthetic tests and public-safe notes.
The exact new 275 generated and 110 previously approved roster/source-note files
remain private pending the recorded new-chart scope/distribution decision.
Historical fit is still UNVERIFIED and the retained rushing reference FAILED.
Version preparation and actual native/published-asset acceptance are later phases.
