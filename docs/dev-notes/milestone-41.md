# Milestone 41 — Priority and full-page chart views

Status: local acceptance complete; owner visual review pending. Implemented in
an isolated worktree from Milestone 38 commit 89b29e4.

## Scope and acceptance

Owner requested a Priority button next to Offense and Defense, then assigned it
to this next UI milestone and a subagent. Add a shared, read-only matrix with
readable offensive rows/defensive columns, operation definitions and approved
exceptions. Preserve team selection, native dialog closing and focus restoration.
Reading it never changes a saved game, pending decision, clock, dice, statistics,
revision or computer call.

Owner further requested that all offensive totals 10–39 be visible together on
one desktop page. All 30 defense rows must fit analogously at 1440×1120 and
1280×1000, without inner vertical scrolling or page clipping. Keep text readable
and retain phone scrolling. Team charts continue to display the selected team's
actual loaded, normalized CSV data, the same frozen facts used by the engine.
All chart help and Priority help must start closed and be user-expandable.

Provide Open in new tab and Open in separate window controls. Each detached
view has independent team and Offense/Defense/Priority controls, and can remain
open while the parent game is played. Separate-window launch must isolate its
opener before navigating, leave a usable new-tab fallback when blocked, and
show recovery controls after a game session expires. No detached mount may
create a game, start autoplay, prepare a computer call or submit a command.

Use the existing engine resolution as the source of every priority operation.
Do not implement a second matrix in the browser or change football behavior.
Verify all 156 printed intersections against the independent expected matrix,
including expanded equivalents and the approved defensive (B) extension.
Use no private team chart or rulebook image; public tests remain synthetic.

## Paydirt consultation

Reviewed local Paydirt `docs/priority-chart.md` and the opening reference in
`paydirt/priority_chart.py` before implementation. Adapt its clear operation key,
row/column orientation and synthetic worked-example approach. Deliberately do
not copy its matrix or fumble/QR/NFL behavior: those differ from Bowl Bound's
approved rules. No Paydirt runtime dependency or team data is introduced.

Bowl Bound authorities reviewed: `docs/priority-chart.md`,
`bowl_bound/resolution.py`, independent `tests/priority_matrix.py`, and the
exhaustive priority and documentation tests. Reuse the existing read-only viewer
and its loaded team charts rather than introduce a separate data source.

## Implementation and review

The engine chart presenter derives the 12×14 display reference by applying
`resolve_cells` to representative normalized facts. The first 13 columns match
the independent 12×13 matrix and all 196 expanded coordinates; the last marks
the approved defensive (B) extension. No rule-resolution code changes. Legends
explain controlling results, supplemental/Option/penalty procedures, offensive
parentheses, INT/QR, INT/TD, F/TD and signed minimum locations. This ordinary
scrimmage reference does not claim to cover special-call procedures.

The existing chart panel and grid are reused in the native dialog and standalone
query shell. The shell is selected before mounting the game application and uses
only existing chart GET requests. It loads both frozen team books concurrently
once per viewer/retry, retaining team selection without fetching on tab changes.
Tab URLs contain only game ID, side and view. New-tab links use noopener/noreferrer;
a separate window starts empty, has its opener cleared, then navigates. This
allows genuine blocked-window detection without misreading noopener's null return.

Desktop density uses 13px text and compact row padding, retaining sticky headers
and horizontal scrolling. Smaller screens keep the original readable row size
and vertical/horizontal scrolling. Help, color key and exceptions are initially
folded away. Expanded help may use ordinary dialog/page scrolling.

The simplify review checked reuse, quality, efficiency and clarity. It retained
the single panel/grid and engine resolver. Cumulative tests found the reordered
controls had changed initial native-dialog focus; Close charts was restored as
the first focusable control without weakening the existing browser assertion.
The previous lexical architecture guard prohibited the word “priority” anywhere
in browser code. Its expected scope now permits displaying the engine's shared
reference and rejects cell-priority access/resolver operations instead. Football
calculation, raw chart parsing and prohibited terminology guards remain intact.

## Red-first evidence

- Unchanged Python baseline: 5 failed, 1 passed because the priority field was
  absent from the chart book/API. New tests independently verify all printed
  intersections and all expanded runtime coordinates.
- Unchanged web baseline: 5 failed, 1 passed for missing Priority/detached
  controls and initially open help. The existing open-help expectation changes
  because the owner explicitly requested it closed; opening remains tested.
