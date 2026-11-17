---
id: FLOW-007
title: Evaluate browser-only Bowl Bound using Pyodide/PyScript and WebAssembly
status: open
priority: Low
milestone: '46'
created-at: 2026-11-15
resolved-at: null
closed-at: null
tags:
- investigating
- browser-only
- pyodide
- cross-project
links: []
commits: []
---

## Description

Evaluate the proposal to offer a browser-only Bowl Bound distribution that runs the existing Python engine, rules and chart loading client-side through Pyodide or PyScript instead of requiring a local Python backend. This mirrors Paydirt FLOW-033 and is intended to be explored for both games. Two possible paths: a static PyScript prototype embedded in HTML, and a Pyodide runtime in a Web Worker behind the existing frontend or a lightweight Vite bundle. Expected trade-offs need measured evidence: first-load WebAssembly/runtime size and caching, browser startup and simulation performance, virtual filesystem and save persistence, static chart/season asset loading, browser compatibility, offline behavior, and the effect on the current CLI, web backend, packaging and release process.

## Resolution / verification

- Run a time-boxed feasibility spike that loads the existing core engine under Pyodide or PyScript in an isolated browser context, using only public sample teams, and record startup, package size and basic play-path results.
- Inventory runtime assumptions that may block or complicate browser execution: Python version, standard-library use, path and filesystem access, threading, process/environment dependencies, subprocess use, native or optional packages, chart/season asset layout, save/load and standings persistence, and any browser-incompatible code.
- Compare the static PyScript prototype with a Pyodide plus Web Worker/React or Vite architecture. Cover load time, memory, UI responsiveness, caching/offline behavior, browser support, debugging, automated testing and maintainability; do not assume zero rewrites or a short delivery until the spike proves it.
- Define how public charts, season rules, rosters, saves and standings would be packaged or persisted in the browser, including IndexedDB or browser filesystem options, and explicitly keep private chart/source material out of any static publication.
- Document what a browser-only build would preserve or lose compared with the current CLI, Python-backed web app, desktop packaging and required full-regression/release verification. Produce a recommendation, effort estimate and follow-up tickets, or record why the approach is not worth pursuing.
- Record the Paydirt FLOW-033 consultation, what is shared across both games, and what is deliberately not reused.

## Comments

--- 2026-11-15 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-15 — Paydirt FLOW-033 consultation ---

Copied and adapted from local Paydirt `docs/dev-notes/issues/FLOW/FLOW-033.md`
(open, Low, created 2026-11-14). The proposal, the two candidate architectures
(static PyScript prototype; Pyodide in a Web Worker behind the existing frontend
or a lightweight Vite bundle) and the trade-off list are shared across both
games. The owner intends to explore this for Bowl Bound and Paydirt together, so
findings should be recorded in a form that can be compared across the two
projects.

Bowl Bound-specific starting facts from a read-only inspection of the current
tree (not spike evidence):

- The engine package depends only on the standard library plus `pyyaml`; the
  importer's `pdfplumber`/`reportlab` and the web stack's `fastapi`/`uvicorn` are
  optional extras, not engine imports.
- `bowl_bound/team_csv.py` reads team bundles from a `Path`-based seasons root;
  `backend/app.py` passes that root into `TeamCatalog` and `SavedGame`. A browser
  build needs a virtual filesystem or a fetch-backed loader for
  `seasons/<season>/<team>/` and `seasons/<season>/provenance/`.
- `bowl_bound/save_game.py` and `backend/app.py` use `threading.RLock`;
  `backend/launcher.py` uses `socket`, `webbrowser` and a background thread.
  These are backend/launcher concerns, but the spike must confirm the engine
  itself has no blocking threading or socket assumptions.
- The frontend is Vite/React and already talks to a thin JSON API, so a Pyodide
  worker could sit behind the same request shapes without changing the UI
  contract.
- Public distribution is constrained: only the fictional Cedar Valley/Harbor
  Tech samples and the exact approved generated 2007 manifest may be published.
  A static browser build must not copy the local `seasons/` tree or include
  private PDFs, imported charts, rosters, saves or audit logs.

