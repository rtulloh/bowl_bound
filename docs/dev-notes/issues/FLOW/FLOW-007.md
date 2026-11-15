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
