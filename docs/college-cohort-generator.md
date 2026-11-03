# Historical college cohort development tools

This extends the two-phase [chart generator](chart-generator.md). Phase one can
prepare private multi-team bundles and a reviewable historical matchup slate.
Cohort calibration and resume tooling are under development in Milestone 34a;
the established two-team commands remain available.

## Prepare an immutable historical slate

Supply an operator-acquired, checksummed normalized PBP snapshot and versioned
membership, schedule and conference-name snapshots. CSV metadata uses the same
column contract as the documented SDV Parquet files. Historical source data,
charts and reports must stay in ignored `private-data/`. No network request,
reference-chart copy or runtime Paydirt dependency is made by this command.

```bash
.venv/bin/python -m tools.chartgen.cohort_cli \
  --source private-data/example/normalized.json \
  --raw-source private-data/example/source.csv \
  --membership private-data/example/membership.csv \
  --schedule private-data/example/schedule.csv \
  --groups private-data/example/groups.csv \
  --season 2007 --output private-data/example/prepared-01
```

The output path must be new. Existing results are retained after a failure.
Optional `--acquisition` records provider URLs/hashes; `--tactics` supplies a
separately authorized private inferred formation prior. The committed default
is neutral. Reference-derived priors are inferred structural assumptions, not
observed defensive calls, and must not contaminate a source-held-out diagnostic.

Membership requires `season`, `team_id`, `team_id_source` (`espn`), `team_name`,
`subdivision_id` and `conference_id`. Groups require `season`, `group_id` and
`name`. Schedule rows require stable `game_id`, matching `season`, `home_id`,
`away_id`, explicit `neutral_site` and `completed` booleans, `season_type`,
`start_date` and optional `week`, `notes`, `playoff_bowl_name`. Unknown neutral
flags, duplicate identities, cross-season data and opponent mismatches fail.
Names come from that season's group snapshot, including historical conferences.
The optional original PBP header audit verifies its source hash and canonical
home/away identities; same-provider agreement is not independent confirmation.

## Evidence and opponent boundary

Game presence is insufficient. The initial engineering screen requires all four
regulation periods, at least 20 live plays from each side and known primary
rush/completion/sack yardage. Missing or stale terminal clocks are warnings,
not fabricated zeroes or proof of a complete sequence. This screen does not
establish official play-count/statistical completeness. Independent official
corroboration is reported separately and currently remains pending.

The default chart eligibility floor is six screened source games plus at least
30 known rushes, completions and dropbacks. It is an engineering floor rather
than a calibration exposure guarantee. Failed teams remain explicit records.
Source opponent effects condition on all supplied completed screened games,
including observed external opponents, using the generator's regularized fits.
Those opponents need not have charts. There is no recursive chart dependency.

Only recorded fixtures from the requested season can enter this study:
qualified major-conference games, major interconference games and postseason
bowls where both endpoints have qualified generated charts. Other actual games
remain in the exclusion report. No invented pairings, cross-year opponents,
generic replacement teams or silently trimmed schedules are used. A postseason
flag alone does not verify a BCS/title label; unresolved classifications say so.

## Review artifacts

`charts/` holds loadable private bundles and immutable generation manifests.
`review/matchups.md` gives conference groups and a team index;
`matchups.csv` contains one row per physical fixture, sorted by date and ID;
`manifest.json` freezes sides, neutral/postseason flags, source qualification,
chart availability, inclusion/exclusion reasons and source/engine/profile hashes.
`targets.json` stores each team's separately computed offensive and defensive
restricted targets. Both use exactly the selected simulation fixture IDs.
Full-season source summaries are descriptive context, never substituted targets.

The user-requested slate review precedes broad calibration. The simulator must
validate exact fixtures and repetition counts against the frozen hash. Fresh
simulation seed domains do not make those source-fitted games unseen. Genuine
source-held-out diagnostics must exclude withheld rows from all opponent fits
and learned profiles as well as team source totals.

Public tests use original fictional data. Historical matchup reports contain no
raw play text or private reference cells and remain private despite their
review-oriented format. Generated charts are development/playtest inputs and
are not approved for publication or runtime packaging.