Deliberately not reused: Paydirt's NFL rules, season data, private charts, API
and packaging assumptions, and any runtime dependency on Paydirt. This ticket
does not change version metadata, packaging, publication or dependencies.


--- 2026-11-16 21:53 UTC ---

### Recommendation and implementation plan

**Recommend a bounded feasibility spike for Pyodide in one dedicated Web Worker
behind the existing React/Vite frontend.** Keep the Python engine, rules,
normalization, coaching, commentary and save codec authoritative. Offer the
browser build as an additional distribution if the spike passes; retain the CLI,
FastAPI web application and native packages. A separate PyScript page is useful
as a small comparison, but rebuilding the existing UI around Python-in-HTML
would create avoidable presentation and testing work.

This is a recommendation based on source inspection and official documentation,
**not an executed spike or proof of browser compatibility**. No runtime,
dependency, packaging or release changes were made for this investigation.
FLOW-007 stays **open, Low priority, milestone 46**, outside the active v1.1.0
cross-season release scope, as the
[roadmap specifies](../../project-plan.md#46-evaluate-a-browser-only-distribution-with-pyodide-or-pyscript).
It does not block that release. Reconsider priority only with a demonstrated
distribution need and an explicit scope decision.

### Evidence and constraints

Reviewed Bowl Bound at checkout `e218fd95942eecbd1f82b50111718b6c996d1a0a`,
including the existing uncommitted dependency/roster documentation; these are
working-tree observations, not claims about a new published artifact.

| Area | Inspected evidence | Consequence |
| --- | --- | --- |
| Engine dependencies | `pyproject.toml`, `bowl_bound/save_game.py`, `bowl_bound/team_csv.py` | The engine needs the standard library and PyYAML. FastAPI/Uvicorn, PDF tooling and the recovered DuckDB generator are separate extras/tools; exclude them from the browser execution bundle. Generation/import remains a development process. |
| Frontend seam | `frontend/src/api.js`, `frontend/vite.config.js`, `docs/api.md` | Existing async functions return JSON views or raw save text. Introduce a selectable worker transport at this seam, retaining the HTTP transport and component-facing contract. Current Vite development proxy targets the local backend. |
| Application service | `backend/app.py` request models, `create_app`, `_report_data`, `_view_data` | Validation, session registration/control, revision handling, error mapping and presentation serialization are embedded in FastAPI handlers. They are not already a framework-free callable API. Extract reusable Python operations with contract tests; do not import FastAPI into the worker or duplicate these policies in JavaScript. |
| Assets | `bowl_bound/team_catalog.py`, `bowl_bound/team_csv.py:load_team`, `bowl_bound/roster.py` | Loaders use ordinary paths, exact CSV/YAML formats and per-team provenance CSVs. Populate a virtual `seasons/<year>/` tree so the existing loaders can validate it. Do not discard provenance or substitute a new JavaScript chart parser. |
| Synchronization | `bowl_bound/save_game.py` constructs and re-enters an `RLock`; `backend/app.py` has registry locking and threadpool calls | The save wrapper is part of the execution path, not merely a launcher concern. Test lock construction/re-entry, hashing and replay in the selected Wasm runtime. A worker is not permission to remove native locks. |
| Versioned saves | `bowl_bound/save_game.py:_validate`, `tests/test_save_game.py:test_save_from_different_python_minor_version_is_rejected`, `docs/saves.md` | Saves require the same Python major/minor and matching chart fingerprints. Preserve Python 3.12 as requested. Browser/native save interchange is a gate, not an assumed benefit. |
| Native-only concerns | `backend/launcher.py`, `bowl_bound/cli.py`, `scripts/release_package.py` | Socket serving, opening a browser, terminal input and native package assembly stay in their current paths; they are not browser entry points. |
| Persistent seasons | Roadmap milestone 43 / DATA-065; local season runner tests | Persistent played-season management is separate planned work. Do not invent a browser-only standings implementation. A future browser store must persist the same engine-backed campaign records with duplicate-final protection. |

Official documentation checked on 2026-11-16:

- Pyodide documents worker execution to keep synchronous Python away from the
  UI and describes the separate worker/DOM contexts. A basic asynchronous
  message boundary is appropriate here.
  [Pyodide worker guide](https://pyodide.org/en/0.27.7/usage/webworker.html).
- The 0.27 release line moved to **Python 3.12.7**, and the 0.27.7 package catalog
  includes **PyYAML 6.0.2**. Use **0.27.7 as the initial, exactly pinned
  compatibility candidate**, verifying `sys.version_info` in the spike.
  The stable changelog now describes Python 3.14 and changed worker loading;
  never resolve a floating `latest` runtime or silently upgrade Python.
  These documents establish availability, not maintenance/security suitability
  of an older runtime for a new public build.
  [0.27 changelog](https://pyodide.org/en/0.27.7/project/changelog.html),
  [package catalog](https://pyodide.org/en/0.27.7/usage/packages-in-pyodide.html),
  [current changelog](https://pyodide.org/en/stable/project/changelog.html).
- Pyodide documents restrictions on starting Python threads/processes; that does
  not establish that a same-thread reentrant lock is unusable. Test the actual
  save-wrapper path before proposing changes.
  [Pyodide threading FAQ](https://pyodide.org/en/stable/usage/faq.html#can-i-use-threading-multiprocessing-subprocess).
- PyScript is also capable of worker execution. Its documented
  `sync_main_only` option avoids the shared-buffer/header requirements for
  restricted calls; do not characterize cross-origin isolation as mandatory for
  every PyScript or worker deployment. The comparison must pin a compatible
  PyScript/Pyodide pair.
  [PyScript 2026.3.1 configuration](https://docs.pyscript.net/2026.3.1/user-guide/configuration/#sync_main_only),
  [workers](https://docs.pyscript.net/2026.3.1/user-guide/workers/).
- Pyodide's default MEMFS disappears on reload. IndexedDB/IDBFS can support
  persistence; filesystem-backed persistence requires synchronization.
  Browser storage has quotas and eviction, and persistence requests can be
  denied. Keep explicit save downloads as the portable backup.
  [Pyodide filesystem](https://pyodide.org/en/0.27.7/usage/file-system.html),
  [browser storage behavior](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria).
- Offline service-worker caching requires HTTPS or a trusted local development
  origin. This is a static website distribution, not a promise that
  double-clicking an HTML file works. Keep caching separate from the dedicated
  gameplay worker.
  [Service-worker deployment](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers).

### Alternatives and trade-offs

| Option | Benefit | Cost or limitation | Recommendation |
| --- | --- | --- | --- |
| Pinned Pyodide worker + current React/Vite | Reuses the engine and UI; explicit async transport and lifecycle; isolates simulation from rendering | Runtime download, application-service extraction, asset staging, persistence and new browser qualification remain work | Preferred candidate, subject to spike gates |
| Small static PyScript page | Quick way to compare engine bootstrap and basic play without the whole application | Still needs a Python runtime/assets; an independent UI would duplicate interaction work; worker/header behavior depends on configuration | Comparison only, capped at two spike hours; retain if measured simplicity outweighs integration cost |
| Existing local FastAPI/native distribution | Established execution, filesystem and release-validation paths | Requires installation and a local process | Continue supporting; fallback if browser feasibility fails |
| Python on the UI thread | Smallest bootstrapping example | Synchronous engine work can block controls and rendering | Do not use as the production architecture |
| Rewrite/transpile gameplay into JavaScript or move it into a service worker | Different deployment options | Creates another rules implementation or couples live games to a different worker lifecycle | Outside this proposal; Python engine remains authoritative |

Expected maintenance savings from one engine/UI are an inference. Startup cost,
memory, mobile reliability, simulation speed and the size of the extraction have
not been measured.

### Proposed runtime and data design

React calls the existing `api.js` functions. In browser mode those functions
send versioned, request-ID-bearing messages to a dedicated module worker, which
loads pinned Pyodide, the exact engine bundle and a small Python application
adapter. The adapter calls `SavedGame`, `TeamCatalog`, `rules_summary` and
the same serialization/control code used by FastAPI. JavaScript handles
transport, loading and storage only; rules, legal actions, clocks, scoring,
statistics, traces, AI choices and commentary remain Python decisions.

Serialize mutating operations and save/load in a worker queue, including across
asynchronous asset fetches. Preserve `human_side`, control-mode restrictions,
`expected_revision` conflict behavior, size limits, validation and errors.
Expose fixed operations only, not an arbitrary Python evaluation RPC. Add
booting/ready/failed states, bounded requests and a restart path. A timeout is
not evidence that a mutation failed: do not blindly retry snaps or choices.
If recovery requires worker termination, retain the last acknowledged checkpoint
and disclose any unacknowledged action; termination provides no cleanup period.
[Worker termination semantics](https://developer.mozilla.org/en-US/docs/Web/API/Worker/terminate).

For assets, derive a **browser-specific exact allowlist and hashes** from the
reviewed release inputs. Stage engine code, pinned runtime/PyYAML, license and
attribution files, sample team bundles and necessary provenance. The first
spike uses only fictional Cedar Valley and Harbor Tech. A later build may
select already approved generated files, or reviewed historical roster files
once individually pinned under the owner's current authorization. The current
manifest contains 116 generated 2007 teams; this is neither a mandate to preload
all of them nor clearance for neighboring files.

Never publish the working `seasons/` tree, raw PBP, source narratives/PDFs,
imported benchmark charts, acquisition pages, audits or player saves. A static
asset is publicly downloadable even if absent from the picker. Build an explicit
catalog rather than assuming directory listings; fetch selected team bundles
lazily, verify their hashes, and hydrate their complete paths in MEMFS before
ordinary Python loading. Keep the catalog equal to the selected browser manifest.

Start persistence with exact save-text download/upload using the existing
`dumps_game`/`loads_game` validation. Transfer save JSON as an opaque string:
JavaScript must not parse/reserialize large integer seeds or alter integrity
hashes. Add optional autosave through an IndexedDB transaction only after this
works; acknowledge persistence after commit, retain the previous valid checkpoint
on failure, and load into a separate session before replacing the active game.
Test native 3.12 → browser → native continuation. Matching minor versions alone
do not prove matching replay/dice behavior.

Prefer direct IndexedDB storage of save text to mirroring all assets through
IDBFS; the latter adds synchronization lifecycle work and remains an alternative
if measurements justify it. Give browser builds their own versioned storage/cache
namespace, separate from Paydirt if hosted on the same origin. Keep saves out of
public caches, logs and telemetry. Future campaign persistence must reuse the
canonical milestone-43 model; it is not included in the initial browser demo.
Private chart import, arbitrary local folder access, PDF import/generation,
cloud sync and multiplayer are out of initial scope.

### Bounded feasibility spike and decision gates

Time box: **two engineering days / 16 hours**, including at most two hours for
the PyScript comparison. Use an isolated development entry point, synthetic or
approved fictional samples, native Python 3.12 as the reference, and exact
runtime/engine/asset hashes. Do not publish the prototype. Stop at the time box
with a go/no-go report and unresolved blockers rather than extending into a UI
rewrite or custom Wasm toolchain.

Day 1: inventory/import the real execution graph; confirm Python/PyYAML, hashes,
random state, nested locks, loaders and save replay; hydrate both fictional
teams; exercise kickoff, scrimmage, a pending choice, save/load and continuation.
Day 2: compare the minimal PyScript path; run deterministic parity and failure
cases; collect cold/warm performance and a small persistence/offline experiment.
No production refactor is required to prove the initial engine import/play path;
track extraction work separately.

The following are **proposed acceptance targets, not observed results or approved
support promises**. Freeze the matrix and targets before implementation; record
every raw value, failure, exclusion and browser/device version.

| Gate | Measurement / acceptance |
| --- | --- |
| Runtime feasibility | Exact Python 3.12 runtime imports the engine and PyYAML; real team/provenance loaders, `RLock` re-entry, SHA-256, random-state round trip and saves work. No FastAPI server, subprocess or Python thread start is needed. Record runtime provenance and unresolved support/security issues. |
| Deterministic correctness | Same scripted faces and commands match native views/reports, called/resolved plays, score, possession, clock, statistics, legal choices and traces after every step. Cover ordinary play, return/fumble/penalty continuations, halftime, overtime, coached actions and a complete synthetic regulation game. Separately enumerate all 216 offensive and 36 defensive physical combinations through the relevant dice tests. |
| Saves and validation | Native↔browser 3.12 round trips continue identically; preserve raw large-integer save text. Changed teams/digests, invalid or oversized saves and duplicate/stale coached requests fail without changing the active session. Distinguish volatile memory from a confirmed IndexedDB commit. |
| Initial download/startup | Measure compressed transfer, uncompressed staged bytes and dependency breakdown separately. Proposed two-sample first-play budget: at most 25 MiB transferred and cold p95 ≤30 s on a declared 10 Mbit/s, 40 ms RTT desktop profile; warm p95 ≤5 s. Collect 20 cold and 20 warm runs per tested desktop browser and report distributions, not one favorable run. |
| Play/UI responsiveness | Proposed ordinary-command p95 ≤200 ms over at least 200 commands after load; main-thread heartbeat gaps ≤100 ms during worker simulations. Report full synthetic-game time and target ≤30 s on declared desktop hardware. Measure device-specific results separately; emulated CPU throttling is not physical-mobile evidence. |
| Memory | Record Wasm linear-memory allocation and available browser/process measurements with their limits. Compare baseline and five equal batches totaling ten games after dropping old sessions/proxies; investigate monotonic retained growth and target ≤10% growth across the final three equal batches. No blanket memory-cap claim until comparable measurements exist. |
| Persistence/offline/recovery | After a confirmed installation/download, a network-disabled reload can start/resume both sample teams. Test first visit offline, missing assets, blocked/quota-limited storage, corrupt checkpoints, worker crash and interrupted update. Never report an uncached catalog/team as offline-ready or silently mix asset versions. |
| Browsers | Run Playwright Chromium/Firefox/WebKit. Also check real Safari plus a physical iOS/Android device if mobile support is proposed. Record unavailable targets as gaps; Playwright WebKit is not proof of Safari/iOS qualification. |

Stop/recommend defer if import/replay needs engine rule changes, a custom Python
build, relaxed save validation, unreviewed assets, unresolved runtime-maintenance
risk, or materially misses agreed usability budgets. A partial proof is a
documented result, not milestone completion.

### Ordered delivery plan if the spike supports proceeding

These are proposed follow-up work items, **not new tickets already created or
authorization to implement them in this investigation**. Reconsult Paydirt at
each accepted milestone. Write synthetic regression tests first for behavior
changes and demonstrate the expected failure before implementing. Use separately
reviewable commits; assign any delivery beyond the milestone-46 evaluation
through the roadmap rather than silently expanding its scope.

| Order | Work and affected paths | Completion evidence | Estimate |
| --- | --- | --- | --- |
| 1 | Feasibility/ADR: isolated proposed `tools/browser_spike/`, `docs/dev-notes/milestone-46.md`; append results here | Exact versions, dependency inventory, measurements, parity receipts, architecture comparison and explicit go/no-go; review/commit evaluation before delivery | 2 days |
| 2 | Framework-free service: proposed `bowl_bound/application.py`, `backend/app.py`, `tests/test_application.py`; preserve existing API/save/control tests | Both transports use the same validation, session/control operations and view serialization. HTTP bodies/errors, size boundaries, manual/coached controls and revision conflicts remain covered | 2–3 days |
| 3 | Browser transport/assets: `frontend/src/api.js`, proposed `frontend/src/transports/{http,worker}.js`, `frontend/src/workers/engine.worker.js`, `frontend/vite.config.js`, proposed `scripts/build_browser_bundle.py` and `release/browser-manifest.json` | Exact allowlist/hash staging; Python-only engine execution; missing/hash-mismatched assets fail clearly; loading/restart/error UI; no private files or unwanted optional dependencies | 2–4 days |
| 4 | Storage/offline: proposed `frontend/src/browserStorage.js`, `frontend/public/sw.js`, save/load controls and focused unit/browser tests | Opaque-text save interchange, transactional checkpoints, quota/denial recovery, versioned cache installs, offline readiness and two-tab/update behavior | 3–5 days |
| 5 | Browser/native parity and qualification: `tests/test_save_game.py`, `tests/test_api_control_contract.py`, `frontend/src/test/`, `frontend/e2e/`, `frontend/playwright.config.js`, packaging tests and proposed browser CI workflow | Identical synthetic reference transcripts, benchmark matrix, failure tests, catalog equality and privacy injection tests; real browser evidence and all unavailable targets disclosed | 3–5 days |
| 6 | Documentation and separately reviewed release integration: `docs/web-demo.md`, `docs/saves.md`, `docs/rosters.md`, `docs/dev-notes/release-builds.md`, `scripts/run_full_regression.py`, relevant workflows/manifests | User-facing browser/native limits, offline/storage/export behavior, pinned notices/digests, retained native/CLI gates and tested published static bytes before any new distribution claim | 1–3 days |

Planning estimate: **13–22 engineering days including the spike**, roughly
3–6 calendar weeks for one developer allowing review and platform access.
Assumptions: no rules rewrite, no custom runtime build, the existing UI can keep
its contract, public assets are ready, and desktop browsers are the first target.
A Python-runtime maintenance solution, campaign feature, broad mobile support or
private chart import requires separate estimation. These numbers are judgment
from the inspected seams, not measured implementation velocity or a release date.

Keep the established `.venv/bin/python scripts/run_full_regression.py` gate,
upstream coverage and native published-artifact smoke checks. Add browser-mode
unit/contract/E2E and static artifact/privacy checks; do not replace real-engine
tests with mocked worker replies. Existing E2E tests that intercept `/api/`
requests or seed fixtures need an equivalent worker harness. In the eventual
browser release check, download the actual static assets, verify hashes/catalog,
start a real game, save/reload and exercise offline/update failures.

### Paydirt consultation and shared scope

Reviewed local Paydirt at `7a8cd866145237e36649055d467b3bc48e6cdb63`:
`docs/dev-notes/issues/FLOW/FLOW-033.md`,
`paydirt/save_game.py`, `tests/test_save_game.py`,
`paydirt/standings.py:StandingsManager`,
`paydirt-web/backend/routes.py:save_replay/load_replay`, and
`paydirt-web/frontend/src/store/gameStore.js`.

FLOW-033 is an open exploratory proposal, not evidence of a completed browser
runtime. The inspected save/standings code uses disk paths and JSON; web replay
also handles restoration and historical state repair in routes. Share the
benchmark schema, runtime/asset pinning approach, worker lifecycle experiments,
storage-failure matrix and licensing check method across both investigations.
Evaluate a common small bootstrap/transport helper only after both games prove
the same need, with copied/vendored MIT attribution or a separately reviewed
package; introduce no Paydirt repository runtime dependency.

Deliberately do not reuse Paydirt's NFL rules, game-state store, chart formats,
private teams, filesystem defaults, snapshot save schema, season-detection
fallback or prose-based replay repair. Bowl Bound already has strict
season-qualified IDs, chart fingerprints and command/observed-roll replay;
preserve those stronger local contracts and engine-owned state.

### Remaining decisions and verification of this planning change

Before delivery, decide: whether the pinned Python-3.12 runtime has an acceptable
support/patching path; the supported desktop/mobile matrix and reference hardware;
the agreed performance budgets; explicit export-only versus autosave scope;
initial exact public catalog; static hosting/base path and update policy; and
whether any helper actually merits sharing with Paydirt. A newer Python runtime
would require an explicit separate decision and save-compatibility work; it is
not part of this recommendation.

This comment adds planning documentation only. No spike, benchmark, browser game,
dependency installation, implementation, commit, push or external ticket update
was performed. Ticket metadata/status and prior comments are preserved. The
delegated scope owns only this file; the coordinating agent retains issue-index
regeneration/review responsibility.

Validation for this documentation-only change:

- `.venv/bin/python -m pytest tests/test_issue_tracker.py -q` — **18 passed**;
  includes validation of the real ticket collection and generated-index freshness.
- `git diff --check -- docs/dev-notes/issues/FLOW/FLOW-007.md` — passed.
- Verified the entire original ticket is an unchanged byte-for-byte prefix and
  every local Markdown link target exists. Confirmed the issue-index bytes are
  unchanged; no index regeneration was performed within this delegated scope.
- No gameplay or browser tests were run for this planning-only edit, and no
  startup, size, performance or compatibility measurements are claimed.
