# Milestone 33 — Core playability and validation status

## Scope

The owner prioritized five gameplay and fairness tickets for the next milestone:
[AI-027](issues/AI/AI-027.md), [RULE-041](issues/RULE/RULE-041.md),
[RULE-042](issues/RULE/RULE-042.md), [UI-041](issues/UI/UI-041.md), and
[AI-010](issues/AI/AI-010.md). [DEV-059](issues/DEV/DEV-059.md) is included so
routine validation and the slower standalone release build have clear, separate
GitHub status.

[DEV-060](issues/DEV/DEV-060.md) is a focused packaging repair for the reported
standalone-build failure, independent of the pending gameplay and workflow work.
[DEV-061](issues/DEV/DEV-061.md) tracks missing runtime modules exposed by the
next native smoke run.

Milestone 32 remains completed. Imported teams, historical charts, rosters, and
local audit output remain private and excluded from ordinary test collection,
packages, and releases.

## Paydirt consultation — 2026-11-02

Reviewed local Paydirt sources before planning:

- `tests/test_ai_offense_variety.py` demonstrates deterministic coaching tests
  that assert selection leaves gameplay randomness and call history unchanged.
  Adapt these invariants with Bowl Bound synthetic charts; do not reuse NFL
  policies or engine behavior.
- `tests/test_timeouts.py` and `tests/test_flagged_play_timing.py` distinguish
  timeout ownership, halftime resets, and timing after a flagged play. Adapt the
  test shape only. Bowl Bound's engine remains authoritative for its rules.
- `tests/test_ci_workflow.py` statically checks workflow jobs and setup inputs.
  Adapt static workflow validation to Bowl Bound's own regression and packaging
  commands.
- Paydirt's documented fourth-down bands are a design comparison only. Bowl Bound
  will use the owner-approved public policy and will not inspect a kicker chart
  when the CPU chooses among punt, field goal, or scrimmage actions.

No Paydirt source code, team data, or runtime dependency is reused.

The implementation pass independently reread Paydirt's
`tests/test_ai_offense_variety.py`, `tests/test_ai_trailing_defense.py`, and
`tests/test_ai_mode_consistency.py` before AI-010. Adapted exact categorical
probability checks, coaching RNG isolation, committed-history invariants, and
one-coach-per-CLI-game instrumentation. The NFL call families, probability
weights, clock decisions, and field-position policies are deliberately excluded;
the tests exercise Bowl Bound's versioned behavior profiles and synthetic charts.

## Dependency order

1. Establish the AI-010 deterministic regression harness needed by the gameplay
   changes.
2. Implement and test RULE-041 recovery-before-penalty ordering.
3. Implement and test the public fourth-down policy (AI-027), then player-visible
   fairness support (UI-041).
4. Implement RULE-042 pre-play timeout arming across engine, interfaces, and
   save/load.
5. Split and rename GitHub workflow status (DEV-059), then rerun the full
   regression gate and the private local-season audit.

## Acceptance record

Pending implementation.

## AI-010 — Coaching contract harness

Added `tests/test_coaching_invariants.py` with synthetic charts only. It checks
all three tiers' hidden-call independence and pending penalty, conversion, and
overtime save/replay; Hard preview/rejection history purity; exact counters and
bounded recent/situational histories after 220 actual snaps across both teams;
and selection purity through scrimmage, kicks, kneel, Hail Mary, tries, and
decision branches. Cache checks assert tuple identity, true LRU refresh/eviction,
and opponent-count sensitivity. Other checks cover private-plan fallback flags
and reset, exact exploration/exploitation weights, exact Medium group weights
and symbolic-chart fallback, and one coach instance per new/resumed CLI game.

`scripts/audit_coaching_contracts.py` copies only source and public tests to a
temporary directory, injects one fault at a time, and requires the corresponding
regression to fail an assertion. It never mutates the live checkout or copies
local seasons/private data. The 17 faults cover preview/rejection learning,
pending-save and long-history loss, concealed-input leakage, gameplay-dice and
chart mutation, selection-history mutation, LRU/key errors, hidden fallback,
omitted exploration/Medium tilt, invented symbolic bias, and repeated CLI coach
construction. Run it with `.venv/bin/python scripts/audit_coaching_contracts.py`.

The 75 new cases pass against unchanged production. The mutation audit
detects all 17 faults. No gameplay behavior or existing expectation changes.

Validation:

- `.venv/bin/python -m pytest tests/test_coaching_invariants.py -q`: **75 passed
  in 6.94s**; includes unmocked Hard analysis for both roles.
- `.venv/bin/python -m pytest tests/test_coaching*.py tests/test_difficulty*.py tests/test_chart_coaching.py tests/test_cli.py -q`:
  **418 passed in 72.22s** (the two additional unmocked-analysis cases were
  validated by the focused run above).
- `.venv/bin/python scripts/audit_coaching_contracts.py`: clean baseline passes;
  **17/17 deliberate faults detected by assertions**.
- `.venv/bin/python -m pytest tests/test_issue_tracker.py -q`: **18 passed**.
- `.venv/bin/python -m ruff check .` and
  `.venv/bin/python -m ruff format --check .`: passed; **530 files** formatted.

