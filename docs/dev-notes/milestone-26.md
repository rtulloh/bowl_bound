# Milestone 26 — Local MaysFootball chart testing

## Scope

The canonical scope is [Milestone 26 in the project plan](project-plan.md#26-support-local-play-testing-from-free-maysfootball-chart-pdfs).
The owner asked to use the MaysFootball charts listed as free downloads to test the
PDF exporter and prepare local play-test teams. “Free download” is not treated as a
redistribution license. Keep all historical PDFs, converted charts, and detailed
reports outside Git, runtime bundles, and release artifacts.

## Paydirt consultation — 2026-10-30

Reviewed the local Paydirt checkout before planning this follow-up:

- `extract_charts.py` reads original Excel cell values, fills, and number formats
  before writing CSV. Adapt the principle that source evidence must survive conversion;
  do not reuse its workbook assumptions or permissive exception fallbacks.
- `docs/chart-generator.md` explicitly supports one original workbook layout and
  recommends staged output plus chart-reader validation. Adapt source-profile
  documentation and round-trip validation; do not copy its historical defaults or
  overwrite behavior.
- `tests/test_chart_loader.py` and `tests/test_team_charts.py` use synthetic cases for
  token normalization and strict chart validation. Adapt synthetic, isolated
  regression fixtures. Paydirt has no relevant PDF page-rotation or geometry profile
  to reuse.
- No Paydirt code, team data, PDF layout assumptions, NFL behavior, or runtime
  dependency is reused.

## Initial local findings (before the current fixes)

The official [MaysFootball free-download page](https://maysfootball.com/stuff.htm)
lists seven PDFs from 2002 through 2008. Local copies are in an ignored temporary
directory only.

- `2002free.pdf` passes inspection and cell extraction for two teams, but team-file
  serialization refuses several red-filled defensive yardage cells because their
  source colors do not match the current semantic token legend.
- `2003free.pdf` and `2004free.pdf` pass page and cell geometry checks, but lack a
  detectable power rating in the supported header box.
- `2005free.pdf` and the first two offense pages in `2006free.pdf` fail the current
  roll-anchor check.
- `2007free.pdf` has one offense page with unsupported column geometry. Its 2007
  Ohio State and LSU charts are the BCS championship teams the owner wants to play.
- `2008free.pdf` has portrait pages with rotated defense/special content and a distinct
  offense grid. Its defense grid normalizes to 480 cell positions, but its fill colors
  use four-component values and the PDF has no detectable power rating.
- The batch CLI reduces several typed project validation failures to a generic
  “unexpected failure” status, so the cause is not clear to the local user.

The following section records the current state; historical team files remain ignored
and are not included in source control or release artifacts.

## Current local status — 2026-10-30

- The latest batch dry run validates all seven PDFs from 2002 through 2008, covering 18
  historical teams. All 18 bundles are installed under the ignored local `seasons/` tree;
  strict team-file/provenance verification passes for each.
- The 2002 serializer mismatch was exact-zero ambiguity: the CSV token `0` does not encode
  sign/color, while source RGB does. Serialization now uses measured RGB only to select red
  versus green for an exact zero. Synthetic red/green round trips and current 2002 export
  validation pass.
- Blank no-change cells with an out-of-bounds marker were another round-trip loss: the
  serializer wrote an empty token and dropped the timing fact. IMPORT-018 tracks the fix;
  the synthetic regression now covers offense, defense and special-teams rows.
- Rotated defense/special pages in the 2008 PDF are detected as 90-degree pages and yield
  480 positions each. Synthetic coverage verifies source-coordinate preservation through
  round trip. DeviceCMYK fills now convert deterministically and only their exact verified
  palette signatures map to chart colors. Local extraction recognizes all fills, and the
  full 2008 export validates in the latest dry run.
- The 2005 and first two 2006 offense pages use an explicit 20.28-point row profile; all 30
  printed anchors validate before cell positions are emitted (IMPORT-011). A tiny glyph
  overhang is assigned once to its unique center cell; ambiguous or larger overlaps remain
  rejected (IMPORT-019).
- Recovery metadata uses a rotated right-side text column that shifts left by a few points
  in some Mays PDFs. Synthetic regressions cover both verified positions, and all seven
  local PDFs now pass recovery extraction; no range is defaulted.
- Defensive parenthesized `(B)` now has a narrowly scoped, owner-approved interpretation:
  it overrides ordinary offensive results as a defensive breakdown, then triggers the
  offense's B-column reroll. Synthetic tests cover extraction, team-file round trip,
  priority, and the resolver trace (IMPORT-016). Finding and confirming a real example
  during local play-testing remains open. The exported 2007 teams now include the intended
  LSU and Ohio State play-test pair.
- Local roster files and source notes are present beside all 18 historical team bundles.
  The 2003 Miami (Ohio), 2003 Army, and 2006 Navy rosters are explicitly partial key-player
  lists; the other roster files use official university roster sources. All remain private.
  Verified skill-position starters are now ordered first and recorded in each roster's
  `starters` metadata, so commentary rotates only among verified starters at positions
  with evidence. Source limits are recorded beside each private roster. Three local roster
  files also contained empty keys and OCR artifacts that prevented startup; those entries
  were cleaned, and a verified fullback starter was added to the 2006 RB commentary pool.
  Synthetic tests cover starter rotation, validation, serialization, and legacy-roster
  fallback. All 18 local roster files parse, and the intended two-team CLI matchup starts
  successfully (FLOW-006).
- The official [2007 LSU roster](https://lsusports.net/sports/fb/roster/season/2007) and
  [2007 Ohio State roster](https://ohiostatebuckeyes.com/news/2000/7/27/2007-ohio-state-football-roster)
  are available for the intended BCS matchup. Local roster files will be added only beside
  chart bundles that pass full export and round-trip validation.

## Work log

### 2026-10-30 — Opened follow-up tickets

Initial regression-first support for IMPORT-010 is in the worktree: the synthetic
rotated-defense end-to-end test passes, and the local 2008 PDF's rotated defense pages
now inspect and yield 480 chart positions each. The owner approved a local-only rating
of 200 for charts with no numeric rating; the importer now requires an explicit flag and
marks those team files as local-only placeholders.

The initial follow-up dry run exposed the blockers tracked by IMPORT-010 through
IMPORT-019. The current dry run validates all seven PDFs; the importer fixes and issue
records remain in the worktree pending the milestone regression gate and commit. No
historical material is tracked or packaged.

### 2026-10-30 — roster validation and milestone gate

- Corrected the user-reported terminal startup failure by removing malformed empty keys
  and duplicate OCR artifacts from three ignored local rosters. A reserve name that had no
  clean copy was normalized and retained. Starter metadata now includes a source-verified
  fullback in its shared commentary position. All 18 local roster files parse, and every
  starter entry is present in its position list.
- Replayed the user's two-team terminal command with an immediate `quit`: both bundles
  loaded, the terminal started, and it exited without a roster error.
- Exported the seven private source PDFs into a temporary private directory: seven PDFs
  succeeded and all 18 team bundles passed the exporter's team-file round trip. Temporary
  outputs were removed.
- Full Python gate: `.venv/bin/python -m pytest --cov -q` — 2,595 passed, 93.37% coverage
  (75% minimum). Focused metadata and issue-index tests: 50 passed. Frontend tests: 122
  passed across 16 files; production build passed using Node 24.22.1 / npm 11.19.1.
- Ruff check, Ruff format check, `git diff --check`, and `.venv/bin/python -m pip check`
  passed. These checks are complete before the dedicated Milestone 26 commit.
