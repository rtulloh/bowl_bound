# Original sample teams

Cedar Valley and Harbor Tech are fictional, independently authored Bowl Bound
teams. No historical chart, player data, imported PDF or Paydirt chart is an input.
Cedar Valley favors running; Harbor Tech favors passing. They are illustrative,
not calibrated claims about historical football strength. Both use the supported
2007 rules profile and complete offense, defense, supplemental, special-team,
PAT and fumble-recovery data. Rare-outcome unit fixtures remain separate.

The actual chart bundles are public and tracked directly in
[`seasons/2007/`](../seasons/README.md), with [CC0-1.0 terms](../seasons/SAMPLE-LICENSE.md).
Only these two fictional teams and their provenance are allowlisted; historical
data and all other seasons content remain ignored. A fresh checkout is already
discoverable by the ordinary web catalog (`--seasons seasons`).

The fictional teams use 2007 because the engine supports historical rules through
2023; using the current year would require a separately approved rules profile.
To restore missing identical sample files or install into an isolated catalog:

```sh
.venv/bin/python -m bowl_bound.sample_teams
```

Or pass --seasons /path/to/an/empty/seasons for an isolated catalog. Select
Cedar Valley (2007) and Harbor Tech (2007) in the normal team picker. The stable
IDs are 2007/cedar-valley and 2007/harbor-tech. The current runtime contract is
team.yaml with offense.csv, defense.csv, special.csv and season-level provenance
CSV, not team.json. The tracked recipe in bowl_bound/sample_teams.py reproduces
all public files; tests compare their bytes and load them through the normal
catalog. No historical/private folder is distributed or broadly unignored.

Existing differing files or symlink destinations are refused, never overwritten.
Identical samples may be installed repeatedly. Historical folders are untouched.
Provenance identifies sample-teams-v2; page/coordinates are explicitly synthetic
schema placeholders and are not assertions that a PDF exists. The source digest
identifies the versioned recipe, not a historical PDF.

## Redistribution

To the extent permitted by law, the original sample-team recipe and its generated
chart values are dedicated to the public domain under CC0 1.0 Universal:
https://creativecommons.org/publicdomain/zero/1.0/ . They may be used, modified and
redistributed without restriction, without warranty. This dedication applies only
to this original sample content, not the Bowl Bound game/rules, historical teams,
third-party assets or other project code.

These samples are the safe default for reusable examples and local play-tests.
Do not infer redistribution rights from a historical filename containing “free”.
Creating and validating both samples is mandatory before linking GitHub or
publishing; publication still requires explicit owner approval and a privacy audit.

## Outcome coverage

Playable samples deliberately do **not** contain every engine stress-test family.
Running columns contain numeric gains/losses, fumbles, breakaways and ordinary
penalties, never PI, interceptions, incompletions or quarterback passing branches.
Only Option can redirect to SOP/BLP; those resolved pass columns may contain pass
outcomes. Passing columns include incompletions, interceptions, PI and quarterback
branches. Defenses keep these events in the corresponding play columns.

Samples use bounded numeric gains and losses, not negative T1/T2/T3/X distances
or remote turnover locations. Ordinary numeric matchups are tested for net losses
no worse than 12 yards; breakaway and quarterback supplemental columns have their
own bounded values. These are explicit fictional-demo design limits, not new
Bowl Bound rules or claims of historical calibration. Safeties near the offense’s
own goal line remain possible and correct. Full Priority Chart/variable/rare-event
coverage remains in dedicated synthetic engine tests rather than playable teams.

Recipe v2 corrects v1’s indiscriminate stress-cell placement. IDs remain unchanged,
but chart/provenance fingerprints change: **v1 sample saves cannot be replayed
against v2 charts**. Finish with an unchanged v1 catalog or start a fresh v2 game;
never edit save hashes to bypass validation. On 2026-10-26 the owner explicitly
authorized replacing the fictional charts and restarting the local game. No
historical teams or engine chart interpretations change.

## Release builds

GitHub release packaging must include only these two original fictional teams,
not copy the entire local `seasons/` tree. The owner directed that Ohio State and
Miami remain unpublished in game packages; their local charts are not deleted.
Milestone 24 must verify chart, provenance and roster exclusions in built artifacts.
