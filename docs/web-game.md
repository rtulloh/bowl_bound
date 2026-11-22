# Browser-only Bowl Bound

The static build runs the Bowl Bound Python engine in a Pyodide worker. A host
serves the assets over HTTPS or localhost. Players open the site and choose
Cedar Valley and Harbor Tech in the default sample build. A build staged
with `--include-release-teams` also includes exactly the generated charts and
reviewed rosters pinned in the release manifest. Serve the whole output directory, including `browser/`, and preserve
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

## Play a season

Select **Seasons** from the opening screen. Give the campaign a name and choose
a historical schedule or **Custom schedule**. Historical choices depend on the
installed chart catalog. The [schedule coverage](season-schedules.md) lists the
games and teams included in each template. For a custom league, choose chart
editions, assign conferences as needed, and enter the week and home and away
teams for each matchup. Mark games that count toward the conference record.

Choose a control mode and select **Play game**. Use **Return to seasons** in the
game menu to leave a fixture and **Resume game** to continue it. Finished games
automatically update **Standings**, **Team statistics**, and **Rankings**.
**Team statistics** opens with five per-game leader cards and sortable offense
and defense tables. Choose totals or per-game figures and narrow the table to
total yardage, passing, or rushing. The tables use Bowl Bound's team box scores,
including its college sack accounting.

Only fixtures explicitly marked as conference games count in conference records.
The ranking uses two-thirds overall winning percentage and one-third opponents'
winning percentage. It weights opponents by completed meetings, excludes their
games against the team being ranked, and uses .500 when an opponent has no
other results. Ties count as half a win.

The browser stores each fixture checkpoint and its accepted final result together
in its local season library. **Remove result** reopens a completed fixture and
recomputes the season totals. **Discard progress** removes an unfinished checkpoint.
If a fixture save fails, use **Retry fixture save** before continuing. Campaigns
belong to the current browser profile and site origin.
