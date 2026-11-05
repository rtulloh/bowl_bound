# Milestone 38 — Web chart viewer

Status: implementation complete and reviewed; awaiting owner visual confirmation.
Separate from the Alpha 6 chart-content release.

## Scope and acceptance

Owner selected Web UI first on 2026-11-05. Provide a Charts button during a game,
defaulting to the controlled team. Let players inspect either team's offense and
defense, including all rolls, plays, formations and the offensive supplemental
columns. Preserve normalized cell colors, signs, priorities, out-of-bounds markers
and explicit zeroes. Provide text equivalents and a legend.

Chart reading must preserve the complete save, revision, pending decisions, clock,
statistics and dice journal. The engine owns the chart view; the API serializes it
and the frontend only renders it. Never expose source provenance or file paths.
Keyboard dismissal, focus restoration and narrow-screen scrolling must work.

## Paydirt consultation

Reviewed local Paydirt `paydirt-web/frontend/src/components/Plays/OffensePlays.jsx`
and `DefensePlays.jsx` before implementation. Adapt the visible play numbering and
board-style presentation while retaining Bowl Bound's own play/formation labels.
No dedicated chart-view component was found in that frontend. Do not reuse its
NFL play names, formations, keyboard handlers, chart data or runtime code. A chart
viewer has no play-selection shortcuts and cannot issue gameplay commands.

## Validation

Red-first checks: the chart-view module/component did not exist; all four new
API cases returned 404 before implementation. A later synthetic zero/out-of-bounds
case failed with `0` instead of `0*`, then passed after preserving that marker.
No prior gameplay assertions changed. Save-purity tests freeze the download
timestamp because each save includes a fresh timestamp and integrity hash.

Focused Python checks: 111 passed across chart/API, control-contract, save replay
and issue-tracker cases; another 59 passed across release/archive/metadata/player
documentation checks. The new engine/API cases total eight after the marker
regression was added. All 150 frontend tests passed.

Real-engine browser checks initially found lost focus after Escape and an
absolutely positioned screen-reader span escaping the grid on phones. Closing
the native dialog before restoring focus and positioning cell descriptions
relative to their cells fixed both. Desktop (1280px) and phone (390px) checks now
pass with full-grid counts, zero gameplay POSTs and identical save contents
(except download timestamp/integrity metadata). No assertions were weakened.

Actual fictional-team screenshots are retained locally under ignored
`private-data/chart-viewer/`: `offense-desktop.png`, `defense-desktop.png` and
`defense-phone.png`. They use only the original fictional sample charts.

Cumulative gates passed: **3,966 Python tests, 93.33% branch-inclusive coverage**
(943.60 seconds); **150 frontend tests** and **56 real-engine Chromium tests**
(4.1 minutes). No skips. Browser output retains the existing NO_COLOR/FORCE_COLOR
environment warning; Vitest reports its jsdom performance advisory. Initial browser-gate
attempts with an isolated port/fixture configuration were invalid: existing
full-game tests hard-code port 8123 and several fixture helpers also require
`BB_E2E_SEASONS`. Stopped those runs and reran the established gate on 8123 with
the matching canonical fixture path; no project assertions or timeouts changed.

Validation environment: Python 3.13.17,
Node 24.22.1 and npm 11.19.1; pip check, Ruff checks/format, frontend production
build and npm audit (zero vulnerabilities) pass. No dependencies changed.

The simplify skill review confirmed reuse of normalized `format_cell` and
existing engine play/formation labels, no frontend rule parsing, no chart reads
on the ordinary gameplay path, no provenance in the view and no added runtime
dependency on Paydirt. Expanded new CSS declarations for review.

Track acceptance under UI-061; owner visual confirmation remains separate.

## Commands

Run from the feature worktree (frontend commands use the pinned Node/npm PATH):

```sh
.venv/bin/python -m pytest tests/test_chart_view.py tests/test_api_charts.py -q
.venv/bin/python -m pytest tests/test_api_control_contract.py tests/test_save_game.py tests/test_issue_tracker.py -q
.venv/bin/python -m pytest tests/test_release_archive.py tests/test_release_package.py tests/test_packaging.py tests/test_release_metadata.py tests/test_release_player_docs.py tests/test_priority_docs.py -q
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pip check
.venv/bin/python scripts/build_issue_index.py
npm ci --prefix frontend --ignore-scripts
npm test --prefix frontend
npm run build --prefix frontend
npm audit --prefix frontend --audit-level=high
BB_E2E_SEASONS=/private/tmp/bb-chart-viewer-e2e-seasons npm run test:e2e --prefix frontend
git diff --check
```

The canonical `/private/tmp` path avoids macOS's `/tmp` symlink, which the sample
installer deliberately refuses. Existing browser tests require standard port 8123.
The visual preview server uses port 8139 and is independent of test fixtures.
