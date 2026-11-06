# Team catalog: generated teams, fictional samples and private imports

These two fictional Bowl Bound teams are **public and redistributable**, with
complete chart files, fictional commentary rosters and synthetic provenance checked into this repository:

- `2007/cedar-valley/`: run-oriented Cedar Valley
- `2007/harbor-tech/`: pass-oriented Harbor Tech
- Each team's `roster.json` and `roster-sources.md`: original fictional names and CC0 provenance
- `2007/provenance/cedar-valley.csv` and `harbor-tech.csv`: synthetic chart source evidence

All original sample content is dedicated under [CC0-1.0](SAMPLE-LICENSE.md). The
teams contain no historical charts, PDFs or player data. They use the supported
2007 rules profile, not an unsupported current-year profile.

The ordinary web backend discovers these teams automatically with
`.venv/bin/python -m backend --seasons seasons`. A fresh checkout needs no import
step. To restore missing chart files or generate a separate chart catalog, run
`.venv/bin/python -m bowl_bound.sample_teams [--seasons /path/to/catalog]`.
This chart recipe does not generate roster files; reuse the two published
fictional rosters when copying the samples. Conflicting owner edits are never
overwritten. Do not restart a running server
without saving its games first.

Alpha 6 also explicitly tracks 116 generated 2007 statistical teams under
[CC BY 4.0](GENERATED-LICENSE.md). Their 464 chart files and 116 generated virtual
provenance CSVs are individually hash-pinned in `release/manifest.json`; no
historical rosters are included. Alpha 8 corrects the neutral defensive-formation
profile with disclosed experimental yardage tradeoffs while preserving source,
nondefensive and OOB facts. Read [generation and limitations](../docs/generated-charts.md).
Private imported charts, other seasons, historical/other rosters, source PDFs,
saves and detailed game records remain private and ignored. See [the sample guide](../docs/sample-teams.md) for tests and outcome coverage.
