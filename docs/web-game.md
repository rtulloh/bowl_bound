# Browser-only Bowl Bound

The static build runs the Bowl Bound Python engine in a Pyodide worker. A host
serves the assets over HTTPS or localhost. Players open the site and choose
Cedar Valley and Harbor Tech, the two fictional 2007 teams included in this
build. Serve the whole output directory, including `browser/`, and preserve
its directory structure when deploying under a subpath.

## Build and test locally

From the repository root, with the project's pinned Node and Python versions:

```sh
npm --prefix frontend ci
npm --prefix frontend run build:browser
python -m scripts.build_browser_bundle --output frontend/dist-browser/browser
python -m http.server 8124 --bind 127.0.0.1 --directory frontend/dist-browser
```

Open `http://127.0.0.1:8124/`. The staging command downloads the pinned
runtime at build time. Once staged, the site loads the runtime from its own
origin. Use a clean static server for the focused end-to-end check, which starts
its own server:

```sh
npm --prefix frontend run test:e2e:browser
```

## Save and resume

The browser saves an engine checkpoint at game start and after accepted
actions. **Save game** also writes a checkpoint on demand. On the opening
screen, open **Saved games** to resume, rename, export, or delete a game.
**Export game** downloads a file for backup or transfer. Use **Import saved
game** to restore it in another browser. The export carries the checkpoint and
control mode. A compatible raw engine save can also be imported when the
matching charts are included. Engine validation applies to all restores.

Saved games belong to the browser profile and site origin. Clearing site data
can remove them. Keep an export as a backup, especially if the browser reports
a storage error. Pause and reload to recover the last confirmed checkpoint if
the engine stops responding.

This build covers individual games. Season management is deferred.
