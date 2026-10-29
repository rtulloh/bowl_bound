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

The web game opens <http://127.0.0.1:8000> in your browser once its local server
has started. If no browser opens, enter the displayed address manually. Keep
the terminal window open while playing. Save/download your game before stopping,
then press **Ctrl+C** in the terminal. Closing a browser tab does not stop the
server; stopping the server discards unsaved in-memory games.

Options work with the executable, `start.sh`, `start.bat`, or
`python -m backend.launcher`:

- `--version`: print the public game version without starting a server.
- `--no-browser`: start without opening a browser.
- `--port 8001`: choose another port if 8000 is in use.
- `--seasons PATH`: read a separately installed local team folder. The launcher
  does not copy, change or install teams. Browser saves use your download folder
  or browser-selected save location, not the bundled resources.

The launcher binds only to this computer by default. Remote binding requires
`--host ADDRESS --allow-remote`, is unauthenticated, and is not an online
multiplayer service. Do not expose the game to the Internet or open router
ports. A desktop firewall exception for public networks is not needed for
ordinary local play.