- Unchanged browser layout: both desktop cases failed; total 39 ended at
  y=1308.83 (1440×1120) and y=1324.14 (1280×1000). New geometry assertions
  require first/last rows inside the viewport, no inner vertical overflow and
  at least 12px cell text. All displayed cells are checked against the actual
  real-engine chart GET response, including both offense and defense.
- Review regression: 1 failed, 1 passed when the defensive (B) help omitted
  SOP/BLP precedence. The clarified help and explicit offensive-parenthesis
  explanation pass with the full independent matrix checks.
- Request-count expectations now cover the concurrent home/away pair once,
  rather than a fresh fetch on each team change. No gameplay requests occur.

## Validation

Focused engine/API/independent matrix: 405 passed. Focused frontend: 6 passed.
New real-engine browser cases: 6 passed, covering desktop complete charts, phone
Priority, safe detached tabs/windows, unchanged saves/no POSTs and expired URLs.
Full frontend: 154 passed. Full real-engine browser gate: 62 passed in 4.2m,
including complete regulation/overtime and coached games. Final focused browser
follow-up: 8 passed, including keyboard help and independent parent/child
selection. No skips. Browser
startup emits the existing NO_COLOR/FORCE_COLOR environment warning; Vitest
prints its worker-reuse performance advisory. Neither indicates a test failure.
Ruff check/format, pip check, npm audit (zero vulnerabilities), production build,
issue tracker and player-documentation checks pass. Full Python gate: 3,968 passed in 825.35s (13m45s), 93.40%
branch-inclusive coverage (required minimum 75%).

Commands (run from the isolated worktree; prepend Node 24.22.1's bin to PATH for
npm):

```sh
.venv/bin/python -m pytest tests/test_priority_view.py tests/test_api_charts.py tests/test_chart_view.py tests/test_priority_matrix.py tests/test_priority_docs.py -q
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pip check
npm test --prefix frontend
npm run build --prefix frontend
npm audit --prefix frontend
BB_E2E_SEASONS=/private/tmp/bb-priority-e2e-seasons npm run test:e2e --prefix frontend
BB_E2E_SEASONS=/private/tmp/bb-priority-e2e-seasons npm run test:e2e --prefix frontend -- priorityViewer.spec.js chartViewer.spec.js
.venv/bin/python scripts/build_issue_index.py
.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_release_player_docs.py -q
git diff --check
```

Preview on port 8140 uses the original fictional Cedar Valley/Harbor Tech CSV
bundles. Actual desktop (1440×1120 and 1280×1000), defense, shared Priority,
detached-window and phone screenshots are retained only under ignored
`private-data/milestone-40/`. Visual inspection confirms compact readable tables
and closed help. Measured detached offense at 1280×1000: first row y=189.78,
last row y=807.59, grid scrollHeight/clientHeight both 695, cell text 13px.
The 14-column Priority grid may scroll horizontally at smaller desktop widths;
team-chart columns and all 30 rows fit at the required reference sizes.
No new runtime source paths were introduced; the existing exact release manifest
already includes every modified runtime/frontend module. No private data or
chart imagery is added to tracked files.

Acceptance tracks each objective separately: UI-062 Priority; UI-063 full desktop
chart; UI-064 initially closed help; UI-065 detached tab/window controls.
Alpha 6/M39 remain a separate stream; no publication is part of this milestone.

## Acceptance

Tested implementation: `92fc811dafd6c56cabcb554451f43d2aa45bd42a`.

All four objectives satisfy their documented synthetic, API, frontend and
real-engine browser checks. Original fictional CSV screenshots provide the
reviewable result. Reading either team, switching any reference, closing help
or opening/dismissing independent windows changes no game/save state and
reveals no selected computer call. The main game remains playable while a
detached chart stays open. No release, merge, tag or push was performed.

UI-062 through UI-065 await owner play-test confirmation before closure.

## Canonical numbering correction — 2026-11-05

Public Alpha 6 commit `9a2897f7d45d9b2b6c48fc21fd311b02562d788b` assigned
Milestone 40 to DEV-073's bounded native-catalog discovery fix. Retarget this
local viewer work and UI-062 through UI-065 to Milestone 41 before integration.
Original tested commits, append-only ticket evidence, screenshot paths and
Git history retain their original labels/hashes; no implementation is changed.
Metadata/documentation checks apply to this correction, without artificial
behavioral tests.

The next release candidate must start from that exact public commit, integrating
only Milestone 38 and this Milestone 41 viewer work. Do not use private local main
or alter the Alpha 6 pipeline. Preserve the port-8139/8140 previews. Owner web
play-test review precedes any subsequent release publication.

