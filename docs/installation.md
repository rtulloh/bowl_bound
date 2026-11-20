# Installation

[Player guide](README.md) · Next: [How to play](playing.md)

## Standalone downloads

Select a standalone release from the project release page. Choose your
operating system and processor, and do not confuse a GitHub source ZIP with a
standalone app.
Standalone archives include Python, the built web interface, 171 generated teams
across 2002 and 2007 and two fictional samples; players do not need Python or Node.js installed.
An Internet connection is needed to download, not for ordinary local play.

For Windows, the **installer** is
`BowlBoundSetup-1.1.1-windows-x64.exe`. Verify its checksum first, then
run it and follow the setup wizard. It installs `BowlBound.exe` for the current
user under `%LOCALAPPDATA%\Programs\BowlBound`, without administrator access,
and creates Start menu and desktop shortcuts. Uninstall through Windows
Settings → Apps → Installed apps → Bowl Bound. Close the game first; uninstall
before installing a replacement version. The installer requires an empty
destination. Personal saves and external team libraries are not removed.

The **DMG is the primary macOS download**. Choose the disk image for your Mac:

| Mac processor | Primary download |
| --- | --- |
| Apple Silicon (M1 or later) | `BowlBound-VERSION-macos-arm64.dmg` |
| Intel (64-bit x86_64) | `BowlBound-VERSION-macos-x86_64.dmg` |

