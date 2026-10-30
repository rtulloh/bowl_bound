# Team file format (Milestone 5c)

`bowl-bound-import --export` validates every chart cell and dedicated PAT outcome of a
supported PDF and writes each team in the same shape as Paydirt's season folders, so the
files are easy to read, diff, and share tooling with:

```text
seasons/<season>/<team-slug>/offense.csv
seasons/<season>/<team-slug>/defense.csv
seasons/<season>/<team-slug>/special.csv
seasons/<season>/<team-slug>/team.yaml
seasons/<season>/provenance/<team-slug>.csv     # Bowl Bound's own evidence file

seasons/2002/ohio-state/        seasons/2002/provenance/ohio-state.csv
seasons/2002/miami-florida/     seasons/2002/provenance/miami-florida.csv

seasons/<season>/<team-slug>/roster.json        # optional; see rosters.md (not a chart file)
```

The folder name is a **slug**: the school name lowercased, accents folded to ASCII, and every
run of other characters turned into one hyphen (`Miami (Florida)` becomes `miami-florida`,
`Texas A&M` becomes `texas-a-m`). No folder or file name contains spaces. The real name is
stored in `team.yaml` (`team_name`). A name that reduces to nothing, or to `provenance`, is
rejected, and two teams that reduce to the same slug in one season are rejected rather than
merged.

The team folder holds only what a Paydirt team folder holds (the three chart CSVs and a
YAML file). Provenance is kept in a sibling `provenance/` folder so that Paydirt-style
discovery, which looks for folders containing the three chart CSVs, never sees it.

Historical `seasons/` contents are git-ignored and not part of the Python package.
Only the two [original fictional samples](sample-teams.md) and their synthetic
provenance are narrowly allowlisted for public tracking. Converted historical
charts must never be committed; game release bundles exclude Ohio State and Miami.

```bash
.venv/bin/bowl-bound-import private-data/source-pdfs/example.pdf --export --output seasons --dry-run
.venv/bin/bowl-bound-import private-data/source-pdfs/example.pdf --export --output seasons
```

In export mode `--output` is the **seasons root folder**, not a file. In the default
inspection mode it is still a single report file.

## Writing rules

- **Dry-run** validates everything and prints counts and destination folders only, never
  chart text. It creates nothing and does not fail because a destination already exists.
- **Existing files** are never replaced without `--force`. Every destination is checked
  before the first write, so a refusal leaves the folder exactly as it was.
- **All or nothing:** if writing one file fails, files already written in the same run are
  removed (or restored to their previous contents under `--force`), and directories the
  run created are removed.
- **Atomic and private:** each file is written to a temporary file then renamed, and has
  owner-only (0600) permissions. Symlinked roots and parents, and the source PDF, are
  refused. Path separators and `..` cannot escape the root.
- A validation failure writes nothing.
- Output is deterministic: exporting the same PDF twice gives byte-identical files.

## Chart files

All three are plain CSV with a header row and rolls `10` through `39` (offense and special)
or `A-1` through `F-5` (defense). Column positions match Paydirt's, so a positional reader
for Paydirt's files reads the same columns here. Bowl Bound uses its own play names as
headings, and its extra `QR` column comes **last**, after Paydirt's `Fumble` column.

`offense.csv` (31 lines, no comment rows):

```text
#,Line Plunge,Counter,End Reverse,Draw,Option,Screen,Sprint Out,Boot-leg,Drop Back,B,QT,Fumble,QR
```

Columns 1-9 are plays 1-9, then the `B` and `QT` supplemental columns, then `Fumble`, which
is `R` (recovered) or `L` (lost) for that roll, then `QR`. The `R` rolls must be `10..k` and
the `L` rolls `k+1..39` for some `10 <= k < 39`; that column alone defines the fumble
recovery range.

`defense.csv` (31 lines): `#,Formation,Sub,` then the nine play names; one row per
formation `A`-`F` and sub `1`-`5`, for example `A-1,A,1,...`.

`special.csv` (31 lines):
`#,Kickoff,Kickoff Return,Punt,Punt Return,Int. Return,Field Goal,Extra Point`. In the Extra
Point column a blank means the kick is good and `NG` means no good. Those 30 cells are the
dedicated PAT outcomes. They are not part of the 810 chart cells.

A team is **810 chart cells plus 30 PAT outcomes**: offense 270, supplemental 90, defense
270, special teams 180.

### Cell text

Cell text uses Paydirt's notation and is canonical: the reader accepts exactly the text the
writer produces, and anything else is rejected.

| Text | Meaning |
| --- | --- |
| `7`, `-3`, `0` | Yards. |
| `(7)`, `[7]` | Yards with parenthesized or bracketed priority. |
| `42*` | Yards, out of bounds. |
| `TD` | Touchdown. |
| `F`, `F + 6`, `F - 4` | Fumble (bare `F` means `F + 0`). |
| `INT 28`, `BK 5` | Interception or blocked-kick return. |
| `OFF 15`, `DEF 5X`, `PI 15` | Penalty by team, fixed yards, or variable. |
| `BLACK` | Incomplete (a black cell). |
| `B`, `QR`, `QT`, `SOP`, `BLP`, `FG`, `KO`, `NG` | Named results. |
| (empty) | No change. |

Colors, bounding boxes, and original text are **not** in these files. The importer turns each
PDF color into an explicit fact at import time and the engine reads that fact, never the
color.

## `team.yaml`

