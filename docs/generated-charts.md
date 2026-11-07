# Generated 2007 teams

Alpha 6 adds **116 generated 2007 college teams** alongside the original fictional
Cedar Valley and Harbor Tech samples, for **118 playable teams**. Three source
teams remain unavailable because their generation evidence did not pass the
cohort's coverage gates. No rejected teams were added to increase the count.

Choose a team from the web setup menu. From an installed source checkout, for
example:

```sh
python -m bowl_bound --play -d hard --away 2007/ohio-state --home 2007/lsu --compact --trace 2>&1 | tee /tmp/bb.log
```

The generated teams have no historical player rosters; commentary uses generic
player roles. The two fictional samples retain their original fictional names.
Save/resume requires the same team-chart content; keep copies of saves before
upgrading or replacing a chart.

## Generation and attribution

These charts are independent statistical estimates built from individual
ESPN-derived 2007 play-by-play events supplied through SportsDataverse/cfbfastR.
The [SportsDataverse data release store](https://github.com/sportsdataverse/sportsdataverse-data)
declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit
SportsDataverse, cfbfastR and the ESPN-source lineage. The generated resources
carry [their attribution and license](../seasons/GENERATED-LICENSE.md).

The generator classifies event outcomes, uses disclosed pooling/inference where
called play families or defensive formations are unobserved, and quantizes
distributions into Bowl Bound dice/chart cells. Proprietary benchmark chart values
do not construct or select this cohort. The charts are modified statistical
estimates, not official Bowl Bound charts or reproductions of source narratives.

Alpha 9 uses the experimental `authored-bb-budget-aware-v1` policy. It redistributes
pass-defense responses within exact existing per-call INC/INT/QT and per-formation
INT budgets. These are defensive chart budgets; full plays also consult offense
and Priority. Zero modeled mechanisms stay dormant, and source unknowns remain
unknown. Small budgets use attainable tactical
contrasts with explicit residuals; an equal contrast is not reported as a strict
success. Known interception locations supply a pooled depth distribution; the
short/long and formation roles are authored assumptions, not observed historical
formation effects. The balancing stage preserves its incoming physical weight/depth
inventory after source-based depth transport.
Offense, run/Option defense, supplemental, special-teams, PAT, recovery and gameplay
metadata retain their accepted semantics, including the corrected OOB facts.

The release pins exactly 464 chart files and 116 virtual-cell provenance CSVs in
[the exact release manifest](../release/manifest.json). Each generated team has one
derived virtual source describing its emitted cell tokens, colors and coordinates.
This is generated evidence, not original PDF geometry or raw play-by-play. Detailed
source ancestry remains private. The supplied source snapshot SHA-256 remains
`1f8e553002c0299a2993eb533231053d6cf406dbe0e9d41ecc400267484bb1ba`.
The exporter is `bb-chartgen-budget-alpha-v1`; model SHA-256 is
`a46aaf838a718e012a2ce90a4438e6de475a0d810f18ab7e92d87148603a9e5f`.
Alpha 8's numeric formation prior remains part of this experimental lineage.
The [OOB evidence correction](dev-notes/college-chart-oob-evidence-audit.md) fixes
a positive-only denominator that had marked nearly every ordinary numeric cell.
OOB allocation now uses positive narrative mentions over matching numeric-outcome
support, with exact dice quantization. Missing mentions remain unknown: these are
lower-bound narrative-incidence estimates, not fully observed historical OOB rates.
Some columns have no positive evidence and remain explicitly unidentified; an
unmarked cell does not establish that the source play was observed in bounds.

No raw play-by-play, source narratives, private imported benchmark charts,
historical rosters, logos, saves or detailed audit reports are distributed.
Generated 2007 Ohio State and Miami charts are distinct from privately imported
2002 charts, which remain excluded.

## Testing limits and feedback

This is a community-testing alpha, not a claim of historical calibration.
Provider-to-normalized event checks do not independently reconcile official
season box-score totals or establish complete historical coverage. Ambiguous
provider records remain tracked source limitations; unknown kick distances are
excluded from numerical fitting rather than converted to zero. Older
retained season audits reconciled games under frozen baseline coaching; their
results do not establish accuracy under the current release AI. Matching a mean
or completing a season does not establish every team's balance. Sparse families,
unobserved formations, finite chart cells, uncertain tails and missing source
fixtures remain limitations. The retained Alpha 8 diagnostic below found material
rushing, sack, interception and fumble gaps. Those historical results are not fresh
measurements of Alpha 9. A bounded current-engine game check establishes mechanical
consistency and supplies descriptive results; it does not certify historical fit
or prove improvement. The metadata power rating is a uniform placeholder, not a
historical ranking. Recent seasons are separate future work.

Please report the version, matchup, difficulty, seed/save when available, and the
decision or result that seems wrong. Scores, rushing/passing balance, turnovers,
special teams and repeated computer choices are useful observations. Follow the
[reporting guide](reporting-bugs.md), and review attachments before sending them.
No affiliation or endorsement by the data providers, universities or game
publisher is implied. The code license does not grant rights to excluded content.

Generated-chart releases now require an [automated probability and tactical
audit](generated-chart-audits.md), alongside separate source qualification and
current-engine game/coaching reviews. The gate evaluates actual chart behavior;
different-looking cells and successful completed games alone are insufficient.

## Retained Alpha 8 source-fit diagnostic

The following historical Alpha 8 diagnostic describes 116 paired games per chart
version using then-current Hard-v15 against baseline-v15 coaching, with the same
opponents and seeds between versions. Each generated team has two team-game
exposures. The conditioned supplied source covers 1,291 team-games for these 116
subjects with unequal exposure and different historical opponents/calls. This is
retained evidence, not an Alpha 9 measurement or historical-accuracy pass.

| Measurement | Conditioned supplied source | Neutral predecessor | Corrected catalog |
| --- | ---: | ---: | ---: |
| Completion / pass attempt | 58.79% | 58.84% | 58.50% |
| Interception / pass attempt | 3.22% | 4.35% | 3.97% |
| Sack / dropback | 5.75% | 7.18% | 7.19% |
| Pure rushing yards / attempt | 4.773 | 3.838 | 3.791 |
| Passing yards / attempt | 6.873 | 6.439 | 6.404 |
| Primary fumble / known eligible snap | 1.483% | 2.211% | 2.214% |
| Points / team-game | 28.024 | 28.392 | 28.862 |

Sacks count as NCAA rushing attempts in Bowl Bound. Pure rushing removes sacks
and restores their lost yardage; sack rate uses pass attempts plus sacks. Source
pass exposure is 43,217 attempts, versus 8,362 neutral and 8,419 corrected. Known
primary-fumble source exposure is 92,427 snaps with one additional unidentified
snap; the simulations contain 17,958 and 17,973 eligible snaps. Return-holder
fumbles are separate from primary fumbles. Points use consistent supplied-provider
final-score headers including returns and overtime, not reconstructed touchdown
counts. Official source completeness and totals remain unverified.

Per-team mean absolute errors, neutral to corrected, are completion 5.31→5.16
percentage points, interception 2.01→1.99 points, sack 2.49→2.42 points, pure
rushing 0.923→0.995 yards/attempt, passing 0.971→0.918 yards/attempt, primary
fumbles 1.193→1.155 percentage points and scoring 7.59→7.02 points/team-game.
Individual two-game estimates vary widely; these averages do not establish every
team's balance or justify tuning parameters to this corpus.

The old experimental pure-rushing error bound of 0.5 yards/attempt is exceeded.
That remains a failed accuracy assessment, alongside the material sack,
interception and fumble gaps above. Earlier research already retained neutral
profiles after proposed refinements failed protected per-team safeguards; its
older coaching evidence does not certify the current policy. No accuracy failure
is relabeled a pass because structural or bookkeeping checks succeed.

A bounded mechanism review replayed retained production traces and evaluated
11,296 observed ordinary call contexts with exact 216×36 primary dice. Under the
same corrected call mixture, the direct authored prior changes conditional
numeric run/pass means by about −0.010/+0.013 yards. Those conditional means
exclude pending branches and are not source yards per attempt. Known numeric
credit matches engine field clipping exactly; clipping removes about 0.201 yards
per pure rush attempt and 0.532 per pass attempt in the corrected corpus. It
does not explain the full remaining source-fit gap. Fixed plays, supplements,
fumbles, chart quantization and AI/schedule mixtures remain model limitations
for further work. No new rule, observer or selector defect was reproduced by
this bounded review, and no source or coefficient was changed to clear it.
