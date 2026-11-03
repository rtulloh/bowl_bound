# College chart generator (development preview)

The two commands generate local Bowl Bound team bundles from play-by-play evidence,
then assess bounded refinements using the production engine. They do not add a
runtime dependency or publish team charts. This is experimental development tooling;
a complete bundle and completed games do not establish a historical statistical fit.

## Install and inputs

Use Python 3.10+ in this checkout's own virtual environment. CSV input uses the
standard library; Parquet conversion needs the optional dependency:

```sh
.venv/bin/python -m pip install -e '.[dev,generator]'
.venv/bin/python normalize_college_pbp.py --help
.venv/bin/python generate_college_charts.py --help
.venv/bin/python refine_college_charts.py --help
```

Download an authorized snapshot separately. The tools do not create accounts,
request credentials or fetch network data. Raw historical inputs, normalized event
files, generated teams, learned profiles and reports belong in ignored
`private-data/`. Source licenses and underlying data rights must be reviewed
separately; this tool does not grant redistribution rights.

The initial adapter accepts local cfbfastR ESPN-derived CSV/Parquet snapshots.
Required columns are `season`, `game_id`, `id`, `pos_team_id`, `def_pos_team_id`,
`type.text` and `text`. Optional observed fields cover yards, outcomes, penalties,
turnovers, kick/return ownership, down/distance/field position and clock.
Absent optional fields are recorded. Events without distinct possession/opponent
identities are excluded with counts. Duplicate game/event identities fail.
Scans, PDFs and NCAA/CFBD-specific layouts are not accepted by this adapter.

```sh
.venv/bin/python normalize_college_pbp.py \
  --input private-data/source/season.parquet \
  --source-url https://example.invalid/authorized-source/season.parquet \
  --output private-data/source/normalized.json
```

Normalization writes a schema-versioned source-neutral JSON file, source URL,
filename, raw SHA-256, row counts, missing columns and an event checksum. Preserve
this file unchanged. Each event retains stable team/opponent and game/event IDs,
source text, observed result class, scoring yardage, family confidence, penalty
accepted/declined/no-play distinctions, fumbles/lost/recovery evidence, kick and
return yards, sack loss and available situation/clock facts. Unknown yardage is
`null`, never a zero-yard observation. Missing fumble flags remain unknown; an
explicit two-outcome-per-216 prior is recorded if no fumble evidence exists.
Fair catches, downed kicks and touchbacks do not become zero-yard return samples. Explicit original kick result labels take
precedence over unpopulated derived flags; older ESPN PAT flags need this policy.

College sacks count as rushing attempts/losses and are excluded from passing
attempts, matching [engine statistics](statistics.md). Declined fouls preserve
live-play credit; negated/offsetting events do not contribute offensive credit.
Accepted no-play fouls still contribute penalty diagnostics. Scoring plays retain
their observed gain; a touchdown flag does not create a guaranteed `TD` chart cell.

## Phase 1: immutable baseline

Use stable source IDs, not display-name matching. The following names are fictional
examples; the source file must contain the selected team IDs and season.

```sh
.venv/bin/python generate_college_charts.py \
  --source private-data/source/normalized.json --team 1 --name 'Cedar Valley' \
  --season 2007 --seed 19 --output private-data/chartgen/baseline
.venv/bin/python generate_college_charts.py \
  --source private-data/source/normalized.json --team 2 --name 'Harbor Tech' \
  --season 2007 --seed 19 --output private-data/chartgen/baseline
```

The command writes each strict team folder under `<output>/<season>/<slug>`, its
810-cell/30-PAT provenance in `<season>/provenance/`, and a sidecar in
`generation-manifests/`. It refuses an existing team folder and symlink parents.
Keep the baseline and create new output roots for later candidates. The production
CSV codec validates every bundle before writing. Chart metadata uses the explicit
local-only placeholder power rating, with no advanced defense privileges.

Generation is deterministic for the same normalized source, seed, profile and tool
version. All 216 offensive and 36 defensive physical combinations determine row
weights; rows are not equiprobable. Subset-sum allocation selects nearest feasible
symbol masses and weighted empirical quantiles fill numeric cells. Rounding and
finite row masses create visible limits; a rate smaller than a feasible cell may
quantize to zero. Multiple rare categories compete for available row masses.

