# PDF chart importer

This source-checkout tool inspects one PDF or exports charts from one PDF or a
directory. It is separate from the game engine and standalone app. Export validates
every chart cell and PAT outcome; inspection alone does not establish that a chart is
playable. See [team file format](team-bundle.md) for the exported data.

## Install and choose a mode

Use Python 3.10 or newer. Install the optional `pdf` extra to import charts; the `dev`
extra also installs the synthetic-PDF test tools. The game runtime requires only
PyYAML, and native release requirements do not include PDF libraries.

```sh
python3 -m pip install -e ".[pdf]"
```

The install provides `bowl-bound-import`. From a source checkout,
`.venv/bin/python -m tools.pdf_import.cli` is equivalent.

Inspection accepts exactly one non-symlink PDF. It prints the report without writing in
dry-run mode; omit `--dry-run` to save the private JSON report:

```sh
bowl-bound-import "$PDF" --output "$REPORT.json" --dry-run
bowl-bound-import "$PDF" --output "$REPORT.json"
```

Export accepts one PDF or a directory. `--output` is the seasons library root.
Preview and export a directory with:

```sh
bowl-bound-import "$PDF_DIR" --export --output "$TEAMS" --dry-run
bowl-bound-import "$PDF_DIR" --export --output "$TEAMS"
```

Use `--help` for the complete option list. `--output` is required in every mode.

## Batch results and overwrite behavior

Directory discovery is nonrecursive, ignores hidden files and macOS `._` files, and
accepts `.pdf` case-insensitively. Files sort case-insensitively, with original spelling
as a stable tie-breaker. The CLI prints one status per input and a summary, for example:

```text
[1/2] sample-a.pdf: ok
[2/2] sample-b.pdf: FAILED - chart is incomplete
summary: 1 succeeded, 1 failed
```

Each PDF is independent: a failure does not stop the others. Writes for one PDF are
transactional; on a write error, the importer attempts to restore that PDF's prior files
before continuing. Every input is validated and collisions are resolved before writes
begin. Successful PDFs can be exported even when another fails. The command exits `0`
only if all inputs succeed, `1` for any input, validation or write failure, and `2` for
invalid arguments.

If multiple PDFs contain the same season and team identity, every PDF in that collision
is refused; the importer never merges them.
`--dry-run` checks generated destinations, aliases, symlinks, and existing files without
writing. It cannot predict later disk or permission failures.

Existing reports or team files require `--force` to replace. Back up the team library
before using it: changing charts can make saves that refer to the old team incompatible.
Source aliases and unsafe symlink paths are refused even with `--force`.

## Supported layout and privacy

The importer supports digitally generated offense/defense page pairs in the documented
Bowl Bound layout. Page order pairs a school's offense with the following defense; the
offense name and season identify the team. A defense mascot is only a display label and
cannot confirm school identity. Check that each pair belongs together and review exported
charts against the original before use.

Scans, photos, encrypted or malformed files, incomplete pairs, and unsupported layouts
are rejected. OCR is not provided. Missing or ambiguous cells fail validation and are
never converted to zero-yard results.

Keep source PDFs, converted teams and reports private. Status output and reports can
identify source files and teams; do not share them publicly. Do not commit historical
charts, PDFs, report text, or extracted values. Public tests use synthetic PDFs only.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Unsupported or scanned PDF | Use a digitally generated file in the documented layout; OCR and arbitrary layouts are unsupported. |
| Missing or ambiguous cell | Check the source PDF and use a supported copy. Do not fill the result with zero or edit exported values to bypass validation. |
| Some batch files fail | Read each status locally. Correct the failed inputs and rerun; successful PDFs may already have been exported. |
| Duplicate team collision | Check the school names and seasons in the source PDFs. Every PDF involved must be corrected or separated before export. |
| Symlink or input error | Pass a regular PDF file; directories are accepted only with `--export`. Symlinked PDFs, input directories, and output paths are refused. |
| Destination already exists | Preview with `--dry-run`; back up the library before deliberately replacing files with `--force`. |
| Private source or report | Keep it local under an ignored private path. Share only a generic error description, never chart text, files, or report excerpts. |
