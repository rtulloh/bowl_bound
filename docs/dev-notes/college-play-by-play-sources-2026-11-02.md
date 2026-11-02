# College play-by-play sources for a possible chart generator

Research date: 2026-11-02. This is a source-feasibility investigation, not an
implementation milestone or a claim that historical charts are ready to publish.

## Finding

SportsDataverse/cfbfastR is the closest college equivalent to nflverse found in
this review. Season-level play-by-play files are downloadable without an API key
and readable directly from Python. A generator looks feasible for selected modern
team-seasons, subject to game coverage, statistical reconciliation, and explicit
handling of inferred play classifications. A published season file does not
guarantee a complete team-season.

## Paydirt consultation

Reviewed the local Paydirt generator before assessing the sources:

- `../paydirt/docs/chart-generator.md`
- `../paydirt/docs/chart-generation-workflow.md`
- `../paydirt/docs/dev-notes/statistical-chart-generator.md`
- `../paydirt/paydirt/nflverse_play_by_play.py`, especially `_run_chart` and
  `_pass_chart`
- `../paydirt/generate_nflverse_charts.py`

Applicable ideas: normalize source records before chart construction; preserve
opponents, outcomes and provenance; diagnose sparse categories and fallback
classifications; adjust for opponents; separate source estimates from engine
calibration; use deterministic dice allocation and held-out validation. Paydirt's
classifier uses air yards, run location/gap and narration, making actual field
population an important source-selection criterion.

Do not copy Paydirt's play-family mapping, chart symbols, NFL rules/statistical
conventions, calibration coefficients, or templates into Bowl Bound. Bowl Bound
needs its own mapping and engine validation, including all 216 offensive and 36
defensive dice combinations. No runtime dependency on Paydirt is proposed.

## Source inventory