Every chart has nine offensive columns, B/QR/QT supplemental columns, six defensive
formations with five weighted subrows, six special-team columns, PAT results and a
recovery range. B uses a joint empirical upper-tail distribution from runs and completions,
with each primary column's reference frequency estimated to preserve its mean; QR uses pooled
rushing evidence and QT observed sacks. Option SOP/BLP and pass QR have explicit
small modeled priors (two physical outcomes per 216 before quantization). These
are experimental mechanics priors, not observations of designed calls.

Explicit narrative labels can identify counter, reverse, draw, option, plunge,
screen, sprint/rollout, bootleg or dropback families. A generic rush/pass does not.
At least 30 known family samples are required for a separate family distribution;
otherwise the relevant team run/pass pool is used and recorded. Sparse team
numeric distributions partly pool toward supplied league events. An entirely
missing rush, completion, sack, kick or required return distribution fails with
an evidence error; supply better evidence rather than accepting fabricated zeroes.

Offense and defense are estimated separately. A regularized additive team/opponent
model adjusts run/completion yardage and completion/interception/sack probabilities.
It retains FBS/FCS opponents by identity; a 100-play zero-centered ridge prior
shrinks small samples. No conference strength or formation observations are
invented. Defensive tactical formations are neutral inferred responses, with
quantized team outcome effects. Defense numeric adjustments are bounded to four
yards. Weak pass defenses may use parenthesized numeric responses; strong ones
may add incomplete/INT/QT responses. All combinations resolve through the engine's
priority table. This model needs play testing; it is not an observed tactical chart.

Scrimmage and observed return fumbles have separate sampling denominators.
Fumbles, recovery/lost ownership, interception returns, penalties and positive
narrative OOB evidence are modeled explicitly. Ordinary penalties use named
approved engine tokens; `DEF 5Y` retains the engine's approved policy. Observed zero-yard primary results use explicit white no-change boxes, preserving
QB Sneak color semantics. Fixed empirical cells replace unidentified DS/T/X responses. No variable or guaranteed
TD response is invented from absent evidence. The engine retains QB Sneak/RZDZ;
Advanced II user options remain disabled.

Special teams use observed kicks and returns, blocked-punt frequency, PAT success
and an empirical monotone field-goal range mixture. Field-goal source distance is
kick distance; chart range is line-of-scrimmage distance after subtracting a
7-yard hold and 10-yard end zone. Sparse distance neighborhoods use a stated
Beta(1,1) prior. Return observations are matched to receiving-team identity.
Unknown returns remain unknown and absent pools fail; touchback zeroes must be
reviewed in source diagnostics rather than assumed to be observed returns.

An optional `--coverage` JSON supplies `expected_games` (list of IDs) and `official`
(integer totals keyed as `rush_attempts`, `rush_yards`, `pass_attempts`,
`completions`, `pass_yards`, `interceptions`, `sacks`, etc.). The manifest reports
missing/unexpected games and exact observed-minus-official deltas. It does not
silently replace PBP distributions with cumulative totals. Do not claim complete
historical calibration while reconciliation fails.

Generated provenance uses a clearly labeled virtual evidence table and normalized
source hash, not invented PDF coordinates. Original downloaded evidence remains
in the normalized source file and its raw-source manifest.

## Optional private tactical prior

Neutral tactics deliberately contain no historical coefficients. To make A–F
formation roles meaningful for local play testing, an operator with authorized
reference charts can estimate a **private** pooled prior:

```sh
.venv/bin/python learn_college_tactics.py \
  --reference private-data/references/2007/fictional-a \
  --reference private-data/references/2008/fictional-b \
  --output private-data/chartgen/tactical-prior.json
```

This command reads complete local team folders without modifying them. It pools
numeric and semantic response frequencies, centers every effect across formations
within each play, and applies a fixed 50% shrinkage. Centering removes the overall
team-strength component. Bounds are four yards and 0.12 probability per effect;
scaling preserves centering. These are declared experimental safeguards, not
claimed empirical constants. It stores source hashes and 54 aggregate effects,
not reference rows or a chart template. Reference-derived profiles are private.

