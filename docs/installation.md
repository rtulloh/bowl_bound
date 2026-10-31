# Installation

[Player guide](README.md) · Next: [How to play](playing.md)

## Standalone downloads

The third alpha is available from the project release page. Select your
operating system and processor, and do not confuse a GitHub source ZIP with a
standalone app.
Standalone archives include Python, the built web interface and the two
fictional sample teams; players do not need Python or Node.js installed.
An Internet connection is needed to download, not for ordinary local play.

For Windows, the **installer** is
`BowlBoundSetup-0.1.0-alpha.3-windows-x64.exe`. Verify its checksum first, then
run it and follow the setup wizard. It installs `BowlBound.exe` for the current
user under `%LOCALAPPDATA%\Programs\BowlBound`, without administrator access,
and creates Start menu and desktop shortcuts. Uninstall through Windows
Settings → Apps → Installed apps → Bowl Bound. Close the game first; uninstall
before installing a replacement version. The installer requires an empty
destination. Personal saves and external team libraries are not removed.

The **portable ZIP** is an alternative on Windows and the distribution format
on macOS. Extract the **entire** archive into a user-writable folder. Do not run
from inside the ZIP or move only the executable away from its supporting files.
Open a terminal in the extracted `BowlBound` folder:

| Platform build | Run | Alternative |
| --- | --- | --- |
| Windows x64 | `.\BowlBound.exe` in PowerShell | `start.bat` |
| macOS Apple Silicon (arm64) | `./Bowl-Bound` | `./start.sh` |
| macOS Intel (x86_64) | `./Bowl-Bound` | `./start.sh` |

Apple Silicon and Intel Mac builds are different; use the right one. Intel means
64-bit x86_64, not 32-bit x86. Linux is source-only for this alpha.

The browser opens <http://127.0.0.1:8000>. Keep the terminal open while playing;
save your game before pressing Ctrl+C to stop. If the browser does not open,
enter the displayed address manually. See [startup options](startup.md).

### Verify downloads before overriding a warning

Compare the installer or archive SHA256 against the checksum published with that same
release. A matching checksum detects corruption; trust also depends on obtaining
both from the genuine release page. Do not bypass antivirus detections or
organization security policy.

```powershell
# Windows PowerShell: replace the filename with your download.
Get-FileHash .\BowlBoundSetup-0.1.0-alpha.3-windows-x64.exe -Algorithm SHA256
# Or check the portable ZIP instead.
Get-FileHash .\BowlBound-0.1.0-alpha.3-windows-x64.zip -Algorithm SHA256
```

On macOS use `shasum -a 256 FILE.zip`.

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

For a verified build, first try right-click → **Open**, or the app-specific
**Open Anyway** option in System Settings → Privacy & Security after an attempted
launch. Available choices vary with macOS version and managed-device policy.

If quarantine still prevents a verified extracted portable build from running,
this narrowly removes the quarantine attribute from **that extracted game
folder only** (replace the example path with the real folder):

```sh
xattr -dr com.apple.quarantine "$HOME/Downloads/BowlBound-0.1.0-alpha.3-macos-arm64"
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
**11.19.1** on PATH. The source checkout already contains the fictional samples.
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