| Source | Documented seasons | Access and likely role |
| --- | --- | --- |
| [SportsDataverse ESPN-derived PBP](https://cfbfastr.sportsdataverse.org/reference/load_espn_cfb_pbp.html) | 2004–present | Bulk CSV/Parquet/RDS; no key needed for downloads. Game state, outcomes, participants, narration and modeled metrics. [Release files](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_pbp). |
| [Classic cfbfastR PBP](https://cfbfastr.sportsdataverse.org/reference/load_cfb_pbp.html) | 2014–present | Separate CFBD-sourced EPA/WPA build. Filter divisions deliberately; newer files include additional lower-division games. [Release files](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/cfbfastR_cfb_pbp). |
| [SportsDataverse NCAA-derived PBP](https://cfbfastr.sportsdataverse.org/reference/load_ncaa_mfb_pbp.html) | 2013–present | Parsed stats.ncaa.org data, including FBS examples inspected here and FCS/lower divisions. Useful narrative-derived pass depth, direction and formation fields. [Release files](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/ncaa_mfb_pbp). |
| [CollegeFootballData API availability](https://api.collegefootballdata.com/data-availability) | Raw plays 2001–present | Bearer key; team/week queries, schedules, opponents and statistics. Current [free tier](https://collegefootballdata.com/api-tiers) allows 1,000 calls/month. Availability varies by game and field. |
| Official school gamebooks and archives | Case by case | Gap filling and older-season research. Verified a full four-quarter [2002 Ohio State–Indiana PBP page](https://ohiostatebuckeyes.com/news/2002/9/28/box-score-from-ohio-state-vs-indiana-51); this does not establish a complete 2002 season. |

The [older cfbfastR-data repository](https://github.com/sportsdataverse/cfbfastR-data)
describes frozen legacy 2002–2021 material. Use the maintained release tags above
for current bulk files, rather than treating a legacy repository as current or
complete. No comparable, verified bulk source for full 1980s/1990s seasons was
established in this investigation.

CFBD documents enriched passing and rushing beginning in 2025. The
[passing schema](https://api.collegefootballdata.com/api/passing) includes nullable
air yards, short/deep depth, direction and parsing status; the
[rushing schema](https://api.collegefootballdata.com/api/rushing) includes direction
and attribution/parse status. These are promising leads, but no authenticated
response was tested, and schema presence does not establish field completeness
or tracking-quality measurements. CFBD's historical schedules begin much earlier
than its raw PBP; those ranges must not be confused.

A licensed alternative is [Sportradar's NCAA game PBP API](https://developer.sportradar.com/football/reference/ncaafb-play-by-play).
Historical season availability and commercial terms were not established here.
Its documentation explicitly says NCAA yards after catch are not collected.

## Actual 2023 file inspection

Downloaded the two public release assets below, then queried their Parquet data
locally with DuckDB 2.0.0 in an isolated research environment. No project runtime
dependency was added. Counts describe these particular snapshots, not all seasons.
Rows include administrative events; they are not all scrimmage snaps.

| Observation | ESPN-derived export | NCAA-derived export |
| --- | ---: | ---: |
| Rows | 153,899 | 326,932 |
| Distinct source game IDs | 903 | 1,569 |
| Columns | 507 | 51 |
| Pass rows used for presence checks | 54,991 (`pass_attempt = true`) | 99,516 (`play_type = 'pass'`) |
| Pass-depth field populated | 42 (0.08%) | 93,986 (94.44%) |
| Air yards populated on those pass rows | 32 (0.06%) | No numeric air-yards column |
| Rush rows used for presence checks | 59,910 (`rush = true`) | 104,996 (`play_type = 'rush'`) |
| Rush-direction field populated | 330 (0.55%) | 101,452 (96.62%) |

The feeds have different event classifications and division coverage; these
denominators are not matched populations. The NCAA depth values observed were
`short` and `deep`, not exact yardage. Direction does not identify a run's designed
gap. Field presence measures availability, not labeling accuracy.

Selected team game counts illustrate why schedule reconciliation is required:

| 2023 team | ESPN-derived distinct games | NCAA-derived distinct contests with that offense name |
| --- | ---: | ---: |
| Michigan | 15 | 15 |
| Ohio State / Ohio St. | 13 | 12 |
| Alabama | 14 | 14 |
| Georgia | 14 | 13 |

These counts are not a certification of full game or season PBP. NCAA records
contained ESPN IDs for 1,531 contests, but only 852 distinct games joined to this
ESPN season export. For example, only 14 Michigan games joined directly despite
15 NCAA contests being present. Reconcile schedule IDs, aliases and individual
plays before combining feeds; never concatenate overlapping games as new plays.

The publisher's [2023 NCAA QA summary](https://github.com/sportsdataverse/sportsdataverse-data/releases/download/ncaa_mfb_qa/ncaa_mfb_qa_2023_summary.json)
reports 1,524 of 1,569 games without flagged errors, leaving 45 with issues.
Reported categories include clock, scoring, down/distance and possession checks.
Its threshold is nonblocking; this is not evidence that every flagged game is
unusable or that every unflagged game is complete. The
[source repository](https://github.com/sportsdataverse/ncaa-mfb-football-data)
also describes checks that are not applicable to this feed.

Snapshot provenance:

- [ESPN 2023 Parquet](https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_cfb_pbp/play_by_play_2023.parquet):
  50,671,667 bytes; release asset updated 2026-10-28;
  SHA-256 `3f7f7d6b95148e00fd7f3a8777cb2e2b1503f5f02953093c65918f3f346a3670`.
- [NCAA 2023 Parquet](https://github.com/sportsdataverse/sportsdataverse-data/releases/download/ncaa_mfb_pbp/ncaa_mfb_pbp_2023.parquet):
  11,205,150 bytes; release asset updated 2026-10-27;
  SHA-256 `d9afa2dc11d0b82be18f34a46f4969308b5a93ee24bc2dc927d20d74b73a3940`.

Local downloads, QA JSON and query summaries remain under ignored
`private-data/pbp-source-research-2026-11-02/`. No play text, historical charts,
player rows or raw season data are included in these public-safe notes.

## Recommended pilot and unresolved decisions

Use 2023 first: it is complete historically and within the current
[1940–2023 major-college rules profile](../rules-profile.md). Michigan and Alabama
are candidates because both inspected feeds contained the expected 15 and 14
games respectively, but still require full reconciliation. A 2025 data experiment
could assess CFBD's richer fields; playing a generated 2025 team would require
a sourced rules-profile extension.

1. Build an expected schedule, including bowls/playoffs and FCS opponents; audit
   missing, duplicate and partial games before selecting a team-season.
2. Normalize ESPN outcomes/state and reconcile useful NCAA narrative detail by
   game and play. Preserve originals, source hashes, IDs and confidence; retain
   disagreements rather than silently overwriting one feed.
3. Reconcile team totals, scoring and per-game pass/rush/sack/penalty/special-team
   accounting with official records. Define college statistical conventions
   explicitly rather than inheriting Paydirt's NFL treatment.
4. Design a Bowl Bound classifier. Generic PBP does not reliably reveal designed
   play calls or distinguish all Bowl Bound families, especially option branches
   and trick plays. Preserve observed versus inferred classifications and unknown
   cases. Avoid turning missing detail into zero yards or certainty.
5. Estimate offense and defense with opponent adjustment and explicit pooling for
   rare categories. College schedules and small season samples make these
   assumptions consequential. Quantize using Bowl Bound dice, then validate
   held-out game statistics and structured traces in the real engine.

This supports statistically modeled charts; it does not promise reconstruction
of original commercial charts or their exact design method.

## Separate workstreams — owner direction, 2026-11-02

After the release build has started, review this investigation on a dedicated
branch while progressing the next planned milestone in another branch. Use
separate Git worktrees so each stream has its own checkout and working changes:

| Stream | Branch | Local worktree | Initial scope |
| --- | --- | --- | --- |
| PBP/chart generator | `research/college-pbp-generator` | `../bowl_bound-pbp-generator/` | Review the source findings, coverage gates, classification assumptions and pilot design before implementing a generator. |
| Next milestone | `milestone/33-core-playability` | `../bowl_bound-milestone-33/` | Complete [Milestone 33](milestone-33.md) under its existing acceptance criteria and ticket dependency order. |

Both branches start from the shared documentation commit on top of `28dea63`.
The already dispatched [standalone build](https://github.com/rtulloh/bowl_bound/actions/runs/41538136008)
uses `28dea63`; branch preparation does not change that build's inputs. Branch
setup is preparation only, not implementation or milestone acceptance.

Keep generator experiments, dependencies, fixtures and changes on their branch;
keep core playability and validation-workflow changes on the milestone branch.
Each stream retains its own validation and review. Coordinate shared-file changes
explicitly and integrate reviewed commits separately. Continue to keep raw PBP,
generated historical charts and audit output in ignored private storage; public
tests must use synthetic fixtures. This investigation does not expand Milestone
33 or complete any of its acceptance criteria.

## Use and publication boundaries

[CFBD's current terms](https://collegefootballdata.com/terms), effective
2026-08-12, permit private analysis/model training and independently derived
outputs while restricting standalone raw-data redistribution. Product-specific
licenses and third-party rights still matter. SportsDataverse's repository
software license alone does not establish rights to all underlying ESPN/NCAA
data. Any future chart publication remains subject to the project's explicit
rights and owner-approval requirements.

## Validation and scope

Inspected primary provider documentation, GitHub release inventories and the two
downloaded 2023 datasets. Checked asset hashes and local aggregate counts.
No authenticated CFBD sample, complete-season statistical reconciliation,
classification-accuracy audit or generator implementation was performed.
Documentation-only changes require whitespace/link checks, not behavioral tests.
The note's relative Markdown links were checked and `git diff --check` passed.
Existing documentation/packaging checks:
`.venv/bin/python -m pytest -q tests/test_release_player_docs.py tests/test_priority_docs.py tests/test_packaging.py tests/test_release_metadata.py`
— **13 passed in 2.42s**, with no skips or warnings.