Pass `--tactics private-data/chartgen/tactical-prior.json` to **both** generation
and refinement. The profile hash/origin is recorded in candidate manifests and
refinement reports. PBP still supplies offensive/defensive team strength; these
priors only introduce explicitly inferred formation differences. Negative rate
effects and coarse five-row probabilities may be infeasible; inspect the exact
engine probability audits rather than treating requested deltas as achieved rates.
The four-reference pilot is a small modeled prior, not independent evidence of
historical defensive formations or a cell-by-cell cloning target.

## Phase 2: real-engine refinement

The second script regenerates complete candidate bundles from the same source and
a bounded calibration profile. It never edits a baseline chart in place.

```sh
.venv/bin/python refine_college_charts.py \
  --source private-data/source/normalized.json \
  --team '1=Cedar Valley' --team '2=Harbor Tech' --season 2007 \
  --generation-seed 19 --seed 20071102 --iterations 3 \
  --training-games 128 --validation-games 512 \
  --output private-data/chartgen/refinement-01
```

The initial runner is an explicitly balanced **two-team mechanics study**. It does
not reproduce either team's historical schedule. Every team receives the stated
number of training and held-out games, with alternating home/away assignments.
Do not call repeated games between two teams historical-schedule calibration.
A later matched-schedule extension must generate/reconcile an opponent cohort.

Each candidate uses identical paired training seeds. Selection uses training
metrics only; a separate seed domain validates the selected candidate once. Never
retune against those held-out seeds. The initial 128/512 game counts are smaller
than Paydirt's 64/256 full-season plan; reports record actual college team exposure,
raw event denominators, game-cluster variance/standard error and effective sample
sizes so precision can be judged. Increase counts before making tight fit claims.

The production `SavedGame` and local-season audit run every game. The public,
situation-aware baseline coaching policy makes legal actions without chart
lookahead. Structured observations and calls are retained. Overtime series starts are
recorded from the real engine and checked against report state and engine series
order; lawful reset boundaries are distinct from broken state transitions. Clock, scores, scoring
ledger, state transitions, statistics and roll traces are reconciled. Failures are
retained and count against candidate selection. Four held-out seeds additionally
verify save/replay continuation with both CPU possessions.

Profiles jointly adjust run/pass yards, completion, interceptions, sacks and
fumbles. Multipliers are bounded to 0.6–1.4; completion/field-goal shifts to
−0.15–0.15. Return and field-goal knobs are reserved for diagnosed refinements;
the initial automatic proposal does not fit kick-location or coaching defects.
Predeclared efficiency tolerances appear in the report. Core efficiency exposure under 1,000 training or 2,000 validation observations
fails a metric gate. Drawn special-team and PAT metrics require at least 100
observations. Stop when training
passes, a proposed bounded profile is unchanged, or the iteration limit is reached.
The best retained candidate is selected before held-out results are examined.

Reports distinguish mechanics readiness from source/statistical fit. They include
per-team metrics, completion/INT/sack/rush/pass/fumble outcomes, drawn special-team
chart distributions, actual kick outcomes, score/volume and legal call diagnostics.
Drawn kick/return means are not net special-team yards. Sparse or missing metrics
remain visible. Passing mechanics alone does not assert tolerances or historical
accuracy. Four additional held-out games use the existing `chart-v10` policy as a separate
coaching assessment. This small assessment checks mechanics and call diagnostics;
it does not establish a cross-policy statistical fit.

Record the engine hash, git commit, source hashes, seed plan and selected profile.
Any engine timing/rules/coaching change invalidates that fit until revalidated.
Do not adjust chart strengths to hide a known engine or coaching bug.

## Local play testing and review

Load candidate teams with the ordinary game catalog, without replacing reference
charts. Point `--seasons` at the selected candidate root; for fictional examples:

```sh
.venv/bin/python -m bowl_bound \
  --seasons private-data/chartgen/refinement-01/candidate-00 \
  --home 2007/cedar-valley --away 2007/harbor-tech
```

Review `generation-manifests/`, `training/summary.json`, `heldout/summary.json`,
`selected-profile.json` and `refinement-report.json` first. Keep bad seeds and
candidate histories. Historical reference charts may be compared privately for
structural bounds/mechanisms; they are diagnostics, not cell-by-cell targets.
Public tests use original synthetic evidence and never read private bundles.

Track acceptance and unresolved model/source limits in the
[Milestone 34 work log](dev-notes/milestone-34.md).
