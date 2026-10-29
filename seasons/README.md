# Team catalog: public samples and private historical teams

These two fictional Bowl Bound teams are **public and redistributable**, with
complete chart files and synthetic provenance checked into this repository:

- `2007/cedar-valley/`: run-oriented Cedar Valley
- `2007/harbor-tech/`: pass-oriented Harbor Tech
- `2007/provenance/cedar-valley.csv` and `harbor-tech.csv`: synthetic source evidence

All original sample content is dedicated under [CC0-1.0](SAMPLE-LICENSE.md). The
teams contain no historical charts, PDFs or player data. They use the supported
2007 rules profile, not an unsupported current-year profile.

The ordinary web backend discovers these teams automatically with
`.venv/bin/python -m backend --seasons seasons`. A fresh checkout needs no import
step. To restore missing files or generate a separate catalog, run
`.venv/bin/python -m bowl_bound.sample_teams [--seasons /path/to/catalog]`.
Conflicting owner edits are never overwritten. Do not restart a running server
without saving its games first.

Only the exact sample files above are allowlisted. Other seasons, historical
charts, rosters, source PDFs, saves and detailed game records remain private and
ignored. See [the sample guide](../docs/sample-teams.md) for tests and outcome coverage.
