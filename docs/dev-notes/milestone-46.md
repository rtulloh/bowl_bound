# Milestone 46 browser-only base game

Owner scope is a playable static build with save, restore and export. Season
management and release publication follow separate review. The worktree starts
at `c5fe4d8` on `feature/browser-only`. Track delivery under
[FLOW-007](https://github.com/rtulloh/bowl_bound/issues/219).

## Six slices

Paydirt was consulted at `3ac20be`. Its v1.11 browser work used a Pyodide
worker for the existing Python engine. The later six slices in
`docs/dev-notes/season-ui-design.md` cover checkpoints, an exhibition picker
and four season-management slices. Bowl Bound uses the six browser delivery
stages from FLOW-007 to produce a playable base game with season work deferred.

| Slice | Paydirt reference | Bowl Bound decision |
| --- | --- | --- |
| 1. Feasibility | `docs/dev-notes/release-1.11.0-plan.md` and `419f0d5` | Use pinned Pyodide 0.27.7 and exercise the ordinary Bowl Bound UI and engine on a static origin. |
| 2. Operations | `paydirt-web/backend/browser_bridge.py` | Share game operations with HTTP, including revision checks and the engine replay save codec. Preserve Bowl Bound's control and chart rules. |
| 3. Worker and assets | `paydirt-web/frontend/src/runtime/python.worker.js` and `scripts/build_browser_spike.py` | Use a serial worker and hash-verified assets. Stage the fictional sample teams from the release manifest and self-host the pinned runtime. |
| 4. Checkpoints | `paydirt-web/frontend/src/runtime/checkpoints.js` and `gameLibrary.js` | Store named single-game checkpoints and control mode in IndexedDB and preserve opaque engine save text through export and import. |
| 5. Browser qualification | `paydirt-web/frontend/e2e/checkpoint-recovery.spec.js` | Exercise real engine progression, save acknowledgements, reload and transfer to a fresh browser profile, with no HTTP API calls. |
| 6. Build and review | `docs/dev-notes/release-1.11.0-plan.md` and browser Playwright config | Document the local build, check package boundaries and retain a reproducible browser test. Release testing and publication are separate. |

The existing React frontend and rules engine remain the implementation used by
both transports. The static build needs only a file host at runtime. The selected
catalog contains the two 2007 fictional teams, Cedar Valley and Harbor Tech.
Published generated charts and private working assets are outside this first
browser catalog.

The older evaluation proposed a PyScript comparison and extensive platform and
performance measurements. The owner directed a working build following Paydirt.
Local validation is scoped to that build and individual game saves.

## Focused acceptance

- `npm --prefix frontend run build:browser` and
  `python -m scripts.build_browser_bundle --output frontend/dist-browser/browser`
  produced 18 files totaling 16,266,565 uncompressed bytes. The staged archive
  contains 54 allowlisted entries, including 15 pinned sample assets. Both
  CDN download and local runtime staging produced archive SHA-256
  `a1f8ad53804ebb02ab7cfe37933a575c9faa3ce5f98398e193117fa7b029ae81`.
- `python -m pytest -q tests/test_browser_bridge.py tests/test_browser_bundle.py`
  passed 7 tests. Coverage includes deterministic staging, private-input
  exclusion, exact seed preservation, pending-choice replay and raw save
  interchange with the HTTP adapter.
- `npm --prefix frontend test -- src/runtime src/test/browserSaves.test.jsx`
  passed 5 tests for worker messaging, failure handling and browser saves.
- `npm --prefix frontend run test:e2e:browser` passed with Playwright Chromium
  149 using a local launch override for `--single-process --disable-gpu`.
  Default Chromium launch was blocked by macOS Mach port permissions. The
  focused check used a static site at a subpath, played through kickoff, waited
  for the local checkpoint, reloaded, resumed, exported, and imported into a
  separately launched browser. It verified the clock and play history and
  observed zero HTTP API calls and uncaught page errors.
- Ruff lint and format checks for changed Python files and `git diff --check`
  passed.

The full regression gate is deferred to upstream at the owner's direction.
Additional browser targets, owner play-testing and published-asset verification
remain release work.