No skips or warnings in these checks. The milestone-wide gate remains pending.

## DEV-060 — Stale sample metadata hashes (2026-11-02)

Consulted local Paydirt `.github/workflows/release.yml` and
`tests/test_ci_workflow.py` before this repair. Adapt its early required validation
and repository-configuration regression approach. Paydirt has no corresponding
pinned sample manifest in that workflow: keep Bowl Bound's exact public allowlist
and strict byte checks rather than its broad staging or automatic release policy.
No Paydirt data, rules, code, or runtime dependency is reused.

The upstream [standalone run](https://github.com/rtulloh/bowl_bound/actions/runs/41528902829)
at `98eb443` passed source tests but failed staging on all three native targets.
`08b905b` renamed the two fictional teams' `privileges` metadata to
`defense_chart_markers` and advanced their team-file version from 2 to 4 without
refreshing the release hashes. Both stale hashes match the files immediately
before that commit; the other 13 approved sample hashes still match.

Added a regression that stages the repository's actual selected public inputs,
asserts the complete public sample set is pinned, and checks the exact staged
inventory. It visits only manifest-selected paths. The synthetic tampering,
private-file exclusion, and checkout-conversion tests remain required. Updated
only the two reviewed YAML hashes; documented hash maintenance in the sample
guide. No existing test expectation changes.

Validation:

- `.venv/bin/python -m pytest tests/test_release_package.py -k real_release_inputs -q`:
  **1 expected failure** before the hash repair, matching the upstream error.
- `.venv/bin/python -m pytest -q tests/test_release_package.py tests/test_release_archive.py tests/test_standalone_build.py tests/test_standalone_smoke.py tests/test_windows_installer.py tests/test_native_notices.py tests/test_sample_teams.py tests/test_sample_playability.py tests/test_build_workflow.py tests/test_issue_tracker.py tests/test_create_issue.py`:
  **199 passed in 5.68s**, no skips or warnings. Includes successful public-input
  staging and synthetic complete-game/save replay coverage for the samples.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: **526 files** already formatted.
- `.venv/bin/python -m pip check`: passed.
- `.venv/bin/python -m pytest -q tests/test_issue_tracker.py tests/test_release_player_docs.py tests/test_priority_docs.py tests/test_packaging.py tests/test_release_metadata.py`:
  **31 passed in 2.62s** after documentation updates; **72 local documentation
  links** verified and `git diff --check` passed.
- Used `.venv/bin/python` with Node **24.22.1** / npm **11.19.1** in a temporary
  directory to run real `stage_sources`, `build_frontend`, `assemble_runtime`,
  and `archive_runtime` calls. The inspected ZIP contained **72 files**, with
  exactly the **15 approved sample files** and no other seasons content. npm
  reported **0 vulnerabilities** and the existing `whatwg-encoding@3.1.1`
  deprecation warning. Temporary outputs were removed automatically.
- `.venv/bin/python scripts/build_issue_index.py`: regenerated the tracker.
  The first attempt with system `python3` failed because it is Python 3.9;
  the project requires Python 3.10+ and the supported virtualenv run succeeded.

This repair does not complete Milestone 33. Native CI confirmation remains
pending publication of the fix; the remaining milestone work stays pending.
Tested implementation commit: `ca3d3bb`; DEV-060 is resolved pending native build
confirmation.

### DEV-060 pre-push gate — 2026-11-02

The owner authorized committing and pushing the repair. Reviewed both outgoing
commits and their seven changed paths: documentation, one public-input regression,
and the release manifest only; no private charts, PDFs, reports, saves, or logs.

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`:
  **3,115 passed in 724.12s**, **92.90% branch-aware coverage** (75% required),
  no skips or Python warnings.
- `.venv/bin/python -m ruff check .`,
  `.venv/bin/python -m ruff format --check .` (**526 files**), and
  `.venv/bin/python -m pip check`: passed.
- From `frontend/`, using Node **24.22.1** / npm **11.19.1**:
  `npm ci --ignore-scripts`, `npm test` (**128 passed, 16 files**),
  `npm run build`, and `npm audit` (**0 vulnerabilities**) passed. npm retained
  the existing `whatwg-encoding@3.1.1` deprecation warning.
- `npx playwright install chromium` succeeded, followed by
  `BB_E2E_SEASONS=/private/tmp/bowl-bound-dev060-push-e2e npm run test:e2e`.
  **All 33 cases failed at browser launch**, before application assertions:
  macOS denied Chromium's MachPortRendezvousServer process registration
  (`bootstrap_check_in`, Permission denied 1100). The existing
  `NO_COLOR`/`FORCE_COLOR` environment warning also appeared. This environment
  cannot supply a successful browser gate; no tests were skipped or weakened.

The browser limitation is recorded rather than treated as a passing full gate.
A fresh hosted standalone workflow must confirm browser and native builds after
the push; DEV-060 remains resolved pending that confirmation.

## DEV-061 — Incomplete application runtime selection (2026-11-02)

Consulted local Paydirt `.github/workflows/release.yml` and
`tests/test_ci_workflow.py` before this follow-up. Adapt the distinction between
source regression and native packaging, with explicit required validation.
Paydirt's broad freezer inputs do not provide Bowl Bound's exact application/data
selection; retain the existing privacy allowlist and add coverage at its boundary.
No Paydirt source, team data, NFL behavior or runtime dependency is reused.

Run [41538136008](https://github.com/rtulloh/bowl_bound/actions/runs/41538136008)
at `28dea63` passed source tests and the real-engine browser gate. All three native
targets successfully staged and froze the app, confirming the DEV-060 hash repair,
then failed the extracted-executable smoke with the launcher's generic
"Web dependencies are missing" message. This was an application selection error,
not an absent installed web distribution.

An isolated macOS ARM64 prototype reproduced the underlying
`ModuleNotFoundError: bowl_bound.decision_facts`. The runtime manifest also omitted
`return_recovery` and `team_catalog`. Adding those allowed startup, but the actual
game-creation smoke exposed the deferred `difficulty` import of
`coaching_situations`. All four are current runtime code and are now explicitly
selected. An AST audit found no other unselected application imports; the two
development-only coaching audit modules remain excluded. No sample hash, privacy
selection, gameplay implementation or smoke expectation changes.

The new regression stages and assembles only approved public inputs with a
synthetic frontend, starts an isolated child interpreter, blocks application
imports from the checkout/editable installation, imports the entry points and
creates a default Medium game with the original fictional samples. It first
failed on `decision_facts`, then failed on `coaching_situations` when expanded to
cover deferred game-creation imports. Both expected failures were demonstrated
before the respective manifest additions. The probe requires a pristine runtime
without generated Python caches.

Validation is recorded below before committing/pushing the repair. This work
does not complete Milestone 33 or begin either parallel feature stream.

Validation:

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`:
  **3,116 passed in 721.67s**, **92.90% branch-aware coverage** (75% required),
  with no skips or Python warnings.
- `.venv/bin/python -m pytest -q tests/test_release_package.py -k real_release_runtime_imports`:
  expected failures on `decision_facts` before repair and on
  `coaching_situations` after adding game-creation coverage, before the fourth
  manifest addition. Existing assertions were retained.
- `.venv/bin/python -m pytest -q tests/test_release_package.py tests/test_release_archive.py tests/test_standalone_build.py tests/test_standalone_smoke.py tests/test_windows_installer.py tests/test_native_notices.py tests/test_sample_teams.py tests/test_sample_playability.py tests/test_build_workflow.py tests/test_issue_tracker.py tests/test_create_issue.py`:
  **200 passed in 7.81s**, no skips or warnings.
- Created an isolated `/private/tmp/bowl-bound-dev061-native-env` with
  `.venv/bin/python -m venv`, then installed
  `--only-binary=:all: --no-deps -r release/requirements-native.txt` using that
  interpreter. Used real `stage_sources`, `build_frontend`, `assemble_runtime`
  and `write_spec` calls under `/private/tmp/bowl-bound-dev061-complete`, with
  pinned Node **24.22.1** / npm **11.19.1**. Ran the environment's Python with
  `-I -B -m PyInstaller --noconfirm --clean --distpath
  /private/tmp/bowl-bound-dev061-complete/dist --workpath
  /private/tmp/bowl-bound-dev061-complete/analysis
  /private/tmp/bowl-bound-dev061-complete/freeze/BowlBound.spec` and
  `PYTHONDONTWRITEBYTECODE=1`. Real `inspect_modules` and `smoke_executable` calls
  passed: version, startup, UI/assets, exact fictional sample catalog, snap,
  save/load and graceful shutdown. The standard launcher entry was unchanged.
  This is an engineering ARM64 prototype under Python **3.12.8**, not the
  workflow's pinned **3.13.17** native-notice/ZIP/installer acceptance. No prototype
  artifact is approved for publication.
- `.venv/bin/python -m ruff check .`,
  `.venv/bin/python -m ruff format --check .` (**528 files**) and
  `.venv/bin/python -m pip check`: passed.
- From `frontend/` with the pinned Node/npm, `npm ci --ignore-scripts`,
  `npm test` (**128 passed, 16 files**), `npm run build` and `npm audit`
  (**0 vulnerabilities**) passed. Existing `whatwg-encoding@3.1.1` deprecation
  and Vitest performance advice remain visible.
- `BB_E2E_SEASONS=/private/tmp/bowl-bound-dev061-e2e npm run test:e2e`:
  **33 failed before application assertions** because this environment denies
  Chromium's macOS process registration (`bootstrap_check_in`, Permission denied
  1100). Existing color-environment warnings also appeared. The reported hosted
  run passed its browser gate; a new hosted run remains required. No browser tests
  were skipped or weakened.
- `.venv/bin/python scripts/build_issue_index.py` and
  `.venv/bin/python -m pytest -q tests/test_issue_tracker.py tests/test_release_package.py`:
  **57 passed in 1.73s** after tracking updates. All **15** selected sample hashes
  match, **75** relative documentation links resolve, and `git diff --check`
  passed.
