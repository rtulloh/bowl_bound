# Historical college cohort development tools

This extends the two-phase [chart generator](chart-generator.md). Phase one can
prepare private multi-team bundles and a reviewable historical matchup slate.
The cohort runner and resume tooling are implemented and under validation in
Milestone 34a; the established two-team commands remain available.

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

## Historical simulation and residual refinement

The new cohort runner accepts only the frozen actual fixture manifest. Candidate
profiles share the same training seeds by season/game/repetition; held-out and
coaching domains are separate. Neutral-site designation is retained as metadata;
no extra home-field rule is invented. Postseason configuration is passed to the
existing engine. Provider flags may be corrected only through an identity-matched
`--primary-overrides` file with primary URL, SHA256, evidence locator and preserved
before/after values. Classification correction does not establish event or
membership completeness.

Engine audit artifacts retain full outcomes, clocks, scoring, statistics, traces
and calls. At most two engine processes are submitted at once. Complete artifacts
are published atomically without replacing earlier files; resume checks source,
manifest, engine/tool, profiles, targets, charts, seed plans and every result hash.
Malformed or changed artifacts fail for investigation. In-memory summaries retain
only verified metric facts, with full logs kept privately on disk.

Separate offensive profiles retain the original bounded knobs. Defensive residual
profiles add run/pass yard offsets bounded to two yards, completion shifts bounded
to 0.08 and interception/sack shifts bounded to 0.03. Defensive completion response
yards use a source-league prior plus the independently fitted defensive effect,
never the same team's offensive chart strength. The finite defensive dice can
leave a requested correction unexpressed. No defensive fumble knob or observed
formation claim is invented.

A residual update needs at least 250 simulated metric observations and takes a
half-step multiplied by `n / (n + 1000)`. Three candidates is the default declared
iteration bound. Global candidates are compared by equal-team, equal-OFF/DEF
normalized error, rather than selecting mutually incompatible team profiles from
different opponent fits. Training gates require 1000 primary observations and
held-out gates 2000; established special-team minimums/tolerances remain explicit.
An empty selected slate remains a valid coverage/exclusion report, but simulation
and refinement reject it before creating outputs.

Sparse, unavailable, saturated and unchanged finite-dice outcomes remain failed
or unidentifiable gates. They are never converted to zero or silently passed.
The selected profile is regenerated from the source model and compared with the
selected candidate before private playtest output is accepted.

A fresh-seed result is simulation validation on source-fitted actual fixtures.
Whole-game source partitioning excludes a withheld game's rows from both sides
and every opponent fit; a genuinely unseen-source diagnostic must also use
uncontaminated neutral priors and independently fitted profiles. The main final
full-source generation does not claim unseen-source validation.

After the user reviews the concrete slate, run the separate second phase with
that exact manifest hash (replace the synthetic placeholder below):

```bash
.venv/bin/python -m tools.chartgen.cohort_refine_cli \
  --source private-data/example/normalized.json \
  --manifest private-data/example/prepared-01/review/manifest.json \
  --targets private-data/example/prepared-01/review/targets.json \
  --reviewed-manifest-sha256 REVIEWED_SHA256 \
  --output private-data/example/refinement-01 \
  --training-repetitions 4 --validation-repetitions 8 \
  --coaching-repetitions 1 --iterations 3 --workers 2
```

Use the identical command with `--resume` after interruption; changed tool/engine
inputs require a new run, rather than silently continuing old calibration.
`calibration-matchups.csv` and `.md` report actual attempted training, held-out
and coaching repetitions/failures for each frozen physical fixture. The final
JSON includes per-team assessments, raw denominators, game-cluster uncertainty,
source/engine/profile hashes and retained candidate history. Statistical failure
may accompany mechanically usable charts and must remain visible.
