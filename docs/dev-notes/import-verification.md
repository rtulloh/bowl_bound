# Milestone 6: local importer verification

Historical PDF comparisons and their expected values are private. Keep source
PDFs, converted teams, independent expectations and detailed verification reports
under ignored local paths; none are supplied by this public repository.

## Public verification workflow

1. Use the [import guide](../importing-teams.md) to validate and export an
   authorized PDF into an external library.
2. Independently compare every exported position against the source. Do not
   derive the expected values from the exporter being checked.
3. Use `tools.pdf_import.verification.verify_team_export` from a private local
   script to check completeness and metadata against those expectations. Keep
   the script and its output outside ordinary public test collection.
4. Retain source provenance and record any corrections privately. Structural
   validation is not a substitute for independent cell-by-cell comparison.

The public regression uses synthetic files only:

```sh
.venv/bin/python -m pytest tests/test_pdf_verification.py tests/test_pdf_export_e2e.py -q
```

No historical-team ratings, recovery ranges, PAT outcomes or detailed local
comparison results are reproduced here. Public fictional samples are documented
in [sample teams](../sample-teams.md).
