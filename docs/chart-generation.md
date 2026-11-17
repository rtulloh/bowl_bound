# Chart generator

The chart generator is public source under `tools/chartgen/`, with fictional
tests under `tests/chartgen/`. It is a development tool run from a source
checkout. The installed game reads its ordinary YAML/CSV outputs through the
existing chart loader; it does not depend on the generator or download data.

Use Python **3.12** from the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,web,generator]'
.venv/bin/python -m tools.chartgen --help
```

DuckDB is an optional development dependency for Parquet input. CSV and the core
API acquisition command use the Python standard library. Source snapshots,
historical candidates and detailed receipts go in ignored `private-data/` paths.
The generator's source code and tests are published with the repository under
its code license. Source-data and generated-chart distribution are separately
reviewed; neither a successful command nor the code license grants those rights.

## Acquire and normalize source

For a fresh ESPN core-v2 snapshot, including postseason games assigned to the
requested season:

```sh
.venv/bin/python -m scripts.acquire_chart_source \
  --season 2002 --output private-data/source-2002 --workers 4
```

The destination must be new. This checks each game listed in the season's
regular/postseason inventories, saves exact responses and checksums, and writes
`normalized.json`, `teams.json`, `coverage.json` and `acquisition.json`. Missing
play feeds are recorded as gaps. A complete acquisition receipt means the listed
games were checked; it does not certify complete or accurate play-by-play.
Review coverage before selecting a cohort. Copy the desired source-ID/display-name
pairs into a separate `selected-teams.json`; do not mistake every team mentioned
as an opponent for a complete team-season.

The conservative core adapter preserves unknown values. In older feeds,
`statYardage` on a punt/kickoff return describes the return, not gross kick
distance. Missing gross distances stay unknown. Constant zero starting
`yardsToEndzone` values are discarded. When home-team identity is known, the
adapter checks the end-coordinate orientation before converting `yardLine` to a
start distance. An interception spot is reconstructed only when its return and
the next consecutive snap corroborate it, using the existing location policy.
Missing type labels for field goals/PATs can be classified from explicit source
text; source text and original response bytes remain available for review.

Blocked punts keep statistical punt credit in `yards` and physical movement from
scrimmage to initial recovery in `blocked_kick_yards`. The latter supplies the
`BK` chart suffix consumed by the engine. Narrative parsing requires an explicit
initial kick distance and named field destination with no separate recovery clause.
An unspecified destination or separate recovery needs a reviewed, source-bound
adjudication of the initial recovery spot. Statistical zeros, final spots after an advance, and ordinary punt
distances cannot substitute. Unknown source locations remain unknown. When a team
has observed blocks but no known locations, fitting explicitly pools known physical
locations from other blocked punts in the supplied league source. The team's block
rate stays team-specific. No ordinary-punt pool or invented zero supplies the
conditional location distribution; generation stops when that blocked-punt pool is
also unknown. Receipts identify team/league pooling and count known, unknown and
modeled location samples separately. Sparse pooled support still needs statistical
review. Normalized schema 6 stores this field;
schemas 1–5 remain readable with unknown physical movement, without reinterpreting
their statistical yardage. Existing released charts require separate review before
regeneration; this does not alter their pinned files.

The version-4 core adapter also links return-fumble recoveries recorded as the
first event of the next drive. It checks the previous drive's unique final
punt/kickoff return or interception, period, returning team and matching end/start yard line.
Named returners (the named interceptor for interceptions) must match, with at
most 30 elapsed seconds. An unnamed punt
marked "no return" requires the same clock and position; muff versus fumble
after possession remains unknown. These disclosed associations do not establish
independent source accuracy. Conflicting evidence stays unresolved.

The linked fumble and explicit recovery facts accompany the original kick or
interception event into return-chart fitting. An interception-return fumble
belongs to the intercepting team and does not become a primary rushing/passing
fumble for the throwing team. The separate recovery row retains its source text and
flags, with `no_play=True` marking the duplicated fitting observation; provenance
names both event IDs and the linking policy. Original optional observations and
unknown gross/return distances stay intact. A return-fumble sample containing
only positives alongside unknowns fails rather than becoming a 100% rate.
Existing version-1 through version-3 normalized snapshots remain readable; re-normalize retained
raw games to apply the new classification, or use the experiment below, which
calls the same enrichment before fitting.

For a rush, completion or sack split at a drive boundary, the adapter requires
the same clock and named carrier, a known primary gain, and identical end/start
team, yard line, down and distance. The recovery's advance never substitutes for
the original play's gain. A unique final action and first recovery row must be
in adjacent numbered drives, with no penalty flagged. The original recovery
row and optional observations remain retained. These positive associations do
not establish that other plays were observed nonfumbles.

For older feeds with fumbles recorded separately from rushes, completions and
sacks, inspect candidate primary/recovery links before changing normalization:

```sh
.venv/bin/python -m scripts.audit_espn_fumbles \
  --plays private-data/source-2002/raw \
  --output private-data/source-2002/fumble-audit.json