For this preparation phase, reconsulted Paydirt `.github/workflows/release.yml`,
`tests/test_release_metadata.py` and
`docs/dev-notes/release-readiness-2026-11-02.md`. Adapt coordinated version checks,
separate build/publication stages and concrete complete-game validation evidence.
Bowl Bound's own exact manifest, approved generated catalog and native catalog
smoke remain authoritative; do not copy Paydirt's packaging paths, source data,
private audit records or NFL behavior, and add no runtime dependency.

## Original-board presentation follow-up

Owner feedback adds UI-066 (large grouped defense formations, boxed dice and
stronger colors), UI-067 (Running Plays1–4, separate Option5, Passing Plays6–9
bands and supplemental offense block), UI-068 (loaded Special Teams chart),
and UI-069 (prominent bordered tab/window launch controls).
Earlier Paydirt images guide layout only; later Bowl Bound references confirm
grouping. No reference values or images are copied. CSV facts/rules stay intact.

Reconsulted Paydirt paydirt/cli_charts.py for explicit offense/formation labels
and dice/result presentation. No equivalent web chart viewer was found. Do not
reuse its NFL play names/classification (play5 is Screen). Bowl Bound Play,
PLAY_LABELS and DEFENSE_LABELS remain authoritative; separate Option5 explicitly.
Use backend presentation groups rather than parse combined browser labels.

Tests first cover number/name fields, group spans/dice labels, normalized Special
Teams cells, all-row geometry and read-only controls. Existing previews/dist stay
unchanged until root starts a matched candidate backend/bundle.


Special Teams consultation also reviewed Paydirt `paydirt/chart_loader.py`
(SpecialTeamsChart/parse_special_csv) and its TestSpecialChartValidation. Adapt
explicit CSV column ordering and synthetic marker assertions only. Do not reuse
its extra fumble-return column, NFL call labels, FC/OB/TB meanings or tolerance
for malformed/blank cells. Bowl Bound's six supported special columns and
loaded PAT outcomes remain authoritative. No reference chart values are copied.

The renderer receives explicit column/row groups, play-number/name labels and
dice labels from the engine presenter. Existing flat cell order and combined
row labels remain compatible. Defense uses accessible six-row-group headings
spanning five dice rows. Offense's supplemental block repeats totals beside the
main table; both headers and all 30 rows align. White headings, black grid lines
and strong normalized fills follow the requested board style. Special Teams
preserves BLACK as a procedure marker and supplies its own color/symbol key,
including loaded GOOD/NG PAT results. All help remains closed by default.

Red-first follow-up evidence: two engine group tests initially failed for missing
presentation fields; six Special Teams engine/API cases failed for the missing
table. New board frontend cases initially failed for absent formation and
supplemental groups; Special Teams and launcher assertions failed before their
controls were present. A separate help regression rejected the scrimmage BLACK
incomplete-pass explanation for Special Teams. Grouped-header browser regression
also checks the second sticky header row's offset to keep both header bands
readable on scrolling. Tests retain synthetic facts and compare browser cells
against the actual frozen game response, rather than reference screenshot data.

Changed browser expectations are intentional: offense now has two tables with
30 rows each (the same 360 cells), and defense exposes separate formation letters
and 1–5 dice instead of repeating combined A·1 labels. The loaded cell facts,
game rules, engine revision and dice behavior remain unchanged.


Follow-up focused acceptance: 434 engine/API/independent-matrix/documentation
checks pass; all 157 frontend tests pass. Ruff check and format pass (620 files),
production build succeeds using an external private outDir to preserve running
preview bundles. New browser cases compare all displayed cells, formation/dice
semantics, aligned totals and strong fills; Special Teams help has no incomplete
pass claim, and desktop/phone launch controls remain bordered and visible.

Follow-up commands:

```sh
.venv/bin/python -m pytest tests/test_chart_layout.py tests/test_special_chart_view.py tests/test_api_special_chart_view.py tests/test_chart_view.py tests/test_api_charts.py tests/test_priority_view.py tests/test_priority_matrix.py tests/test_priority_docs.py tests/test_issue_tracker.py tests/test_release_player_docs.py -q
npm test --prefix frontend
npm run build --prefix frontend -- --outDir /private/tmp/bb-board-browser-root/frontend/dist --emptyOutDir
```

Focused browser execution uses an ignored config/wrapper serving that external
bundle against the actual engine and synthetic fixtures; the integrated Alpha 7
candidate will run the unchanged standard complete gate against its own matched
backend and default production bundle. Existing preview sessions remain live.

Final follow-up browser acceptance: all 10 cases pass (16.3s), with no skips.
