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
distributions into Bowl Bound dice/chart cells. It constructs these outputs from
statistical evidence; proprietary benchmark chart values do not construct or select
this cohort. Neutral calibration profiles were retained because proposed changes
failed protected per-team safeguards. The charts are modified generated estimates,
not official Bowl Bound charts or a reproduction of source narratives.

The release pins exactly 464 chart files and 116 generated virtual-cell provenance
CSVs. The provenance describes generated cell evidence, not PDF geometry. Source
snapshot SHA-256:
`1f8e553002c0299a2993eb533231053d6cf406dbe0e9d41ecc400267484bb1ba`.
The frozen cohort manifest SHA-256 is
`e0fddc5f0e888e5339a924a908a813766c729b195b8c6cf72e2e89cda0f88939`.
This corrected cohort uses generator `college-chartgen-v5`, with the same source
snapshot, neutral profiles and non-OOB chart facts as its preserved predecessor.
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

This is a community-testing alpha, not a claim of historical calibration. Older
retained season audits reconciled games under frozen baseline coaching; their
results do not establish accuracy under the current release AI. Matching a mean
or completing a season does not establish every team's balance. Sparse families,
unobserved formations, finite chart cells, uncertain tails and missing source
fixtures remain limitations. The metadata power rating is a uniform placeholder,
not a historical ranking. Recent seasons are separate future work.

Please report the version, matchup, difficulty, seed/save when available, and the
decision or result that seems wrong. Scores, rushing/passing balance, turnovers,
special teams and repeated computer choices are useful observations. Follow the
[reporting guide](reporting-bugs.md), and review attachments before sending them.
No affiliation or endorsement by the data providers, universities or game
publisher is implied. The code license does not grant rights to excluded content.
