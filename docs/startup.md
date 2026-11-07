# Starting and stopping the local web game

From an extracted standalone folder, run `Bowl-Bound` (`BowlBound.exe` on
Windows), or use `start.sh` / `start.bat`. Keep the complete extracted folder
together. Standalone apps need no Python or Node installation. Platform builds
are still under preparation; only platforms listed with an actual release are
supported.

From a source checkout, install Python dependencies with
`python -m pip install -e ".[web]"`, build the frontend, then run:

```sh
./start.sh
# Windows: start.bat
```

The source script prefers the checkout .venv; otherwise it uses `python3`
(`python` on Windows). On POSIX, PYTHON can select another Python interpreter.
The existing terminal game remains available with `python -m bowl_bound`.
The starter does not install packages or start Vite, reloaders or child servers.

The web game opens <http://127.0.0.1:8001> in your browser once its local server
has started. If no browser opens, enter the displayed address manually. Keep
the terminal window open while playing. Save/download your game before stopping,
then press **Ctrl+C** in the terminal. Closing a browser tab does not stop the
server; stopping the server discards unsaved in-memory games.

Bowl Bound defaults to port **8001**; Paydirt uses **8000**, so both games can
run at the same time. `python -m backend` uses the same Bowl Bound default.

Options work with the executable, `start.sh`, `start.bat`, or
`python -m backend.launcher`:

- `--version`: print the public game version without starting a server.
- `--no-browser`: start without opening a browser.
- `--port 8002`: choose another port if 8001 is in use.
- `--seasons PATH`: read a separately installed local team folder. The launcher
  does not copy, change or install teams. Browser saves use your download folder
  or browser-selected save location, not the bundled resources.

The launcher binds only to this computer by default. Remote binding requires
`--host ADDRESS --allow-remote`, is unauthenticated, and is not an online
multiplayer service. Do not expose the game to the Internet or open router
ports. A desktop firewall exception for public networks is not needed for
ordinary local play.

On Windows, Ctrl+Break is also handled as a graceful stop, like Ctrl+C. Save
before stopping. Closing the console window or ending the process through Task
Manager is not the same as a graceful stop.

## Concurrent source development and play testing

Run a live play test from a dedicated checkout pinned to the reviewed commit,
with its frontend built there and Python imports directed to that same checkout.
Keep that checkout unchanged until the session ends. Use a different worktree
for ongoing edits and a separate port for each server; sharing a dependency
virtual environment does not isolate the imported project code.

Do not edit or switch branches beneath a running source server. Python can retain
an older model in memory and later import a changed module, producing a mixed
runtime even without a reloader. Such a response failure does not by itself mean
the downloaded save is damaged. Preserve the original file and live session,
start a separate server from one consistent snapshot, and load the file there.
Confirm restoration before stopping the old server. Review a traceback or report
the problem if loading still fails; do not hand-edit save integrity or replay data.