```

`--plays` points to retained per-game core play-response JSON files (each with an
`items` list). In the acquisition command's `raw/` directory, the diagnostic
selects only `plays-*.json`. A standalone directory of per-game JSON responses
is also supported. The report binds source hashes,
links only unique drive/sequence predecessors with matching clock, period,
possession and carrier, and lists unresolved recoveries. It leaves source bytes
unchanged, establishes no negative observations and never qualifies a release.
The report requires a new file under `private-data/`.

Processed cfbfastR fumble flags are narrative-derived annotations. Their explicit
false values do not independently establish complete historical observation.
Applying a row-local text rule to a separate-row feed can miss fumbles on primary
plays; linking positive rows alone also supplies no valid negative denominator.
See the [2002 investigation](dev-notes/data066-generator-recovery.md#upstream-fumble-flag-investigation)
for the current evidence and source-accounting limitations.

To compare a disclosed historical attribution experiment against the same input:

```sh
.venv/bin/python -m scripts.experiment_espn_fumbles \
  --source private-data/source-2002/normalized.json \
  --plays private-data/source-2002/raw \
  --teams private-data/selected-teams.json \
  --output private-data/fumble-experiment --generate
```

This writes two fitting views: strict source links, then an additional modeled
link when the same explicitly named carrier, primary action/gain, possession and
period agree but the clocks disagree. It borrows no recovery advances or NFL
position/gain thresholds. Both views explicitly model ordinary primary rows as
negative narrative incidence, except ambiguous predecessors, which stay unknown.
This denominator assumption is separate from positive attribution and does not
establish observed nonfumbles. Unsupported recovery rows remain in the input and
ledger but are omitted from fitting. Per-game reasons and per-team primary
coverage accompany the generation result in `experiment.json`. Source hashes are
checked; normalized input and released chart pins remain unchanged. These are
unqualified experiments, including any retained source disagreements, and do not
authorize distribution.
Both views also apply the generator's shared cross-drive return links;
the report lists special-teams and interception-return links separately from
primary rush/pass/sack links.

The separate `--model-return-denominator` option evaluates narrative-incidence
negatives for ordinary punt, kickoff and interception returns with known return
gain. It is off by default. Source flags, raw responses and their observations
are preserved; the temporary fitting view marks these assumptions as authored
and reports their event IDs separately. Returns that may precede an unresolved
recovery stay unknown, including ambiguous terminal records. Missing ordering
protects returns in the recovery's period, or the whole game when its period is
unknown. Penalties, tries, no-play rows and missing return gains are excluded.

An interception is not assigned a non-fumble flag by the primary-play model;
return absence requires this separate option. A source-adjudicated standalone
rush/completion/sack with a known gain and positive fumble is retained for
fitting even if its recovery row has no preceding primary link. The association
ledger still reports that unresolved link; it does not erase the independent
source correction. Reports distinguish retained standalone primary rows from
omitted recovery rows. These choices remain experimental and require source,
denominator-bias and whole-cohort review before release acceptance.

Alternatively, normalize an existing ESPN-derived CSV/Parquet snapshot:

```sh
.venv/bin/python -m tools.chartgen normalize \
  --input private-data/source.parquet \
  --source-url https://example.org/the-actual-source-snapshot \
  --output private-data/normalized.json
```

Use the actual source URL. The normalizer checks required fields and writes a
versioned, checksummed evidence file. Never substitute zeros or inferred designed
calls for missing observations.

## Generate a candidate

Supported execution seasons for this recovered pipeline are 2002 and 2007:

```sh
.venv/bin/python -m tools.chartgen generate \
  --source private-data/source-2002/normalized.json \
  --teams private-data/selected-teams.json --season 2002 \
  --output private-data/candidate-2002 --seed 1
```

`selected-teams.json` is a JSON object mapping stable source IDs to unique display
names. Output requires a new directory, so an earlier candidate is preserved.
The command freezes supplied evidence, generates the corrected tactical baseline,
applies the recovered budget allocator and standard exporter, finalizes conditional
depths, and checks the final files with the release budget/contrast checks and
ordinary loader. Baselines, exact file pins and detailed receipts are retained.
An allocation or evidence failure returns a nonzero exit code and a failure
receipt; a partial cohort cannot be reported complete.

The original 2007 model identity remains immutable:
`authored-bb-budget-aware-v1` / `bb-chartgen-budget-alpha-v1`, SHA-256
`a46aaf838a718e012a2ce90a4438e6de475a0d810f18ab7e92d87148603a9e5f`.
Its original contract explicitly limits execution scope to the published 2007
cohort. The 2002/2007 execution wrapper therefore has a distinct identity,
`authored-bb-cohort-v1` / `bb-chartgen-cohort-v1`, SHA-256
`73fe046d460fe946ece2ea7ccf766320f0119fa5e61ece50e427ce6b84622e55`.
It records the original algorithm as its parent and does not claim a new
historical fit or reuse the old cohort's approval.

Successful generation is followed by independent source/coverage, statistical,
game-panel and distribution review. The candidate receipt explicitly leaves
historical fit unverified and publication unauthorized. Follow the
[generated-chart audit workflow](generated-chart-audits.md) before changing any
release chart pins. Private PDF-imported Ohio State/Miami charts remain excluded.

## Validation and research tools

```sh
.venv/bin/python -m pytest tests/chartgen -q
.venv/bin/python -m scripts.audit_generated_charts \
  --report private-data/current-release-audit.json
```

The recovered research modules also retain deterministic cohort preparation,
simulation, refinement and source-evidence checks. Their research runner is
`tools/chartgen/research_runner.py`, separate from the application's maintained
local-season runner. Research receipts bind the current engine source inventory,
loaded definitions and an explicit coaching configuration. Changing that context
requires review and a new contract, rather than bypassing the compatibility
check or reusing old simulation evidence.