Verify its checksum, mount the DMG, and drag `Bowl Bound.app` into Applications
or a user-writable folder. Unmount the disk image after copying. For these
unsigned builds, remove quarantine from **the copied app only** using the
[manual command below](#macos-gatekeeper-and-quarantine), then double-click it.
The app opens Terminal and your browser; keep Terminal open and press Ctrl+C
there to stop. No Python or Node installation is required.

The ZIP remains a secondary portable alternative and native-builder input.
Older v1.1.0 downloads have ZIPs only; DMGs belong to the next patch release.
They do not bypass Gatekeeper and are not Developer ID signed or notarized.

### Portable ZIP alternative

The **portable ZIP** is an alternative on Windows and macOS. Extract the **entire** archive into a user-writable folder. Do not run
from inside the ZIP or move only the executable away from its supporting files.
Open a terminal in the extracted `BowlBound` folder:

| Platform build | Run | Alternative |
| --- | --- | --- |
| Windows x64 | `.\BowlBound.exe` in PowerShell | `start.bat` |
| macOS Apple Silicon (arm64) | `./Bowl-Bound` | `./start.sh` |
| macOS Intel (x86_64) | `./Bowl-Bound` | `./start.sh` |

Apple Silicon and Intel Mac builds are different; use the right one. Intel means
64-bit x86_64, not 32-bit x86. Linux is source-only for this release.

The browser opens <http://127.0.0.1:8001>. Keep the terminal open while playing;
save your game before pressing Ctrl+C to stop. If the browser does not open,
enter the displayed address manually. See [startup options](startup.md).

### Verify downloads before overriding a warning

Compare the installer or archive SHA256 against the checksum published with that same
release. A matching checksum detects corruption; trust also depends on obtaining
both from the genuine release page. Do not bypass antivirus detections or
organization security policy.

```powershell
# Windows PowerShell: replace the filename with your download.
Get-FileHash .\BowlBoundSetup-1.1.1-windows-x64.exe -Algorithm SHA256
# Or check the portable ZIP instead.
Get-FileHash .\BowlBound-1.1.1-windows-x64.zip -Algorithm SHA256
```

On macOS use `shasum -a 256 FILE.dmg` for the primary download, or
`shasum -a 256 FILE.zip` for the portable alternative.

### Windows: downloaded-file blocking and SmartScreen

Unsigned early builds may show an unknown-publisher warning. After verifying
the download, right-click the downloaded installer or ZIP → **Properties** →
**Unblock** (if present) → **Apply**. For a ZIP, extract it again into a new folder. If
SmartScreen still blocks a verified build, **More info → Run anyway** may be
available. If it is not, contact your administrator or support rather than
disabling protections. Stop if an antivirus product reports a threat.

`BowlBound.exe` is the Windows executable. `xattr` is **macOS-only**; `chattr`
is not a Windows unblocking command. Do not install extra utilities for this.

### macOS: Gatekeeper and quarantine

After verifying the DMG and copying the app, remove quarantine recursively from
**that copied app**, including its bundled Python library, then launch it.
For an app copied to Applications:

```sh
xattr -dr com.apple.quarantine "/Applications/Bowl Bound.app"
open "/Applications/Bowl Bound.app"
```

If you copied to another folder, replace both paths with that app's actual path.
Do not apply the command only to the launcher executable: nested libraries can
retain quarantine and fail to load. Do not apply it to the mounted disk image.
Right-click → **Open**, or System Settings → Privacy & Security → **Open Anyway**,
may also be available depending on macOS and managed-device policy.

If quarantine still prevents a verified extracted portable build from running,
this narrowly removes the quarantine attribute from **that extracted game
folder only** (the ZIP extracts as `BowlBound`; use the actual folder containing
`Bowl-Bound`, `start.sh`, and `_internal`, not the ZIP filename):

```sh
xattr -dr com.apple.quarantine "$HOME/Downloads/BowlBound"
```

This changes the download security marker; it is not a repair or a signature.
Never apply it to an untrusted download, your home directory, the whole Downloads
folder or system files. Do not disable Gatekeeper globally or use sudo. If your
organization blocks the build, ask its administrator.

### macOS portable build: executable permission

If extraction lost executable permissions, in the verified game folder run:

```sh
chmod +x ./Bowl-Bound ./start.sh
./start.sh
```

## Run from source

For official Windows/macOS/Homebrew/pip links and environment help, see
[Python setup](python-setup.md). Use Python **3.10+**. Web builds additionally require Node **24.22.1** and npm
**11.19.1** on PATH. The source checkout includes the reviewed generated teams and
fictional samples.
These commands assume a complete approved source checkout, not an app archive.

macOS/Linux, from the checkout root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[web]"
npm --prefix frontend ci --ignore-scripts
npm --prefix frontend run build
./start.sh
```

Windows PowerShell, from the checkout root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[web]"
npm --prefix frontend ci --ignore-scripts
npm --prefix frontend run build
.\start.bat
```

Select the required Node version before npm commands (`nvm use` where nvm is
available). There is no need to activate the Python environment or change
PowerShell execution policy when using these explicit interpreter paths.
Package downloads require Internet access during source setup.

For **terminal-only** source play, install with `pip install -e .` using the
same environment interpreter; Node and the web extra are unnecessary. Then use
`.venv/bin/python -m bowl_bound --play -d medium --compact` on macOS/Linux, or
`.\.venv\Scripts\python.exe -m bowl_bound --play -d medium --compact` on Windows.
There is no two-sided terminal mode.

See [importing teams](importing-teams.md) for the optional PDF extractor; it is
a separate source-installed tool, not a bundled standalone feature.

### Windows binary distribution agreement

The Windows installer displays the project license and CPython's additional
Windows binary conditions. The first launch of either the installed application
or portable executable also displays those same conditions in a Windows dialog.
Choose **Yes** to agree and continue, or **No** to quit before the local server
and browser start. Acceptance is saved for your Windows account and applies only
to that exact version of the terms; changed terms require a new agreement.
The installer and first-launch agreement are separate steps.

For unattended Windows use, first inspect the packaged
`WINDOWS-RUNTIME-TERMS.txt`, or run
`BowlBound.exe --show-windows-runtime-terms` to print it and its SHA256 without
starting the game or recording acceptance. After reviewing it, explicitly agree
using `BowlBound.exe --accept-windows-runtime-terms SHA256`, replacing `SHA256`
with the displayed complete hash. A missing or mismatched hash does not accept
the terms. `--no-browser` does not skip the agreement. Silent installation does
not record first-launch acceptance.

The per-user receipt is
`%LOCALAPPDATA%\BowlBound\accepted-windows-runtime-terms.json`.
If the terms or receipt cannot be read or saved, the application exits with an
error. Re-extract missing or changed app resources; keep acceptance records in
your own account's writable application-data folder.
