# Import your own team charts

[Player guide](README.md) · [Installation](installation.md)

## Before you begin

The standalone game reads validated team folders, **not PDFs directly**. The
chart extractor is a separate source-installed Python tool; it is not included
in the standalone executable and has no drag-and-drop import screen. You can
use it to create a local team library, then point the standalone game at that
library. Importing does not require Node or building the web frontend.

Use only Bowl Bound charts you are authorized to use. Owning/downloading a PDF
does not automatically permit redistribution. Keep source PDFs, converted
charts, provenance and extraction reports private. Do not email them with bug
reports or upload them to GitHub. The game does not download teams for you.

### Supported PDF layout

Only the documented digitally generated vector layout is supported:

- An offense page in portrait letter format (612×792 points), followed by its
  defense/special-teams page in landscape letter format (792×612 points).
- Rotated left-edge season/team/role headings, printed dice anchors and opaque
  vector grid/fill rectangles. The offense has nine plays plus supplemental
  columns; defense has six formations with special teams on the same page.
- Complete offense/defense page pairs in the correct order. The offense-page
  school name and season identify a team; a defense mascot alone is not a
  unique identity. Check that adjacent pages really belong together.

Scans/photos, encrypted PDFs, arbitrary print-to-PDF layouts, incomplete pairs,
unsupported colors and ambiguous/missing cells are rejected. OCR is not provided.
A missing result is never silently changed to zero yards. A successful export
validates completeness and normalization, not an independent visual comparison
of every chart value. Review the output against your originals before relying
on it. Game season profiles currently support **1940–2023**; importing a chart
does not enable unsupported season rules or optional privileges.

## 1. Choose a writable library outside the app

Recommended locations are below. The name `seasons` is the library **root**;
it contains year folders, not the PDFs themselves.

| Platform | Team library | Source PDFs, kept separately |
| --- | --- | --- |
| Windows | Your Documents folder → BowlBound → seasons | Documents → BowlBound → source-pdfs |
| macOS | `$HOME/Documents/BowlBound/seasons` | `$HOME/Documents/BowlBound/source-pdfs` |
| Linux | `$HOME/Documents/BowlBound/seasons` | `$HOME/Documents/BowlBound/source-pdfs` |

The shell commands below create these folders. On Windows they use the actual
Documents location, including a redirected Documents folder. Documents may be
cloud-synced by your operating system; choose a different local-only directory
if necessary. Do not use symlinks for the library or its parents.

**Do not put personal teams inside the executable, macOS app contents,
`_internal`, Program Files, a mounted disk image, or the extracted release
folder.** App resources may be read-only and upgrades may replace them. An
external library survives replacement of the app. Keep your own backups.

## 2. Install the extractor from the source checkout

Download the matching complete source checkout separately from the standalone
app. Install Python **3.10+** using the official/platform links in the
[Python setup guide](python-setup.md). From that checkout's root directory:

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[pdf]"
TEAMS="$HOME/Documents/BowlBound/seasons"
PDFS="$HOME/Documents/BowlBound/source-pdfs"
mkdir -p "$TEAMS" "$PDFS"
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[pdf]"
$Documents = [Environment]::GetFolderPath('MyDocuments')
$Teams = Join-Path $Documents 'BowlBound\seasons'
$PDFs = Join-Path $Documents 'BowlBound\source-pdfs'
New-Item -ItemType Directory -Force -Path $Teams, $PDFs | Out-Null
```

If an environment already exists, reuse it and install the `pdf` extra with
that interpreter; do not replace an existing working environment unnecessarily.
The extractor version matches that source checkout's game version. Print it
with the environment interpreter and `-c "from bowl_bound import DISPLAY_VERSION; print(DISPLAY_VERSION)"`.

## 3. Validate, then export

Put one authorized PDF in your source-pdfs folder. Replace `team-charts.pdf`
below with its actual filename. Quote paths containing spaces.

macOS/Linux, still in the source checkout:

```sh
.venv/bin/python -m tools.pdf_import.cli "$PDFS/team-charts.pdf" --export --output "$TEAMS" --dry-run
.venv/bin/python -m tools.pdf_import.cli "$PDFS/team-charts.pdf" --export --output "$TEAMS"
```

Windows PowerShell, still in the source checkout:

```powershell
$InputPDF = Join-Path $PDFs 'team-charts.pdf'
.\.venv\Scripts\python.exe -m tools.pdf_import.cli $InputPDF --export --output $Teams --dry-run
.\.venv\Scripts\python.exe -m tools.pdf_import.cli $InputPDF --export --output $Teams
```

`--dry-run` checks the same destination conditions as export without creating or
replacing files: the output root and generated paths, symlinks, source-file aliases,
and existing files that require `--force`. It cannot predict later disk or permission
failures during the actual write. **`--export` is essential**: without it, `--output`
means an inspection-report filename, not a playable team library.
A PDF may contain multiple supported page pairs; all validated teams are
exported. Process multiple PDFs one at a time. A directory input is accepted
only when it contains exactly one nonhidden PDF; discovery is not recursive.

Existing destination files are refused. Do not add `--force` as a routine fix:
back up the library first and only replace a team deliberately. Changing a
team chart can make saves that refer to the old chart incompatible. A failed
validation writes no team files. Keep errors/reports local; do not paste chart
contents into a public report.

## 4. Preserve the exported folder structure

An example layout (illustrative names, not a supplied historical team):

```text
seasons/
  2007/
    example-college/
      team.yaml
      offense.csv
      defense.csv
      special.csv
    provenance/
      example-college.csv
```

Keep all four team files and the sibling provenance CSV. The extractor writes
the year and team slug from the source headings; do not manually rename them.
Provenance retains the source hash/filename, page, cell position, original text
and background color. Do not edit hashes or CSV cells to bypass validation.
Copying already validated teams between computers requires this same structure
and any necessary rights; a PDF alone is insufficient. Optional rosters are
not generated by the extractor and are not required to play.

To verify discovery from the source environment, run:

```sh
.venv/bin/python -m bowl_bound --seasons "$TEAMS" --list-teams
```

Windows: `.\.venv\Scripts\python.exe -m bowl_bound --seasons $Teams --list-teams`.
Use an installed ID exactly as listed if selecting teams in terminal mode.

## 5. Start the game using your library

Stop the previous server first, then launch from the **standalone app folder**:

macOS/Linux:

```sh
./start.sh --seasons "$HOME/Documents/BowlBound/seasons"
```

Windows PowerShell:

```powershell
$Teams = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'BowlBound\seasons'
.\BowlBound.exe --seasons $Teams
# Or: .\start.bat --seasons "$Teams"
```

Source web users pass the same argument to their source `start.sh`/`start.bat`.
Open or refresh the setup page and select the imported teams in the home/away
menus. The path must point to **seasons**, not the year or individual team.
Include `--seasons` every time you start, or add it to your own shortcut.
There is no automatic import-folder discovery or saved library preference.

**The selected library replaces, rather than merges with, the bundled library.**
If you want the fictional samples there too, use the source environment's
`python -m bowl_bound.sample_teams --seasons PATH` with your chosen library path.
It adds missing original samples without overwriting conflicting files.
Restart with the same library when loading saves; matching team charts must
remain available and unchanged.

If a team is absent, check the path, export success, folder structure and season
support. Do not move the original PDF into the app to fix it. See
[troubleshooting](troubleshooting.md) or email a description/error message using
the [bug-report guide](reporting-bugs.md), without attaching private charts.