Illustrative synthetic metadata, not a historical-team export:

```yaml
# Fictional example (not an installable bundled team)
team_name: Example Valley
nickname: Examples
season: 2007
power_rating: 100.0
privileges: []
source_sha256: <64 lowercase hex characters>
source_filename: synthetic.pdf
team_file_version: 2
status: validated
```

| Key | Meaning |
| --- | --- |
| `team_name` | The offense-page school name. This identifies the team, with `season`. |
| `nickname` | The defense-page header (usually a mascot). Display only; never an identifier. |
| `season` | Positive integer. Must equal the season folder's name. |
| `power_rating` | Printed power rating (50-500). Recorded only; yardage factors stay deferred. |
| `privileges` | Printed markers (`W`, `FBO`, `SPBO`, `XWC`), unique. Empty means none were printed. |
| `source_sha256` | SHA-256 of the exact PDF bytes that were parsed. |
| `source_filename` | The PDF's file name. |
| `team_file_version` | Writers use integer `2`; readers also accept legacy version `1`. Version 2 allows empty RGB fields on metadata provenance rows when no fill was measured. |
| `status` | `validated`. |

A marker is recorded as printed. **No privilege is ever defaulted**, and an absent marker is
not an entitlement. The importer decides nothing from a marker. Per the rulebook, `FBO`
(Free Block Option) and `SPBO` identify teams with an outstanding kick rush, printed black
on a red field in the upper left corner of the defensive chart. Using the option belongs to
the later rules milestones. The meanings of `W` and `XWC` are not yet confirmed. The legend
maps `W`, `FBO`, and `SPBO` to a red field and `XWC` to a green field; a marker whose
measured background disagrees is rejected.

The reader parses YAML strictly: duplicate keys, anchors, aliases, tags, merge keys, unknown
or missing keys, booleans where numbers are expected, non-finite numbers, and unknown
privileges all fail. Strings that look like numbers or booleans (a team called `2002` or
`yes`) are quoted on write and come back as strings.

## `provenance/<team-slug>.csv`

One row per chart cell and PAT outcome, plus one `metadata` row for each piece of metadata
evidence (rating, recovery text, privilege marker):

```text
section,column,defense,roll,page,left,bottom,right,top,original_text,red,green,blue
```

`section` is `offense`, `supplemental`, `defense`, `special_teams`, `pat`, or `metadata`.
Each row keeps the one-based page, the PDF-space bounding box (floats written exactly,
including `-0.0`), the original text exactly as extracted, and the measured RGB background.
For metadata rows only, three empty RGB fields mean no fill was measured; white is not
invented as a default. Chart-cell and PAT rows always require measured RGB. RGB is evidence,
not a rules input. Every row must carry the `source_sha256` and filename recorded in
`team.yaml`; the writer rejects a mismatch.

## Reading

`bowl_bound.team_csv` is the single codec for these files: `team_to_files`,
`provenance_to_csv`, `team_from_files`, `load_team(season_dir, slug)`, `team_folder_name`,
`validate_team_name`, `format_cell`, and `parse_cell`. `load_team` refuses symlinked files and
folders, checks that `team.yaml` `season` equals the season folder, and checks that the team
name slugs back to the folder it was read from. Readers are strict whitelists: exact file
set, exact headers, exactly 30 rows per file, ASCII digits only, no BOM, NUL, or carriage
returns. Nothing is coerced, and error messages never contain cell text.

## What validation rejects

- Any missing or duplicated chart position (the 810 + 30 address set must be exact).
- A cell whose text and background cannot be normalized (see the normalization doc),
  including unknown backgrounds and rotated text. Colors are never guessed.
- A serialized cell token whose implied color disagrees with the RGB evidence in its
  provenance row. The reader reports the CSV row and PDF page without exposing source
  text or filenames.
- A PAT dice-number cell whose text differs from its printed roll, or whose background is
  neither white (good) nor red (no good).
- Missing, ambiguous, or inconsistent metadata: an absent, malformed, or implausible rating
  (ASCII digits with an optional decimal fraction, one baseline, no gaps, 50-500); recovery
  text that is not a single column or
  whose endpoints do not partition rolls 10 through 39; an unrecognized privilege marker; a
  marker box without text; or a marker whose background does not match its class. Paint order
  decides overlapping backgrounds, and unknown paint order is rejected.
- A PDF that changed between inspection and export (hash re-check).
- A chart that does not survive a write-and-read round trip through the strict codec,
  checked before any file is written.

## Console output and errors

Exit codes: `0` success, `1` document, input, or output error (including unexpected
failures), `2` invalid arguments. Error messages name the page and the reason only. They
never contain chart text or the source filename. The page and bounding box are kept on the
exception for local debugging.

## Identity and privacy

A team is identified by its offense-page school plus season; the mascot is a label only.
Team files contain historical chart data and are **private**. Do not commit them or paste
them into issues. Public tests build documents from synthetic tokens only.

## Known limits

- Only the documented digitally generated layout is supported (see the layout doc).
- A passing export proves structural completeness and normalizable cells. It does not prove
  every value matches the original chart; independent reconciliation is Milestone 6.
- A grid-only cell with no fill is accepted as a white background, so an unpainted cell
  reads as white. A PAT cell is therefore "good" unless it is painted red.
- Parenthesized and bracketed cells such as `(TD)` and `[TD]` are preserved as distinct
  priorities. Paydirt's own files may spell the same printed cell differently.
