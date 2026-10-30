# Advanced: import your own team charts

[Player guide](README.md) · [Installation](installation.md)

The standalone game does not import PDFs. Use this optional tool from a matching
complete source checkout to create a local team library, then launch the game with that
library. It does not require Node.js or a frontend build.

Use only charts you are authorized to use. Keep source PDFs, exported teams and reports
private; do not attach or upload them. The game does not download charts for you.

## Set up the extractor

Install Python 3.10 or newer using the [Python setup guide](python-setup.md). From the
root of the complete source checkout:

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

Keep the PDF source folder separate from the team library. Choose a local writable
location if Documents is cloud-synced. Do not put personal teams inside the app or its
release folder.

## Preview and export

Put authorized PDFs in the source folder. Preview, then export the whole folder:

macOS/Linux:

```sh
.venv/bin/python -m tools.pdf_import.cli "$PDFS" --export --output "$TEAMS" --dry-run
.venv/bin/python -m tools.pdf_import.cli "$PDFS" --export --output "$TEAMS"
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m tools.pdf_import.cli $PDFs --export --output $Teams --dry-run
.\.venv\Scripts\python.exe -m tools.pdf_import.cli $PDFs --export --output $Teams
```

The extractor processes top-level `.pdf` files in a deterministic order and prints one
status per file. Successful files can be exported when another file fails; any failure
makes the command return exit code `1`. Fix failed inputs and rerun. Existing destination
files are refused; back up your library before deliberately replacing them with
`--force`.

For a single inspection report, pass one PDF, omit `--export`, and set `--output` to a
private report filename. Inspection does not accept a directory. Without `--export`,
`--output` is a report file, not a team library.

Only digitally generated PDFs in the documented Bowl Bound layout are supported. Scans,
incomplete pairs and ambiguous cells are rejected; missing results are never filled with
zero. Review exported charts against the source before relying on them.
Game season profiles currently cover 1940–2023; importing a chart does not enable other
season rules.

## Start the game with the library

Keep the season/team directory structure created by the extractor intact. In the
standalone app folder, start the game with the library root:

macOS/Linux:

```sh
./start.sh --seasons "$HOME/Documents/BowlBound/seasons"
```

Windows PowerShell:

```powershell
$Teams = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'BowlBound\seasons'
.\BowlBound.exe --seasons $Teams
```

Select the imported teams in the setup screen. The library path must point to `seasons`,
not a year or team folder. A custom library replaces the bundled sample library; if you
want the fictional samples too, add them using `python -m bowl_bound.sample_teams --seasons PATH`
from the source checkout. Use the same unchanged library when loading saves.

For import or game errors, see [troubleshooting](troubleshooting.md). Never include a PDF,
chart, extracted text or detailed report in a bug report.
