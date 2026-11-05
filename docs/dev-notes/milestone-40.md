# Milestone 40 — Priority and full-page chart views

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

All four objectives satisfy their documented synthetic, API, frontend and
real-engine browser checks. Original fictional CSV screenshots provide the
reviewable result. Reading either team, switching any reference, closing help
or opening/dismissing independent windows changes no game/save state and
reveals no selected computer call. The main game remains playable while a
detached chart stays open. No release, merge, tag or push was performed.

UI-062 through UI-065 await owner play-test confirmation before closure.
