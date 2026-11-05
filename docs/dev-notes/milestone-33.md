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
next native smoke run. [DEV-062](issues/DEV/DEV-062.md) corrects the stale
save-guide assertion that normal games enable deferred Advanced II options.
[DEV-063](issues/DEV/DEV-063.md) corrects the local audit’s rejection of valid,
engine-observed overtime series resets discovered during final acceptance.

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

All ten assigned tickets have tested implementations and their engineering
acceptance criteria are satisfied. Automatic
[Tests 41575358111](https://github.com/rtulloh/bowl_bound/actions/runs/41575358111)
passes the complete gate at `eed362c7daacff66c092a11d1ba8a896d1a9a1eb`, including
all 38 real-engine browser cases. The private audit, coaching audits and review
also pass. The records below retain earlier failures and follow-up checks; none
establish owner play-test confirmation or release publication.

| Ticket | Implementation commit | Acceptance evidence / remaining verification |
| --- | --- | --- |
| AI-010 | `33b752d` | 75 contract cases; 17/17 injected faults caught; full coaching and policy audits. |
| RULE-041 | `4b64796` | 47 new recovery/penalty cases; 109 focused hardening/fumble cases; current and legacy replay. |
| AI-027 | `32649b2` | 70 public-policy cases; unchanged approved bands, chart access forbidden at selection. |
| UI-041 | `b4b8fdf` | 29 engine/API/CLI cases, frontend display coverage and all three hosted difficulty/guidance cases pass at `eed362c`. |
| RULE-042 | `3e321f1` | 37 engine/API/CLI/save cases, both side-owned timeout cases and both compact-layout browser cases pass at `eed362c`. |
| DEV-059 | `2b11cd6` | 15 workflow checks; automatic branch Tests passes at `eed362c`; earlier failing run confirms failure propagation. |
| DEV-060 | `ca3d3bb` | Exact sample staging tests and baseline native confirmation on all three targets. |
| DEV-061 | `03d1992` | Isolated staged runtime probe, baseline native/extracted-app/installer confirmation. |
| DEV-062 | `c22df25` | Corrected deferred Advanced II save guidance; save/tracker and full regression pass. |
| DEV-063 | `0a89a68` | 39 local-audit cases; unchanged 120-game audit passes, including strict overtime boundary validation. |

Gameplay tickets await owner play-test confirmation before closure. Existing
DEV-044 and newly recorded DEV-064 frontend warning cleanup remain M23 follow-up;
they do not expand this milestone’s implementation scope.

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

## RULE-041 — Recovery before penalty comparison

Before implementation, reviewed Paydirt's `tests/test_fumble.py` and
`tests/test_flagged_play_timing.py`. Adapt the synthetic recovery/possession
matrix and exactly-once flagged-play timing checks. Do not reuse Paydirt's
recovery ranges, NFL clock charges, return/scoring exceptions, or resolver code.
Bowl Bound's existing turnover resolver supplies the complete prepared facts;
only the session's decision ordering changes.

The session now resolves fumble recovery and any required end-zone/return-foul
consequences before offering the original penalty choice. The engine retains
the completed turnover and return-yardage credit, exposes its known field or
scoring projection, and commits it once on decline. Accepting enforcement
discards the prepared result. Pending views do not alter the field, ledger,
statistics, clock, or play log. Every actually consulted recovery/return roll
appears once in both pending and final traces.

The ordering change requires replay profile `bowl-bound-m33-v1`. Old `m21-v1` and
`m22-v1` journals replay their validated historical command prefix with the old
order; subsequent commands use the corrected order. A legacy save paused before
recovery exposes only `fumble:resolve` until recovery and its consequences are
known. Loading/resaving never draws fresh dice. The normal decision command
records that recovery step, and later saves preserve both the historical prefix
and current continuation. Strict prefix validation and a forged-old-digest
regression prevent the compatibility path from accepting a different final
state. Unsupported `m19-v1` saves remain rejected.

Changed existing expectations include the scrimmage fumble decline label
(completed recovery/possession instead of unresolved recovery), three assertions
of the current replay-profile identifier, and the legacy engine-hardening test’s
recovery-before-decline command chronology documented below. The label fixture now supplies its
recovery roll explicitly before the unchanged sentinel assertion. No assertion
was weakened. Runtime changes remain in already-allowlisted `session.py` and
`save_game.py`; no new module or public sample is staged. Reviewed the exact
runtime manifest and preserved all sample hashes.

Validation:

- Before implementation, **22 expected failures** in the new fumble matrix:
  absent recovery traces, unknown decline projections and too few recorded dice.
  Three additional legacy-journal regressions then reproduced pending/accepted
  replay failure and the obsolete profile identifier before compatibility work.
- `.venv/bin/python -m pytest tests/test_fumble_penalty_order.py -q`:
  **47 passed in 2.28s**. Covers both possessions, offensive/defensive recovery,
  fourth-down consequences, touchdowns/safeties, nested return fouls, prepared
  return-yardage credit, timing/statistics, sentinel dice, current/legacy replay,
  API transport and CLI controls.
- `.venv/bin/python -m pytest tests/test_session*.py tests/test_turnovers.py tests/test_return_fumble_series.py tests/test_penalty_choice_labels.py tests/test_coaching_decisions_v8.py tests/test_save_game.py tests/test_regulation.py tests/test_fumble_penalty_order.py tests/test_api.py tests/test_api_coaching.py tests/test_cli.py tests/test_release_metadata.py tests/test_commentary_replay.py tests/test_coaching_invariants.py -q`:
  **450 passed in 44.73s**; the four subsequently added API/CLI/return-credit cases
  pass in the focused run above.
- `.venv/bin/python scripts/audit_coaching_contracts.py`: clean baseline passes,
  **17/17 faults detected** after updating its codec-helper mutation target.
- `.venv/bin/python -m pytest tests/test_commentary_replay.py tests/test_release_metadata.py tests/test_issue_tracker.py -q`:
  **28 passed in 6.99s**.
- Ruff lint/format passed; **531 files** formatted. No skips or warnings.

Owner play-test confirmation and milestone-wide regression remain pending.

## AI-027 / UI-041 — One public fourth-down policy

Before this phase, independently reviewed Paydirt's
`paydirt/computer_ai.py:311-365` and `tests/test_fourth_down.py`. Its boundary-test
structure is useful. Its historical 1983 NFL rates, random coffin-corner choices,
punt variants and game rules are excluded. The exact Bowl Bound bands remain
those already approved and documented in [coaching](../coaching.md): no new
distance, clock, short-yardage, or aggression policy is introduced.

Current version-10 CPU behavior already implements those bands. AI-027 extracts
them into `coaching.public_fourth_down_call`, accepting only the public observation
and declared aggression/clock threshold. CPU selection and the following UI-041
guidance work use this one engine function. `field_goal_attempt_distance` supplies
the shared public distance. The actual selected kick remains chart-resolved.

AI-027 validation:

- The new shared-policy test initially failed collection because the public
  function did not exist; the existing CPU decision was then extracted without
  changing any policy band or expectation.
- `.venv/bin/python -m pytest tests/test_public_fourth_down.py tests/test_coaching_decisions_v3.py tests/test_coaching_invariants.py tests/test_difficulty.py tests/test_coaching_saves.py -q`:
  **237 passed in 18.95s**. Includes 70 new public-policy cases: all tier/distance
  boundaries with chart reads and evaluation forbidden, late-clock boundaries,
  legal-action filtering, CPU delegation, and saved choice stability while strong
  and weak charts still produce different actual kick outcomes.
- Ruff lint/format passed; **532 files** formatted. No skips or warnings.

The two changed runtime modules were already in the exact release manifest; no
module or sample addition is needed. Owner play-test confirmation, UI-041's
display work and the final milestone gate remain pending.

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


## UI-041 — equivalent public fourth-down guidance

The Paydirt fourth-down code/tests reviewed for AI-027 informed the UI-041
review too; the approved Bowl Bound policy remains authoritative. No NFL make
rates, team-derived kick advice, randomness or special punt variants are reused.
`SavedGame.fourth_down_guidance` uses the same AI-027 public helper with the
normal difficulty's declared profile. It accepts the captured response view so
concurrent API commands cannot attach advice for a different state. API
serialization and browser/CLI rendering contain no football policy. Guidance is
read-only and disappears outside eligible offensive fourth-down scrimmage with
legal kicks. Future public team/season ranges remain outside this milestone.

Test-first evidence: 25 synthetic Python failures on the missing engine method,
and one frontend failure on absent backend wording, before implementation.
Coverage includes both possession sides, all normal difficulties, public distance
bands, short-yardage go, wrong-side/unavailable contexts, chart-read rejection,
repeated-preview dice/journal/history purity, save/load equivalence, atomic-view
use, CLI wording, and API load/get/coached/kick response lifecycle. A frontend
fixture deliberately has first-down state alongside a backend recommendation:
the browser renders the supplied text rather than deriving football meaning.
Full browser execution remains subject to the documented local Chromium sandbox
limitation; fresh branch-hosted coverage is required before final acceptance.


UI-041 focused validation (2026-11-02):
- `.venv/bin/python -m pytest tests/test_fourth_down_guidance.py tests/test_public_fourth_down.py tests/test_coaching_invariants.py tests/test_api.py tests/test_cli.py tests/test_issue_tracker.py -q`: **265 passed in 25.15s**; the new guidance file contains **29 cases**.
- Pinned Node/npm, `frontend/`: `npm test` **129 passed (16 files)**; `npm run build` passed. Focused coaching/no-rules tests: **44 passed**.
- Ruff check and format check passed (**533 files**); `git diff --check` passed.
- Added three real-engine Playwright cases for normal difficulty guidance, three legal snaps, displayed backend facts, save/load and kick clearing. The local focused run failed all three **before assertions** with Chromium `bootstrap_check_in` Permission denied 1100 / SIGTRAP; existing color-environment warnings remained visible. No skips or browser assertion changes. These cases require the fresh branch-hosted browser run before acceptance.
- Review corrected a synthetic short-yardage fixture from a 48-yard attempt (approved policy always kicks there) to 47 yards (Medium fourth-and-one goes). The existing approved bands and production policy were unchanged.
- No runtime module was added; all modified runtime modules already belong to `release/manifest.json`. No sample allowlist/hash or private data changed.


## RULE-042 — armed, side-owned pre-play timeout

Reviewed Paydirt `paydirt-web/backend/routes.py` request/control flow (427–430,
1078–1089, 1186–1191) and `tests/test_timeout_clock_interactions.py`. Adapted the
pre-play interaction and boundary-test strategy; excluded NFL two-minute warnings,
minute clocks, random 35-second play timing and any runtime dependency. The
approved Bowl Bound 10-second timing and three-per-half budgets stay in the engine.

Eligible regulation scrimmage views offer own-side arm/cancel actions, including
after kickoff. Parent confirmed one armed modifier, own cancellation and no
overwrite by the other side. Arming does not commit prior optional timing or
spend dice/budget. The completed legal play consumes it exactly once, logs the
10-second charge and clears it. Pending penalty/kick/RZDZ continuations retain it;
unsupported/invalid actions do not spend it. The no-time elected safety and period
boundaries clear unused arms, preserving existing rules. Existing prior-play
clock decisions and overtime timeouts remain separate. Exhausting the armed
side’s last budget through an explicit prior-play timeout clears the unavailable
arm. Cancel an arm before choosing the separate combined next-spike timing;
no simultaneous next-play clock rule is invented. Safe-kneel queries account for
an armed offensive timeout.

New synthetic tests were red before each discovered behavior correction: absent
post-kickoff actions (17 initial failures), the safe-kneel forecast, prior-delay
period boundary, elected safety’s no-time rule, and combined-spike exclusion.
Corrected two test setup errors (illegal sentinel face, unfinished punt) and the
generic elected safety expectation against the approved rule; documented in
RULE-042. Save tests include pending real Hard RZDZ decisions and reject a forged
unarmed digest for an armed journal. API/CLI tests cover ownership, no overwrite,
preview/save purity, clock/budget changes and replay. Browser fixtures use actual
synthetic engine commands and raw private-seed-preserving save text, never mocked
outcomes. All modified runtime modules already belong to the release manifest.


RULE-042 focused validation (2026-11-02):
- `.venv/bin/python -m pytest tests/test_armed_timeouts.py tests/test_coaching_invariants.py tests/test_regulation.py tests/test_api_regulation.py tests/test_cli_timeout_controls.py tests/test_cli_shortcuts.py tests/test_kneel_safety.py tests/test_save_game.py tests/test_coaching_saves.py tests/test_fumble_penalty_order.py tests/test_fourth_down_guidance.py tests/test_issue_tracker.py -q`: **425 passed in 44.04s**, including **37 new armed-timeout cases**, no skips/warnings.
- Pinned Node/npm in `frontend/`: `npm test` **130 passed (16 files)** and `npm run build` passed. Focused clock/no-rules tests: **22 passed**.
- Ruff check and format check passed (**535 files**), and `git diff --check` passed.
- Added real-engine browser cases for each human side after kickoff: offered own-side arm, unchanged clock/budget, raw-text save/load, legal offensive/defensive call, one 10-second charge and reset. Browser acceptance remains pending the fresh hosted branch run; the local process-launch restriction is not counted as a pass.


## Hosted DEV-060/DEV-061 confirmation

Baseline [run 41558282571](https://github.com/rtulloh/bowl_bound/actions/runs/41558282571)
completed successfully at `03d1992d3a3811cf89879bce985e23937e3a3dc0`: source/browser
test job plus macOS Intel, macOS ARM64 and Windows x64 native jobs all passed.
Applicable extracted-app and Windows installer smoke checks passed. DEV-061 is
now resolved against tested commit `03d1992`; DEV-060 retains tested `ca3d3bb` with
end-to-end native confirmation. Neither is closed on unconfirmed owner play-test.
No release tag, manifest hash or baseline snapshot was changed by this evidence
update. Current milestone changes require fresh branch-hosted browser validation.


## DEV-059 — automatic Tests and manual native release builds

Reviewed local Paydirt `.github/workflows/test.yml` and `release.yml`: reused the
separate workflow purpose/names, while excluding NFL/private audits, mutable
action tags, optional installer failures and automatic publication. Bowl Bound's
complete established source gate is reusable `tests.yml`, with push/PR triggers
for main and isolated workstreams. The native workflow calls it, then performs
the unchanged three-target packaging/installer gate. Its manual dispatch,
read-only permissions, exact pins, artifact-only outputs and explicit publication
boundary are retained.

Checked [GitHub's reusable workflow reference](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)
and [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax):
the local reusable workflow comes from the caller commit; caller/callee
concurrency prefixes differ to avoid cancellation. Full optional source SHA
validation prevents a branch moving between source/native checkouts. No secrets
are passed and token permissions remain read-only. Exact source commit selection
is a build input, not a publication authorization.

Four new regression tests were red before workflow creation; a further red guard
regression preceded immutable-source validation. Six synthetic Bash cases check
SHA/ref validation. Existing assertions follow moved source commands into the
reusable gate and continue to require coverage/browser/pins/failure propagation.
Maintainer docs distinguish automatic source status, manual native acceptance,
and separately authorized publication. Hosted branch validation remains required.


DEV-059 implementation is committed at `2b11cd6`. Focused cumulative packaging/workflow/tracker/metadata validation: **197 passed in 6.35s**, with 11 new workflow cases. Ruff/format (**539 files**) and diff checks passed. The automatic branch-hosted run and final milestone gate remain pending.


Final-gate follow-up: two `test_cli_games` pending-interception API parity cases
were red on the new additive null guidance field. Their expected transport view
now serializes `SavedGame.fourth_down_guidance` while retaining the entire exact
view and future-replay comparison. This changes the API-shape expectation only;
no football or private replay rule changes. The initial full pass is recorded as
failing and the complete gate must rerun after this correction.


The initial full pass also exposed one existing engine-hardening test whose
commands encoded the retired penalty-first order. Its independent regression
reproduced the now-illegal early decline. Updated its command order to recover in
the end zone before offering/declining the original penalty, retaining final
field, exact trace and one committed log entry and adding pre-commit purity
assertions. This completes the intentional expectation migration for RULE-041;
no production behavior changes in this follow-up.


## DEV-063 — strict engine-observed overtime audit boundaries

The first final private season audit completed 120 games, but rejected six at
valid overtime field resets: **114 passed, 6 failed, 0 fallbacks**. The final-view
validator incorrectly required regulation field continuity into and between
overtime series. Detailed game evidence remains private. This is a development
audit defect; no engine, chart, timing policy or coaching behavior changes.

Before this repair, reviewed Paydirt `tests/test_full_season_runner.py` for strict
final/scoring validation and preservation of failing reproductions. Adapt its
failure-accounting discipline, not its NFL schedule, historical seeds, overtime
rules or runtime. Independently reviewed the parallel generator worker’s
`3e699aa` runner correction. Reused only its `OvertimeSeriesStart` evidence and
engine-owned `OvertimeState.next_series` ordering; no generator implementation,
DATA ticket, private input, replay override or policy change is brought here.

The runner records the actual public engine view before the first committed
report of each overtime series. Validation accepts a field reset only with exact
report/state/possession evidence, completed and tied regulation, increasing report
numbers, and the engine’s series order. Ordinary missing/disconnected states,
forged/mismatched/stale/duplicate/premature evidence and non-tied regulation remain
failures. All existing scoring, statistics, traces and four-quarter clock checks
remain. Private game JSON adds `overtime_series_starts`; public outputs and runtime
save formats are unchanged.

Test-first evidence: two boundary tests initially failed on the absent evidence
type. A separate fictional complete game was run against the unchanged runner
loaded from HEAD: it failed with the same `ValueError` as the six local games.
The corrected runner passes that game with both first-round series recorded.
Adversarial controls then showed the initial reviewed boundary implementation
accepted reversed report numbers and non-tied regulation; both were corrected.
A no-regulation-end test now rejects boundary evidence at that boundary, retaining
the independent clock reconciliation too. No assertion was weakened or skipped.

Focused validation: `.venv/bin/python -m pytest tests/test_local_season_runner.py tests/test_overtime.py tests/test_coaching_audit.py tests/test_issue_tracker.py -q`:
**87 passed in 28.31s**. The local-season suite contains 39 cases. Full regression
and the unchanged 120-game private audit must rerun after this committed repair.


DEV-063 tested implementation: `0a89a68`. The unchanged private schedule now
passes **120/120 games, 22,192 reports, 0 fallbacks**, including six overtime games
and 16 engine-observed series. All 120 engine logs, final states, coaching calls,
period scores and configurations exactly match the first run; only audit evidence
and validation changed. No chart or selection adjustment was made. The baseline
policy audit covers all 11 offered offensive calls and six normal formations.
Under the documented comparable public-situation buckets, 2,819 offense/defense
observations repeat 441 prior calls, with a longest streak of three. All 236
team/role/down/distance buckets with at least 20 calls stay below 80% concentration.
These are descriptive baseline observations, not universal usage quotas or a
calibration claim for Medium/Hard. Full normal-tier policy audits run separately.
Detailed reports remain private and are not part of Git history or packaging.


## Final local regression and policy audit

Source implementation is frozen at `0a89a68`; `3d888d9` strengthens the new
series-order test fixture and records private audit evidence. The preceding
runtime gate at `86600a4` passed **3,385 tests in 800.13s**, **93.05% branch-aware
coverage**, without skips or warnings. The complete gate rerun includes
all seven new DEV-063 audit cases: **3,392 passed in 793.00s (13:13)**,
**93.05% branch-aware coverage**, no skips or Python warnings. The strengthened
series-order fixture also passes in the 39-case focused run. The initial **3-failure / 3,382-pass** run is
retained as failing evidence; all three intended expectation migrations were
verified independently before the successful runtime gate.

Fresh available non-Python checks, using Node **24.22.1** / npm **11.19.1**:
`npm ci --ignore-scripts`, `npm test` (**130 passed, 16 files, 5.04s**),
`npm run build` (**590ms**) and `npm audit` (**0 vulnerabilities**) passed.
The existing `whatwg-encoding@3.1.1` deprecation and Vitest performance advice
remain visible. Ruff lint/format (**540 files**), pip dependency check and
tracker (**18 tests**) passed. The final simplify review checked shared helpers,
state retention, response-view consistency, rule authority and workflow controls;
removed an extra workflow EOF blank line and strengthened the audit controls.
All changed runtime paths are manifest-selected; all 15 public sample hashes
match. All 897 local links in changed Markdown resolve. No private inputs,
reports or game saves are tracked in the outgoing changes.

- `.venv/bin/python scripts/audit_coaching_contracts.py`:
  **clean baseline passed; 17/17 deliberate faults detected by assertions**.
- `.venv/bin/python -m bowl_bound.coaching_audit --seeds 101 307 --policies baseline-v2 easy-v10 medium-v10 hard-v10`:
  **32/32 games passed**, eight per policy, both CPU sides and sample arrangements.
  All saved continuations verify (**5,261 replayed commands**); all four regulation
  quarters reconcile to 900 seconds per game; scoring, statistics and **11,726
  trace rolls** reconcile across **5,413 reports**. **Zero illegal selections or
  fallbacks**. All **5,620** committed CPU preference vectors are normalized,
  finite, legal and assign positive probability to the selected call.
- Comparable-call counts/repetitions: baseline **150/21**, Easy **179/25**,
  Medium **191/46**, Hard **186/28**. Longest within-game comparable streak is
  **two** for each policy. All 4,914 per-game situation buckets are below the
  concentration audit’s minimum sample count; no broad balance or calibration
  claim follows. The exact mixture/cache/history/hidden-input contracts are
  separately protected by the AI-010 synthetic suite and mutation audit.
- `.venv/bin/python scripts/run_local_season.py --seasons seasons --games-per-team 12 --seed 20311031 --output private-data/local-season-audits`:
  **120/120 passed**, detailed reconciliation and limitations recorded under
  DEV-063 above. Full game outputs stay in ignored private paths.

Local `BB_E2E_SEASONS=/private/tmp/bowl-bound-m33-full-e2e npm run test:e2e`
attempted all **38 cases**. All failed **before application assertions** because
macOS denies Chromium’s MachPort process registration (`bootstrap_check_in`,
Permission denied 1100 / SIGTRAP). The 38 existing color-environment warnings
remain visible. `npm run test:e2e -- --list` lists **38 tests in seven files**.
No skip, assertion weakening or sandbox bypass was introduced. Fresh hosted
branch Tests/browser confirmation is required; this is not a passing browser gate.


Pre-push status: all available full local checks pass. Local Chromium remains
blocked before assertions as recorded above; fresh hosted Tests/browser coverage
is required before resolving UI-041, RULE-042 and DEV-059 or accepting the whole
milestone. Only `milestone/33-core-playability` is authorized for this push. No
main, release branch, tag, native build or publication is included.


Independent read-only integration review of `03d1992..d518ba2` by the parallel
college-generator worker found no blocking mismatch in `session.py`,
`regulation.py`, `save_game.py`, the shared policy/difficulty wrapper, or API/CLI
guidance. The review checked deferred recovery/return credit across nested
continuations, discarded accepted outcomes, exactly-once traces, legacy prefix
upgrades/digests without load-time draws, armed side/timing/reset/exhaustion/spike
behavior, and captured-view guidance. This is code/test review, not another runtime
run or owner play-test. The generator’s separate calibration remains pinned to
`03d1992` until its workstream explicitly integrates and recalibrates the engine.


## First hosted M33 run — browser fixture follow-up

Automatic [Tests 41571415572](https://github.com/rtulloh/bowl_bound/actions/runs/41571415572)
at `d518ba2` passes Python/lint/format/pip (**3,392 tests in 1,081.55s,
93.03% branch-aware coverage**) and frontend/build/audit (**130 tests,
0 vulnerabilities**). Browser outcome is **33 passed, 5 failed in 5.0m**,
so this is a failing full gate. Both new armed-timeout browser cases pass.

Two compact-controls cases encoded the retired disabled timeout placeholder
after kickoff. They now compare both enabled side actions with exact keys/labels
from the actual engine response, verify no arm initially and no stale placeholder,
and retain every existing geometry/focus/menu/play assertion. The three guidance
cases supplied invalid API mode `scrimmage`, producing 422 before any controls;
the transport fixture now requests supported `drive` mode and verifies success
and initial engine scrimmage phase. All actual guidance/save/kick assertions stay.
No production behavior, engine charts, clock rules or CPU seed changes.

Hosted frontend warnings include existing React act(...) warnings (DEV-044),
a duplicate PlayLog fixture-key warning now tracked as DEV-064, and the known
npm deprecation. These are not suppressed, not browser-failure causes, and remain
M23 follow-up scope. This record corrects any inference that a passing frontend
suite establishes warning-free output. Fresh branch-hosted coverage remains
required before milestone acceptance.


Browser follow-up pre-push gate: **3,392 Python tests passed in 771.66s,
93.05% branch-aware coverage**, no skips or Python warnings; **84** focused
guidance/timeout/tracker cases pass in **6.68s**. Pinned Node/npm: syntax checks
for both changed E2E files pass; frontend **130 tests in 4.56s**, build **587ms**,
audit **0 vulnerabilities**, and Playwright discovery **38 cases / seven files**
pass. Ruff check/format, pip check and diff checks pass. The existing npm
deprecation and Vitest performance advice remain visible.

A second independent read-only review of the two E2E corrections confirms valid
`drive` transport, initial engine scrimmage phase, three zero-yard snaps to the
48-yard public attempt, and exact engine-provided timeout labels/keys after
kickoff. It found no test weakening or obvious setup mismatch. Runtime and audit
tool source are byte-identical to the preceding hosted source-green `d518ba2`;
the 17-fault/32-public-game/120-private-game evidence still applies unchanged.
Fresh hosted browser verification is pending; the previous failing run remains
recorded above.


Independent baseline confirmation: generator-branch Tests
[41572345677](https://github.com/rtulloh/bowl_bound/actions/runs/41572345677)
at `3c1bb9b` passes 33 browsers with runtime/frontend pinned to `03d1992`, and
its passing frontend stage emits the same React act(...) and duplicate-key `1`
warnings. DEV-044/DEV-064 record this evidence; neither warning originated in
M33’s gameplay/UI changes. This does not substitute for the 38-case M33 retry.

## Completed engineering acceptance — 2026-11-02

Automatic [Tests 41575358111](https://github.com/rtulloh/bowl_bound/actions/runs/41575358111)
completed successfully at exact tested commit
`eed362c7daacff66c092a11d1ba8a896d1a9a1eb`:

- Python **3,392 passed in 820.51s (13:40)** with **93.03% branch-aware coverage**;
  Ruff lint/format (**541 files**) and pip dependency checks pass.
- Frontend **130 passed in 16 files**; production build **422ms**;
  dependency audit **zero vulnerabilities**.
- Real-engine Playwright **38/38 passed in 4.1m**. All three normal-difficulty
  guidance cases, both side-owned post-kickoff timeout cases and both corrected
  compact-controls cases pass. No browser case was skipped or weakened.
- The automatic branch trigger and exact source association are confirmed;
  the preceding failed run establishes failure propagation. Static tests retain
  main/PR triggers, read-only permissions, exact pins, immutable source selection
  and the separately named manual native workflow. No automatic publication was
  introduced.

UI-041, RULE-042 and DEV-059 are now resolved against their implementation
commits and this full-gate SHA. Reviewing every assigned ticket confirms all ten
Milestone 33 engineering acceptance criteria are satisfied. The 17/17 mutation
controls, 32/32 public coaching/replay games and unchanged 120/120 private season
games above remain applicable: executable runtime and audit-tool source are
byte-identical to `d518ba2`. Full traces, scoring, statistics, timing, saved
continuations and coaching behavior were reconciled, rather than treating
completed games alone as proof.

The review includes the independent read-only code/E2E reviews recorded above,
exact runtime manifest membership, all 15 public sample hashes and public-safe
outgoing paths. No private chart, save or detailed report is committed. QB Sneak
and RZDZ remain supported; the deferred Advanced II defensive options remain
unavailable. M34 generator work and scheduled M35 coffin-corner work stay on
separate workstreams.

Remaining limits are explicit: local Chromium cannot launch under this sandbox;
valid browser evidence comes from the hosted run. Passing frontend tests retain
the baseline React act/duplicate-fixture-key warnings (DEV-044/DEV-064), npm's
existing deprecation and Vitest performance advice. Native three-target evidence
for DEV-060/DEV-061 belongs to baseline `03d1992`, not a new M33 executable build.
No release was dispatched or published by this work. Gameplay tickets remain
resolved, not closed, pending owner play-test confirmation. Coaching call counts
above are descriptive audits, not universal balance or calibrated team-strength
claims.

Final acceptance pre-push checks: `.venv/bin/python -m pytest --cov
--cov-report=term-missing -q` passes **3,392 tests in 768.11s (12:48)** with
**93.05% branch-aware coverage**, no skips or Python warnings. Pinned Node/npm:
`npm ci --ignore-scripts`, `npm test` (**130 tests, 16 files, 4.96s**),
`npm run build` (**579ms**) and `npm audit` (**zero vulnerabilities**) pass.
Ruff check/format (**541 files**), pip check, all **18** tracker tests,
all **900** local Markdown links and `git diff --check` pass. All ten assigned
tickets are resolved with tested commits; none is closed. The final acceptance
commit changes documentation/status only; reviewed executable source remains
identical to the fully passing hosted `eed362c`.

## Owner play-test follow-up — UI-052 (2026-11-03)

After completed engineering acceptance at `f82ad47`, the owner requested clearer
next-play timeout button wording on the still-unmerged play-test branch. This
narrow [UI-052](issues/UI/UI-052.md) follow-up belongs to M33 owner review; it does
not reopen or replace that snapshot's acceptance record or expand game rules.

Reread local Paydirt `paydirt/interactive_game.py:637`, whose `[T] Call Timeout`
control describes its purpose in plain language. Adapt that wording approach
only, not its NFL timing instruction, code or dependencies. The owner approved
**Use [team] timeout on next play (N)** when unselected and
**Cancel [team] timeout (N)** when selected. The engine supplies both labels and
the existing budget; the browser continues to display backend facts. Action keys,
timeout ownership, timing, save state and gameplay behavior are unchanged.

Updated the existing synthetic frontend fixture/expectations and player guide.
This is copy only: no artificial new behavior test or changed football assertion
is needed. Focused existing engine/CLI/frontend checks and lint/build validation
are recorded below after execution. The live port-8033 process and its in-memory
game remain untouched; the owner will transfer via Save/Load to a new process.

Validation (copy-only follow-up):

- `.venv/bin/python -m pytest tests/test_armed_timeouts.py tests/test_cli_timeout_controls.py tests/test_cli_shortcuts.py tests/test_issue_tracker.py -q`:
  **114 passed in 8.99s**, including all 37 armed-timeout cases; no skips/warnings.
- Pinned Node 24.22.1/npm 11.19.1, `frontend/`:
  `npm test -- src/test/clockFlow.test.jsx src/test/clockChoices.test.jsx src/test/noRules.test.js`:
  **27 passed in three files, 1.09s**; `npm run build` passes (**369ms**).
- Ruff check/format (**542 files**) and `git diff --check` pass. A synthetic
  two-side preview confirms exact approved labels/counts and unchanged state
  after selection/cancellation. Existing frontend expectations change only to
  the approved copy; no gameplay assertion or action key changed.
- No full simulation/regression rerun or push is needed for this local copy
  review. The previous `f82ad47` full-gate evidence stays historical; it is not
  presented as testing this new label change. Port 8033 remains running untouched.


## Owner play-test follow-up — AI-033 (2026-11-03)

The owner questioned a defensive Razzle-Dazzle supplemental choice. This is a
separate [AI-033](issues/AI/AI-033.md) follow-up on the unmerged review branch;
the completed `f82ad47` engineering acceptance above remains historical.
No private team names, chart cells, actual game traces or saves are reproduced.

Before implementation, independently consulted local Paydirt
`paydirt/computer_ai.py:1242` (`should_accept_penalty`), related shared-fumble/
return-penalty previews in `paydirt/game_engine.py`, and
`tests/test_cpu_penalty_decision.py` / `tests/test_fumble.py`. Adapted the principle
of comparing eligible engine outcomes and synthetic recovery/choice tests.
Paydirt has no direct RZDZ equivalent in these references. Its NFL penalty rules,
recovery ranges, return procedures, field heuristics, team fixtures and runtime
code are deliberately excluded. Bowl Bound engine semantics and its existing
versioned utility remain authoritative.

The meaningful red regression gave all three unchanged v10 difficulty tiers a
first-legal uniformly positive B and a later known loss. All chose B, proving the
first-ID fallback defect independently of any favorable realized roll. RZDZ had
no deterministic pending `decision_outcomes`, so ordinary penalty comparison did
not apply. Another red regression showed floating weighted addition broke exact
ties between identical ordinary and supplemental outcomes; rational accumulation
preserves the engine's legal ordering.

The initial, superseded v11 prototype compared complete possible outcomes through isolated real-engine
branches with exact physical dice multiplicities. Offense maximizes and defense
minimizes the existing Hard field/score utility. This is not an unconditional
symbol hierarchy: BLACK means the normalized incompletion, fumble recovery is
probabilistic, QT may be favorable or unfavorable, and fourth-down receiving spot
can outweigh a turnover label. Tests preserve those distinctions. An initial
fumble fixture assumed its recovery spot was always favorable; the corrected
fixture varies the actual recovery distribution at a spot where the unchanged
utility supports the expected ordering. No new state-utility heuristic was added.

### Information and commitment boundary

`ChartAwareCoach` explicitly permits both immutable supplied boards and excludes
the live session, human selected call, gameplay seed and future dice. All normal
tiers inherit that boundary. Existing Easy/Medium restrictions describe ordinary
play-call mixtures, which this fix leaves unchanged; v11 explicitly adds a forced
RZDZ result-choice comparison to all three tiers. It reads the possible supplemental
rows and already revealed RZDZ comparison/formation facts, never an actual future
roll. A probability distribution over legal chart information is not a prediction
of the next draw. QT/B/QR/Option stay unresolved gambles; the selected symbol is
committed before the engine draws and resolves its actual future result. Private
expected utility is not attached to `decision_outcomes` or shown as a known result.

Three-tier invariance tests hold the observed pending state/charts constant and
change the unobserved future stream. The selected QT remains identical; actual
committed outcomes differ. Repeated decisions/plans preserve gameplay tape/source
position, saved facts, journal, view and Hard committed-call history. Current and
frozen-v10 pending saves replay actual committed choices and dice. The prototype
adds only derived revealed context; no future source or expected outcome is saved.

The owner clarified that available-chart probability estimates are permitted,
while the actual future roll remains unknowable. The information review is
complete on that existing boundary; no new hidden data access is introduced.
The implementation remains uncommitted pending validation. The existing
8033/8034 in-memory games remain untouched; parent owns any future updated server.
No push, release or live server restart is part of this follow-up.


Follow-up hardening also reproduced two RZDZ try-phase failures in the new evaluator:
its sandbox initially used scrimmage, so the existing two-point utility correctly
rejected the result. Passing the observed two-point phase now preserves 0/2-point
try outcomes for both choosers without retaining scrimmage field potential.
Ten red version-contract cases identified the development API/audit CLI allowlists
missing v11; both now accept the revision, while old IDs remain supported. The
audit's default normal-tier matrix follows v11. Existing current-tier identity
assertions use the declared current revision; explicit frozen tests still pin old
versions. Export-purity comparisons exclude only the existing `saved_at` timestamp
and its integrity checksum, retaining commands, rolls, RNG state, configuration
and final state digest.


The first full-Python attempt was deliberately interrupted after **1,073 passed,
4 failed in 539.00s** while completing the policy-interface migration and try-phase
hardening. The failures were exact current-policy identity expectations in two CLI
tests and two explicit observation-shape allowlists. The current identity checks
now follow the declared revision; the public allowlist adds only revealed RZDZ
context, and the frozen-v1 stream oracle explicitly excludes it. No legacy stream
assertion or hidden-opponent/future-dice restriction is removed. This interrupted
attempt is not a full regression pass; a fresh final-source run is required.


### AI-033 bounded comparison and performance review

The initial exact production prototype passed **3,446 Python cases in 1,042.31s,
93.13% branch coverage**. This is pre-revision evidence, not the final code's
full gate. A separate private plausibility benchmark found one of 18 candidates
incomplete at 10,000 evaluations: **99.18s cold** and a whole-comparison fallback.
That is not acceptable for interactive play. The old 32-game public audit was
interrupted on this newly found blocker; no result is claimed from it.

The approved smallest revision reuses isolated one-action rollouts with a strict
shared budget: **288 total, equal per candidate, at most 32 each**. All candidates
share deterministic hypothetical streams derived solely from the revealed public
observation and a v11 analysis namespace. Real gameplay and private coaching seeds
are unavailable. Physical dice still use the Bowl Bound distributions; the exact
216-by-36 regression/oracle remains explicit and outside the request path.
Sample means and standard errors are estimates, not exact future outcomes;
failures invalidate the full comparison without renormalization. Frozen policies,
existing state utility, symbolic pending choices and commitment-before-roll remain.

The fictional branching B/QT/fumble/penalty regression was red on engine
invocation **289** in the old path; it now succeeds within the shared budget and
does not collapse to the first B. Further controls check common streams, exact
identical-outcome ties, sampling-error diagnostics, invalid budgets, and explicit
failed samples. The same installed-board benchmark at a synthetic spot/formation
now has **288 successful samples, zero fallbacks, 59.35ms cold / 0.021ms cached**.
It is not the actual live-game state or a latency guarantee; the old 99s measurement
also occurred during host contention. Only aggregate evidence is public.

The unchanged baseline local-season control passes **120/120 games, zero failures
or fallbacks**. This is a mechanics/replay control, not current-v11 coaching
calibration. Detailed reports, chart inputs and comparative findings remain in
ignored private paths. A current public coaching/replay audit and fresh full
Python gate are still required after the bounded source freezes. No push, release
or live-server restart is included; the parent will use an immutable new snapshot
for owner review while regression remains explicitly pending.


Stable-source handoff: **372 focused cumulative tests passed in 58.93s**. A
second read-only benchmark uses the board pair referenced by the owner's actual
private save, at the explicitly synthetic spot/formation: **18 choices, 288
successful samples, zero fallback, 60.15ms cold / 0.023ms cached**, and a later
legal selection. Neither benchmark predicts or replays the unknown original
RZDZ field state/future result. Current source is offered as a focused commit
for an immutable local play test; AI-033 stays open until fresh full validation
and owner review. Prior full-Python evidence is explicitly pre-revision.


### AI-033 final engineering verification

Tested implementation: `aad5312d301c430f9ea8243c758fcb0666ecedf7`; the code is the
same immutable source used by the parent's port-8036 play-test server. AI-033 is
resolved pending actual owner RZDZ confirmation before closure. Original M33
acceptance at `f82ad47` remains historical; this is a bounded owner-review fix.

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`:
  **3,454 passed in 893.63s, 93.15% branch coverage**, no skips or Python warnings.
- Focused cumulative command covers RZDZ, difficulty, coaching saves/profiles/
  invariants, strict saves, API coaching/save/control, CLI games, evaluator and
  exact-probability contracts, version interfaces and current audit matrix:
  **372 passed in 58.93s**. Tracker + isolated real runtime + all 62 new RZDZ
  cases: **81 passed in 15.22s**.
- `.venv/bin/python -m bowl_bound.coaching_audit --seeds 101 307 --policies baseline-v2 easy-v11 medium-v11 hard-v11`:
  **32/32 mechanically correct games**, both sides/arrangements, exact saved-future
  replay, scoring/statistics and all four 900-second quarters. Reconciled **5,451
  reports, 11,764 trace rolls and 5,336 replayed commands**, zero illegal selections.
  All **147** current forced RZDZ decisions (**77 defense / 70 offense**) have
  **zero fallback**; **5,623** preference vectors are finite, normalized, legal and
  assign positive probability to the selected call.
- The whole audit has **two flagged initial-try analysis fallbacks**, preserved
  in [AI-034](issues/AI/AI-034.md), an M23 follow-up. A penalty leaves another
  attempt outside the one-action boundary; the current evaluator refuses to
  pretend it knows a completed zero/two-point outcome. The fictional reproduction
  has 32 explicit failed samples/no mean. No flag or failure assertion is hidden.
- Comparable calls/repetitions: baseline **150/21**, Easy **191/43**, Medium
  **201/45**, Hard **170/28**. Longest comparable streaks: **2/3/4/3**. All **4,911**
  situation buckets remain small samples, with zero advisory concentration warnings;
  this provides no broad balance, optimality or calibration claim.
- Unchanged private command: `.venv/bin/python scripts/run_local_season.py --seasons seasons --games-per-team 12 --seed 20311031 --output private-data/milestone-33-validation/ai033-local-season`:
  **120 passed, zero failures/fallbacks**. Detailed evidence remains ignored.
- Frontend source unchanged: pinned npm CI/test/build/audit already passes,
  **130 tests in 4.66s**, build **1.42s**, zero vulnerabilities; existing npm
  deprecation and Vitest advice remain visible. Ruff check/format (**547 files**),
  pip check and diff checks pass. All ten changed app-runtime files are already
  manifest-selected; the developer audit CLI is intentionally not a player
  runtime module. Real isolated staging/default-game checks pass.

No fresh automated browser/hosted gate is claimed for this follow-up. Local
Chromium's sandbox restriction remains documented above, and no push is authorized.
The parent independently verified health/frontend/assets, v11 imports from the
frozen checkout, and the owner's exact saved-game load/re-save/reload with only
timestamp/integrity differences. This is not invented owner RZDZ confirmation.
No live game was stopped, restarted or edited; no main/release/tag was changed.


### RULE-044 timeout play-test follow-up, presentation checkpoint

Owner's interception screenshot separated deferred prior timing from the selected
play awaiting a mandatory decision. Current rules charge the previous normal
play when the next call starts; its selected timeout waits for that call's final
continuation. Paydirt `game_engine.py:3105` and
`tests/test_timeout_clock_interactions.py` informed ownership/boundary tests; NFL
clock/warning behavior and code were deliberately not reused. Bowl Bound CLI AT
and T were read directly, not assumed equivalent.

Six meaningful red synthetic API cases exposed remaining armed/next-legal-play
status and absent timing explanations; frontend red exposed the missing prior
charge explanation. Presentation now names the in-progress play correctly and
reports recorded timeout use in both latest result and history. Exact clock,
timeout ownership, logs and strict replay remain unchanged. Cumulative Python
435/50.97s; frontend 131/4.60s and build1.16s; focused Ruff pass. Normal CLI AT
parity includes prior30+selected10 at late41s→1s. Natural10s web reservations
are not AT-equivalent; owner authorizes a distinct conditional intent next.
Original M33 acceptance is historical; RULE-044 remains open.


RULE-044 conditional-intent checkpoint (2026-11-03): parent/owner approved
`timeout_after:<side>` rather than altering recorded legacy actions. Its single
side-owned request persists through mandatory decisions, but charges only if
normal resolved-play timing would offer a post-play timeout (>10s). Natural10s,
no-time and unsupported paths are explicit; unsupported keeps the request.
`conditional_timeout=true` is semantic; false and new view-only action offers
are excluded for legacy digest compatibility. Normal/frozen coach observations
exclude new UI request keys; CPU policy versions are unchanged. CLI AT's human
pending limitation is documented, not silently changed.

15 meaningful engine failures, six new API command failures and one frontend
primary-control failure preceded implementation. 44 focused/7.43s and568
cumulative/73.23s pass; frontend 131/4.80s, production build1.08s and Ruff
check/format 554 files pass. Existing browser selectors now use conditional offers;
two fictional pending-interception cases were added, not claimed executed.
Fresh full gate and immutable owner re-test are pending.

Review follow-up: pre-call primary label remains the approved Use TEAM timeout
on next play; if-eligible status says next until a mandatory choice is pending.
A meaningful red CLI menu test exposed the new key leaking as an implementation
name; both prefixes are now excluded without changing terminal T/AT. Both new
browser-fixture INT paths pass through TestClient, not a browser. Isolated real
runtime,18 tracker,pip check and npm audit 0 also pass.

Final-source full gate initially exposed two stale exact CLI/API drive-log
expectations missing additive `timing_label: null`. Both failed meaningfully,
then both passed in0.67s with only that documented field added; all strict
football/save/future comparisons remain. The early full run was interrupted
at511passed/2failed in278.38s and is not acceptance evidence. Executable source
remains e3d6516; a fresh complete gate follows this test-contract correction.

Owner follow-up (2026-11-03): frozen e3d6516 offense timeout/play1 uses10seconds
as confirmed by the owner; defense still awaits confirmation. Parent's separate
HTTP/asset/history and actual 97d synthetic-save compatibility checks pass; no
existing server was restarted. Browser tests now explicitly finish possible
human RZDZ continuations while preserving pending-state assertions, avoiding a
concealed-call-dependent timeout. Only collection/API-fixture checks are claimed
locally, not browser execution.


### RULE-044 final engineering verification

Executable source: `e3d6516fd7362940c7178dcea2276f1b1f75747c`, identical to the
owner's frozen candidate. Test contract corrected in b265de3, browser continuation
checks/docs in 899cd8c. Fresh `.venv/bin/python -m pytest --cov
--cov-report=term-missing -q`: **3,499 passed in 873.91s, 93.17% branch coverage**,
exit 0, no skips/warnings. The interrupted 511-pass/2-stale-expectation run is
explicitly not used as acceptance evidence.

Relevant cumulative 568/73.23s and final focused 122/13.30s pass; frontend 131,
production build, npm audit 0, Ruff check/format 554 files, pip check, isolated
real runtime/default-game stage, 818 local Markdown links and diff checks pass.
Both new browser fixtures pass real API execution, and 40 browser cases collect;
no automated browser pass is claimed because the local sandbox remains blocked.
Root's frozen HTTP/frontend/history and actual 97d fictional-golden strict
load/re-save checks pass. Owner confirms offense; defense confirmation is pending.
RULE-044 is resolved with tested refs, **not closed**. No new M33 acceptance,
push, merge, release or tag is claimed; root owns subsequent UI requests on its
separate worktree. All heavy validation jobs have completed.


### Reviewed web follow-up integration

After the clean 3,499-case timeout gate, integrated the parent's reviewed
0a7065f/78ffa23/81dc6e4/855d4bb work. UI-055 removes only the duplicated budget
suffix from the two engine Use/Cancel labels, preserving action keys, clock and
scoreboard counts. UI-054 stays open: API plus SSR/JSDOM retain all eleven
reports in the authorized inspected game, but actual scroll/lifecycle visibility
is not verified. UI-056/M37 is owner-requested future support-log planning only.
No implementation of the support exporter or speculative history repair occurs.

Generated tracker conflicts were resolved by regeneration, preserving RULE-044
resolved with offense-only confirmation. Application runtime files exactly match
the parent's frozen 855d4bb candidate; browser continuation tests and validation
notes remain separate. A fresh merged-source 3,503-case Python gate follows,
with focused label/timeout/API/tracker and frontend checks first.

Merged-source focused validation: 108 timeout/label/API/tracker cases pass in
13.36s; frontend131 pass in5.00s, production build1.33s, Ruff check/format560
files and diff checks pass. Actual application runtime diff against frozen
855d4bb is empty. Repeated gate is explicitly for the merged label source and
four new regressions; the prior 3,499 green remains valid historical evidence.

Final combined source `61d75fda95dae6247e308ac99656102fe3b6baff` passed
`.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **3,503 passed
in 879.31s (14:39), 93.17% branch coverage**, with no skips or warnings. This is
a fresh gate after the four label tests and reviewed runtime `9d5071f`, not a
reuse of the earlier 3,499-case result. The integrated implementation aliases
are e62925d / 1472238 / 9d5071f / 8bd8838, with tracker reconciliation in 61d75fd.

Focused 108 / 13.36s, frontend 131 / 5.00s, build 1.33s, Ruff check/format
560 files, pip check, 1,245 local Markdown links and diff checks pass. Frontend
output retains the existing Vitest jsdom performance recommendation. No new
automated browser execution is claimed: the documented Chromium sandbox
restriction remains, and the 40-case browser suite has collection/API-fixture
evidence rather than a fresh browser pass. Parent independently verified the
immutable 8039 HTTP candidate and copied saved-game semantics without advancing
the original game. No private payload is committed.

UI-054 remains under investigation; UI-055 is resolved pending owner
confirmation; RULE-044 is resolved with offense-only confirmation, awaiting
defense. UI-056/M37 is future planning only. Original M33 acceptance remains
historical. No live server was changed, and no push, merge, release or tag
was performed. No further heavy validation job is running in this workstream.


### AI-035 late-half report investigation (isolated follow-up)

Work is isolated on `fix/late-half-coaching` from `6c1289c`, leaving the root
checkout and live play-test servers untouched. Parent's read-only evidence
clarified that the reported running call was at a Q1-to-Q2 transition, not
halftime; no kickoff was due. No late-half failure is claimed for that game.

Before the phase, reviewed local Paydirt `paydirt/computer_ai.py:1138` and
`:1193` (offensive/defensive timeout intent),
`tests/test_cpu_timeout.py`, `tests/test_timeout_clock_interactions.py` and
`tests/test_half_ending_clock_trace.py`. Adapt only public-state boundary and
offered-action tests. Do not inherit NFL timeout thresholds, two-minute-warning
behavior, random fractional runoff, private chart data or runtime code. Bowl
Bound's own timing chart and engine offers remain authoritative. Any separate
synthetic clock-policy gap needs red evidence and a reviewed version plan before
production changes; frozen historical coaching behavior must remain stable.

The bounded follow-up separately reproduces a pending-timing scoring loss:
12 current-policy red cases and 12 green controls in 1.38s. All tiers choose a
public-policy field goal that expires before any roll, although the engine
offers a useful own timeout or hurry. The owner's Q1 report remains valid and
unrelated. [The review plan](late-half-cpu-clock-plan-2026-11-03.md) proposes one
derived engine view fact and a versioned clock-policy method instead of
changing observation/analysis hashes. Production is unchanged and AI-035 stays
open at this deliberate red checkpoint; no full-green claim or publication.

Checkpoint validation (production unchanged): the complete new module remains
intentionally red at 12 failed / 12 passed; its green-control selection passes
12 (12 desired-fix cases explicitly deselected), and existing regulation,
optional-clock, coordinator and tracker checks pass 74 in 3.05s. Focused Ruff
check/format and diff checks pass. This is investigation evidence, not a green
implementation or completed acceptance.


AI-035 approved implementation checkpoint: v12 normal clock selection preserves
the shared public-policy FG at a pending Q2/Q4 boundary using an offered useful
own timeout/hurry. One derived engine view Boolean is passed separately to the
clock method; no old observation/analysis hash changes. Ordinary named-tier
loads upgrade under AI-026; explicit development audit loads may freeze v1–11.
The initial draft's contrary ordinary-load promise was corrected before source
implementation. Expanded red97/green13 and useful-timeout red3 preceded final
focused119/5.26s; twelve actual original-source fictional golden checks pass.
Cumulative/full checks and a tested commit are pending, so AI-035 remains open.

Focused/cumulative checkpoint: **365 passed in 44.77s** across difficulty/
profiles/coordinator, strict saves, API, RZDZ, timing and new clock controls.
Fresh pinned frontend: **131 in 4.99s**, production build 739ms, npm audit zero
vulnerabilities. npm ci reports the existing whatwg-encoding deprecation;
Vitest reports its jsdom performance recommendation. Ruff check/format 566 files,
pip and diff checks pass. No new skips are hidden. Full regression remains
pending, and this does not constitute owner play-test confirmation.

Merged root's reviewed 30aaaaa halftime/QT documentation and regression work.
One current-tier fixture used a human call on a legal automatic CPU kick; it
failed 422, then the driver was corrected to follow engine `turn.automatic`.
Browser response capture now precedes load to handle that same automatic path
without dropping clock/kickoff/history/save assertions. The first full run was
immediately interrupted at41passed/13.37s, not claimed as acceptance. Runtime
remains aa578d7. Fresh merged full validation follows.


--- 2026-11-03 — final-source regression ---
Implementation aa578d7 and merged driver checkpoint 007056b passed the fresh
complete Python gate: **3,630 passed in 923.40s, 93.20% branch-aware coverage**,
exit zero. The earlier interrupted run is not acceptance evidence. Focused
merged clock/halftime/API/save/tracker checks pass **145 in 8.75s**. Final Ruff
check/format covers 569 files; pip check, zero-vulnerability npm audit, production
build, frontend 131, 1,267 local Markdown links and diff checks pass. Existing
npm deprecation and Vitest advisory remain documented above.

All 48 browser cases in eight files collect. Fresh real-engine halftime browser
execution fails at Chromium launch before assertions with macOS MachPort1100:
one failed and seven not run under fail-fast, plus its cleanup error. This is
an execution limitation, not a browser pass; no sandbox bypass, skip or assertion
weakening was used. The temporary test server exited; owner servers and games
were untouched. Complete-game coaching/replay and private local-season audits
follow separately. Owner play-test confirmation is still required for closure.


--- 2026-11-03 — completed audit / tested resolution ---
Tested runtime **aa578d7**, merged regression checkpoint **007056b**. The public
32-game matrix (seeds 101/307; baseline-v2 and Easy/Medium/Hard-v12; both sample
orientations and CPU sides) passes mechanics and strict saved-future replay:
5,449 reports, 11,748 trace consultations, 5,347 replayed steps, each regulation
quarter reconciles to 900 seconds, and no illegal choices. All nine ordinary
calls and all six defenses occur for every policy; 672 comparable choices have
117 repeats, maximum within-bucket streak four, and zero concentration warnings.
Current tiers select 15 own timeouts. These are audit observations, not quotas
or calibration claims.

Three initial-try analysis fallbacks (one Easy, two Medium) remain explicitly
reported under AI-034. Isolated uniform-opponent reanalysis reproduces only the
known `hypothetical try did not settle` limitation; it does not reconstruct
historical opponent weights. All 135 forced RZDZ choices have zero fallbacks.
No unresolved samples are zero-filled or hidden.

The separate private local-season baseline mechanics audit passes **120/120**,
zero errors/fallbacks, 22,192 reports and six overtime games. It reads local
private bundles without modifying them; all detailed artifacts remain ignored.
This is baseline mechanics evidence, not current-v12 coaching calibration.

AI-035 is resolved pending owner play testing. The original reported Q1-to-Q2
transition remains valid, unrelated to the synthetic defect. Browser execution
is still blocked as recorded above; no full browser gate or fresh milestone
acceptance is claimed. No push, main merge, release, tag or owner-game mutation.

## Owner-selected next-release blockers — 2026-11-03

The owner selected AI-036, UI-054, CLI-058/UI-058 and UI-059 as required M33
follow-up fixes before the next release. This moves halftime/try presentation
forward from M35, which retains coffin-corner punts. Preserve prior engineering
acceptance checkpoints; do not describe the new scope as already tested or
released. The RZDZ target is normally one to three surprise calls per team per
game with situational judgment, not a new rule limiting human legal calls.

Use the separately tested v12 late-half clock fix as the integration base after
review; preserve older explicit policies. Consult relevant local Paydirt code,
tests and lessons before implementing this follow-up and record references.
Each selected issue needs meaningful synthetic red-first regressions, the
smallest correct engine-owned behavior/presentation change, focused cumulative
checks and documentation. The integrated source must pass the full gate before
push, with browser limitations reported honestly, followed by owner playtesting.
Recommendations such as CLI-062 or AI-032 are separate from this explicit
owner-selected blocker list unless subsequently approved.

### Confirmed six-ticket implementation handoff

The owner explicitly added AI-035 and directed the milestone agent to proceed
with AI-035, AI-036, UI-054, CLI-058, UI-058 and UI-059 as M33 next-release
blockers. AI-035 already has a tested v12 implementation on its isolated branch;
remaining tickets need test-first implementation. Integrate the selected work
without changing the chart-generator branch or frozen owner playtest servers.
Return tested commits, documentation, a full-regression report with any browser
limitations, and concrete playtest instructions. Do not publish or start the
release workflow as part of this implementation handoff.


## Six selected release blockers: implementation phase

Integrated the owner's 839d154 handoff with the tested v12 source at 4137be0;
append-only histories were preserved and the issue index regenerated (18 checks
pass). AI-035 remains tested/resolved pending owner confirmation. Remaining scope
is AI-036, UI-054, UI-059 and the shared CLI-058/UI-058 halftime presentation.
Earlier acceptance is historical, not acceptance of this new follow-up.

Before implementation, consulted local Paydirt `paydirt/computer_ai.py:76–119`,
`paydirt/offense_strategy.py:118–134`, `tests/test_offensive_call_history.py`,
`paydirt/interactive_game.py:2677–2687`, `:3060–3084`, `:3834–3862`,
`tests/test_half_ending_score_flow.py` and `tests/test_halftime_ownership.py`.
Also reviewed its web `Game/Halftime.jsx`, `Game/PlayLogDisplay.tsx`, matching
play-log tests and `halftimeFromEngine.test.jsx`. Adapt committed-history purity,
decaying repeat deterrence, explicit try prompts, engine-owned recap facts and
ordered visible transitions. Paydirt has no Bowl Bound RZDZ policy to copy;
the owner's one-to-three surprise-use target is the coaching requirement.
Do not inherit NFL play categories, timing/warnings, halftime ownership code,
chart cells, private fixtures or runtime dependencies. Bowl Bound owns legal
choices, pending completion, scoring, time, dice and presentation facts.


AI-036 focused source checkpoint: **368 cumulative coaching/API/save/invariant
cases pass in 61.27s**, plus 30 audit-contract checks in 40.57s and 18 tracker
checks in 0.53s. Ruff check/format and diff checks pass. The first cumulative run
caught the CLI audit default still listing v12; both API and CLI defaults now
use v13, and the fresh cumulative run is green. Two mistyped optional test paths
collected no tests and are not counted as validation. Complete-game frequency/
replay evidence and combined final regression remain pending; ticket stays open.


AI-036 complete-game checkpoint at 5a6486f: **32/32 complete and strict future
replays verified in 129.11s** (two seeds, both sample orientations/CPU sides,
baseline-v2 plus three v13 tiers). All quarters reconcile to 900 seconds; zero
illegal calls/concentration warnings. Current RZDZ counts across eight games
per tier: Easy `1,2,1,1,1,2,2,2` (mean 1.5); Medium `1,1,2,1,1,1,1,2` (1.25);
Hard `2,2,0,2,2,1,0,1` (1.25). No adjacent RZDZ calls; zero-use Hard games are
valid. Counts are current synthetic evidence, not a hard rule or historic rate.
There are 5,496 finalized reports, 11,601 trace consultations, 5,288 replayed
steps and 104 forced RZDZ choices with no pending-choice fallback. Three
initial-try fallbacks remain the separate known AI-034 limitation.

The existing audit omitted per-call resolved outcomes. A positive synthetic
complete-game regression fails on that missing evidence field (one failed,
33 deselected, 1.75s); additive counters now retain the CPU's actual finalized
RZDZ outcome IDs and statistical kinds, including excluded penalties. Renew
that reporting audit before resolving; selection behavior is unchanged.

### AI-036 tested surprise policy checkpoint

Commits `5a6486f` / `f0dd4a6`: v13 separate rare RZDZ weighting and committed
own-side repeat deterrence; v1–12 stay frozen. The renewed 32-game audit retains
actual per-call outcomes as well as strict replay. Current tier means are
1.5 / 1.25 / 1.25 RZDZ calls, no adjacent repeats, no revealed-choice fallback.
The 64 outcome/new-policy audit contracts and 368 cumulative coaching/API/save
cases pass. AI-036 is resolved awaiting owner review; combined six-ticket gate
remains pending. Detailed reports remain ignored.

### UI-054 history readability checkpoint

The engine retained all events. Synthetic rendering reproduced older-reading
position loss and missing complete-view/keyboard controls (3 red / 6 controls).
The UI now preserves reading position and offers explicit complete/latest views.
No football facts are calculated in the frontend. 134 frontend tests, build,
50 API/scoring/save cases and a 43-report fictional save replay pass. Browser
viewport cases are added; local launch limitations and owner review remain real
acceptance limits. Paydirt's auto-follow idea is adapted with user-controlled
reading; its frontend football computations are deliberately excluded.

### UI-059 two-point presentation checkpoint

Engine-owned attempt announcements are retained on the original touchdown; a
phase-specific coaching prompt keeps CPU calls hidden. A pure journaled result
review holds web automatic progression until Continue. Old direct kickoff
commands remain legal and dismiss the review, preserving frozen journals. New
review/announcement facts never enter CoachObservation and are excluded only as
presentation from semantic digests. Runtime manifest already includes all changed
modules; no new module or content allowance is needed. Paydirt's explicit try
prompt is adapted; its NFL rules are not. Focused and final evidence is in UI-059.

### CLI-058 / UI-058 shared halftime checkpoint

A single engine-authored review contains Q1/Q2/half scores, scoring events,
supported statistics and second-half kickoff assignment. Q1 score is captured
at the actual engine boundary; adapters calculate no football facts. The CLI
prints and acknowledges this review before automatic play; web acknowledgment
holds the recap for review. Save replay preserves pending/already reviewed
status, and legacy journals may kick directly. Conversion-ready/penalty/untimed
continuations do not announce halftime early. Paydirt's visible recap ordering
is adapted without its NFL rules or frontend period inference. Nine red cases
and one green Q1 control preceded the implementation. Two legacy raw-digest
failures were corrected without changing frozen hash expectations. Final combined
validation and manual acceptance remain pending.

### Six owner-selected release blockers: combined review checkpoint (2026-11-03)

Implementation references: AI-035 `aa578d7`/`007056b`/`243f5e5`; AI-036
`5a6486f`/`f0dd4a6` with tested status `de15731`; UI-054 `f465bb2`;
UI-059 `e97d2b1`; shared CLI-058/UI-058 `8ed9977`. Browser-only fixture
correction `478df71` guarantees both conversion outcomes regardless of the
CPU's legal call. Runtime and all collected Python cases are byte-identical
between `8ed9977` and `478df71`.

Commands and results on supported Python 3.12.8 / Node 24.22.1 / npm 11.19.1:

- `/Users/rtulloh/work/bowl_bound/.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **3,688 passed in 956.38s, 93.28% branch coverage**, exit 0, no skips/warnings reported.
- Ruff check and format check: **577 files**, pass; `python -m pip check`: pass.
- Fresh `npm ci --ignore-scripts`, `npm test`: **136 passed in 5.41s**; `npm run build`: pass; `npm audit`: **zero vulnerabilities**. Existing whatwg-encoding deprecation and Vitest environment advice remain visible.
- Generated tracker and **1,276 local Markdown targets** verified; no missing targets.
- `python -m bowl_bound.coaching_audit --seeds 101 307 --policies baseline-v2 easy-v13 medium-v13 hard-v13`: **32/32 finished and strict future replay verified**, 124.82s, zero illegal calls, all regulation quarters reconcile to 900 seconds. **5,496 reports, 11,601 trace consultations, 5,288 replayed steps**.
- Public current-tier RZDZ means **1.5 / 1.25 / 1.25** (eight games each, CPU scrimmage-call denominators **564 / 556 / 549**), no adjacent calls. **104 current-tier revealed decisions (133 including baseline) have zero fallback**. Three separate known AI-034 initial-try analysis fallbacks remain. **719 comparable calls / 144 repeats**, longest situation streak four; all **4,921** buckets are small samples, no advisory concentration warnings. No universal frequency, balance or historical calibration claim follows. Resolved outcome/statistical-kind counters match the prior checkpoint.
- `python scripts/run_local_season.py --seasons /Users/rtulloh/work/bowl_bound/seasons --games-per-team 12 --seed 20311031 --output private-data/m33-release-followup/final-8ed9977/private-season`: **120/120 passed in 75.44s**, zero failures/fallbacks, **22,192 reports and six OT games**. This separate baseline mechanics audit does not calibrate v13 historical coaching. Detailed reports stay private/ignored.
- Independently generated a fictional halftime save with actual pre-presentation `f465bb2` code in a temporary checkout. Current code loads it and directly executes the scheduled kickoff with identical serialized gameplay/coaching/journal/dice facts, excluding only saved timestamp/checksum.
- Final Playwright collection: **54 cases / 10 files**. Full execution: **54 launch failures before assertions**, each Chromium MachPort1100; temporary E2E server/link cleaned. No sandbox workaround, skip, weakened assertion or browser pass claim. Corrected conversion browser fixtures separately execute all four human/result combinations against the real coordinator.

All six requested implementations are committed. AI-035/AI-036 and CLI-058
are resolved against tested source, awaiting owner review. UI-054/UI-058/UI-059
remain open for valid browser acceptance and owner confirmation. Prior M33
acceptance remains historical; this checkpoint does not declare next-release
readiness, start publication or close tickets without owner confirmation.

Fresh play-test handoff: parent should freeze this branch into a new immutable
worktree/server and preserve ports 8033–8039. Check (1) current named difficulty
reports v13 while explicit frozen saves retain their contract; (2) occasional
RZDZ without a forced minimum; (3) the synthetic late-half useful-own-timeout FG
control; (4) computer going-for-two announcement before defense, result Continue
before automatic kickoff, retained ordered history; (5) Show complete history
and preserved older reading position; (6) HALFTIME recap before Start second
half, with one CLI recap before automatic kickoff. Save before/after recap and
reload to verify review persistence/no repeat. Do not mutate an existing live
process's source. Browser/owner acceptance must be recorded before release review.

### Additional acceptance controls after the combined runtime gate

No production changes follow the combined runtime gate. Four new engine cases
exercise both human sides and both try outcomes through an actual required
kick-reception decision, pending save/replay, and ordered touchdown/try/kick
history. The cumulative conversion/halftime/save/history/commentary command
passes **114 cases in 21.67s**:

```sh
/Users/rtulloh/work/bowl_bound/.venv/bin/python -m pytest tests/test_conversion_presentation.py tests/test_halftime_presentation.py tests/test_save_game.py tests/test_history_fixtures.py tests/test_commentary_replay.py -q
```

Four additional React DOM integration cases run production API requests against
a temporary fictional-team backend on an unused local port. They verify both
human-side two-point prompts/reviews before a required kick-reception choice,
halftime pending/acknowledged save-resume and the complete 43-entry scoring
history across reload. Full frontend now passes **140 cases / 17 files**;
production build and Ruff check/format (**578 files**) pass. Setup/cleanup owns
only the temporary process and folder; all owner servers remain untouched.
`docs/web-demo.md` documents the supported Python source environment needed by
these integration cases.

Runtime remains byte-identical to 8ed9977. Its full **3,688 / 93.28%** result is
historical validation of that unchanged runtime, not a claim that the four new
Python cases were included. These real-API DOM checks do not verify Chromium
layout/scroll geometry or replace the outstanding 54 real-browser cases. All
three UI tickets remain open for browser and owner acceptance. No push/release.

## UI-060 — Paydirt-style halftime presentation (2026-11-04)

The owner requested visually consistent halftime formatting after reviewing the
plain recap, then supplied the simple Paydirt web-card reference. Consulted
Paydirt `paydirt/interactive_game.py:248–442,3834–3844` and
`paydirt-web/frontend/src/components/Game/Halftime.jsx`/tests. Adapted boxed
terminal sections, away/home numeric columns and the web card's hierarchy.
NFL statistics/rules, score inference, branding and runtime dependencies are not
reused. Detailed scoring retains Bowl Bound play numbers; no quarter/time data is
invented.

The terminal prints aligned HALFTIME STATS, SCORING SUMMARY and TEAM STATISTICS
boxes once before the existing kickoff progression. Long names expand columns.
The primary cream web card shows HALFTIME, End of 2nd Quarter, neutral HM/AW
badges, names/scores, engine lead/tie wording and START 2ND HALF. First-half
details starts collapsed and retains score/statistics tables, scoring and kickoff
assignment. A final two-point result remains visible outside that disclosure.

The engine supplies immutable `review.halftime` facts; adapters format them and
never parse prose or calculate football. Existing `review.lines` remains for text
clients. The action key, acknowledgment timing, clock, statistics, dice and strict
save contract are unchanged. A pre-format fictional halftime save loads with only
the added structured recap and requested button label differing in its full
view/turn response. Existing semantic hashing already excludes presentation data.

Test-first evidence and changed expectations are recorded in
[UI-060](issues/UI/UI-060.md), including four initial Python failures, two
conversion-boundary failures, absent frontend component, and red controls for the
owner's simpler card. CLI prose checks now assert aligned cells; UI checks open
the details disclosure before verifying every retained table fact. An inherited
fixture's 0/0/7 typo is corrected to its declared 0/7/7. No football assertion is
weakened.

Validation on the final presentation source:

- Shared supported interpreter `/Users/rtulloh/work/bowl_bound/.venv/bin/python`
  with `-m pytest tests/test_halftime_presentation.py
  tests/test_conversion_presentation.py tests/test_save_game.py
  tests/test_history_fixtures.py tests/test_commentary_replay.py tests/test_api.py
  tests/test_api_coaching.py tests/test_coaching_invariants.py
  tests/test_coaching_saves.py tests/test_regulation.py
  tests/test_release_package.py tests/test_issue_tracker.py -q`:
  **353 passed in 52.13s**. The halftime module separately passes **18** cases.
- Pinned Node **24.22.1**, `node node_modules/vitest/vitest.mjs run`: **142 passed**;
  all four real-API integration cases are **not run** after their setup hits
  `listen EPERM 127.0.0.1`, one uncaught socket error and its 20-second hook timeout.
  Vitest labels those four skipped; no source skip was added. This full frontend
  attempt exits 1 and is not a passing gate. The five new focused UI cases pass.
- Production Vite build, Ruff check/format (**579 files**), pip check, generated
  tracker and diff checks pass; **22** tracker/player-doc/priority-doc cases pass.
  All **54** browser cases collect; no fresh browser
  assertion pass is claimed under the documented Chromium/socket restrictions.
- The two original fictional public teams reach halftime after **102 legal
  actions**. The immutable private preview preserves exact CLI output, a real
  API response and actual React DOM with production CSS. Its primary card starts
  with details closed. This is static HTML for owner visual review, not a browser
  screenshot or layout/scroll acceptance. Earlier previews remain unchanged.

The simplify review kept one dedicated presentation component: the existing
collapsible dark statistics widget has a different wrapper and home/away order.
No general table abstraction or runtime module was added. UI-060 remains open for
valid browser execution and owner visual confirmation. No full Python coverage
gate, milestone completion, merge, push, publication or release is claimed here.

UI-060 implementation commit: `af303326409eae8de996e35a6ce49285cd71e8c3`. Its
clean git-archive snapshot reproduces the fictional halftime and actual-App
static preview, with independent production/SSR builds and no listening server.
The same 353-case cumulative command passes on that clean snapshot in 51.76s;
its five focused UI cases also pass.
The screenshot reference is retained only as private local evidence. UI-060
remains open for browser and owner acceptance; this follow-up does not complete
the milestone.


## Owner CLI follow-ups — 2026-11-04

CLI-062 corrects no-change Razzle-Dazzle choices to `0` in engine labels and
structured presentation values. Raw trace tokens, normalized out-of-bounds facts,
nonzero markers and legal choice IDs remain unchanged. A nullable engine-owned
`replay_label` preserves the old semantic digest for pending saves; it is not
player-facing wording. An authentic pre-fix synthetic save proves strict loading
and continuation rather than generating its expected digest with changed code.
CLI-065 aligns one- and two-digit selectors and Razzle-Dazzle command hints in
both compact and full menus. CLI-066 restores two existing same-season private
rosters and source sidecars to the selected private chart bundle, with existing
chart bytes hash-verified unchanged. Runtime roster behavior was already correct;
no roster names, historical charts or owner logs were added to public tests.

Paydirt references and adaptations: `paydirt/play_resolver.py:532-537` separates
markers from yardage; `paydirt/interactive_game.py:2361-2365` enumerates engine
choices; `paydirt/commentary.py:65-114` loads optional colocated rosters. Reuse only
the separation of semantic facts and display, engine choice rendering, and roster
placement convention. Do not reuse NFL rules/timing, private data, silent malformed
roster fallback or its unpadded numbering. Per-ticket notes retain the test-first
failures: bare `*` versus `0`, plus two distinct play-column offsets with eighteen
choices in compact and full modes. Existing expectations were strengthened with
out-of-bounds and nonzero-marker cases; none were weakened.

Validation uses `/Users/rtulloh/work/bowl_bound/.venv/bin/python`:

- `-m pytest tests/test_razzle_dazzle.py tests/test_cli_presentation.py
  tests/test_cli062_compatibility.py -q`: **73 passed**.
- Related cumulative selection (the sorted union of `tests/test_cli*.py`,
  `tests/test_*save*.py`, `tests/test_*replay*.py`, `tests/test_*razzle*.py`,
  `tests/test_api*.py`, `tests/test_roster.py`, `tests/test_commentary*.py`),
  invoked once with `-m pytest -q`: **721 passed in 111.87s** across 37 modules.
- `-m pytest tests/test_history_fixtures.py tests/test_coaching_invariants.py
  tests/test_conversion_presentation.py tests/test_halftime_presentation.py
  tests/test_presentation_context.py tests/test_issue_tracker.py
  tests/test_priority_docs.py tests/test_release_player_docs.py -q`:
  **137 passed in 12.15s**.

This is an isolated owner-feedback follow-up, not milestone acceptance or a
release. The owner's running interpreter and source checkout remain untouched.
Roster names refresh through ordinary save/load; Python presentation changes
require launching the updated source. Owner play-test confirmation remains
required before closing these tickets.


## Pending interception context — 2026-11-04

CLI-067 adds engine-owned `pending.decision_context` beside the CLI/browser
result choices. The already-resolved interception location is shown from the
intercepting team's perspective; the committed scoreboard does not move until
resolution. Goal-line and end-zone labels preserve the known position without
predicting a return, awarding possession or consuming more dice.

Paydirt `paydirt/interactive_game.py:2483-2487` displays a turnover's field
position. Adapt that useful decision context only; reject its UI-side calculation
and field clamping. Bowl Bound supplies the complete label in the engine and
adapters only render it. `decision_context` is additive presentation data and
excluded from current/legacy digests. Choice labels/IDs, state, clock, statistics,
dice and save schema are unchanged. An authentic pending save captured before
this change proves strict replay compatibility.

Test-first failures: 27 initial Python cases, one additional API case and one
frontend case all failed for missing context. The focused final runs pass all
28 Python cases and all 21 component cases. These cover both possession
directions, ordinary and Razzle-Dazzle interception chains, zero-distance spots,
both goal lines and both end zones. No existing expectation was weakened.

Commands: supported Python `-m pytest tests/test_interception_context.py -q`;
pinned Node 24.22.1 `node node_modules/vitest/vitest.mjs run
src/test/components.test.jsx`. This remains an M33 owner-feedback follow-up,
not acceptance of the full milestone or release validation.


Final cumulative validation for the combined CLI follow-ups:

- Supported Python `-m pytest -q` on the sorted union of
  `test_cli*.py`, `test_*save*.py`, `test_*replay*.py`, `test_*razzle*.py`,
  `test_api*.py`, `test_roster.py`, `test_commentary*.py`,
  `test_history_fixtures.py`, `test_session.py`, `test_turnovers*.py`,
  `test_regulation*.py`, `test_coaching_invariants.py`, `test_*presentation*.py`,
  `test_interception_context.py`, `test_issue_tracker.py`,
  `test_priority_docs.py`, `test_release_player_docs.py`, `test_timing.py` and
  `test_bounds_declarations.py` under `tests/`: **993 passed in 127.48s**,
  51 modules. No skips or warnings were reported.
- Pinned Node `node node_modules/vitest/vitest.mjs run
  src/test/components.test.jsx src/test/regulation.test.jsx
  src/test/milestone19.test.jsx src/test/coaching.test.jsx
  src/test/compactGame.test.jsx src/test/noRules.test.js
  src/test/playLog.test.jsx src/test/reviewIntegration.test.jsx
  src/test/halftimeReview.test.jsx src/test/commentary.test.jsx`:
  **110 passed**. The four real-server review integration cases did not run:
  localhost `listen EPERM 127.0.0.1` caused one uncaught socket error and a
  20-second setup-hook timeout. Vitest labels those four skipped; no source
  skip was added. This combined frontend attempt exits 1, not a passing gate.
  The independent focused component run passes **21/21**.
- `node node_modules/vite/bin/vite.js build`: production build passes.
- Ruff check/format on changed Python files and `git diff --check` pass.
- The earlier bounds/timing follow-up command `-m pytest
  tests/test_bounds_declarations.py tests/test_timing.py -q` passes **44** cases.

The first implementation is `064e03d` (CLI-062/065 and private roster assembly
guidance for CLI-066). No push, publication or full milestone acceptance is
claimed. The live-server integration restriction remains explicit and owner
play-test confirmation is outstanding.

Pending interception implementation: `62a2c37`. Combined final implementation
passes the 993-case Python selection and the focused component/build checks
recorded above. CLI-062, CLI-065, CLI-066 and CLI-067 are resolved for owner review
and remain unclosed pending play-test confirmation. The existing socket
restriction is retained; no live-server web acceptance is claimed.


## Resume command catalog root — 2026-11-04

CLI-068 fixes the printed resume hint for custom generated chart directories:
include absolute `--load` and `--seasons` paths through existing shell quoting.
Human/compact/trace controls remain, and strict team fingerprint validation is
unchanged. The reported save loads read-only with its original generated bundle,
including saved Hard difficulty and both local roster snapshots. No owner data
is committed or rewritten.

Paydirt `paydirt/interactive_game.py:2801-2849` was consulted; it uses a separate
saved-game loader without an equivalent custom chart-root hint, so no code is
reused. Two synthetic test-first failures demonstrate the omitted argument for
W and explicit saves. Tests then resume from the printed arguments after a
working-directory change, including paths with spaces. Supported Python:
`-m pytest tests/test_cli_save_shortcut.py tests/test_cli.py
tests/test_cli_games.py tests/test_cli_solitaire.py tests/test_cli_input_contract.py
tests/test_cli062_compatibility.py tests/test_interception_context.py -q`:
**91 passed in 9.87s**. Ruff check/format passes on the two changed Python files.


## Early-down punt selection — 2026-11-04

AI-037 traces the reported post-kickoff first-down punt to the late-half candidate
list, which added both punts and field goals on any down. Weighted exploration
could then choose the punt. Coaching v14 excludes punts before fourth down while
retaining field goals and the public fourth-down priorities. All engine-legal
human actions remain. The ordinary tier advances to v14 for future calls on
load under AI-026; explicit development v1–v13 behavior stays frozen, including a
captured v13 seeded selection stream. Engine facts, clocks, dice, chart values,
recorded commands, save schema and observation allowlist are unchanged.

Paydirt `paydirt/computer_ai.py:154-221` was consulted before implementing this
follow-up. Adapt its separation of end-half field-goal opportunities and a
fourth-down punt gate, not its NFL rules, ranges, time units or runtime code.
Tests first produced 37 expected failures and four passing controls. The focused
punt module passes 42 cases, including an independent real-engine Hard candidate
check after a synthetic kickoff. Existing ordinary-load version assertions now
expect the new current version; frozen historical assertions are retained.

Supported Python commands: `-m pytest tests/test_late_half_punt_policy.py -q`
(**42 passed**) and `-m pytest tests/test_late_half_punt_policy.py
 tests/test_late_half_cpu_clock.py tests/test_late_half_cpu_clock_contract.py
 tests/test_razzle_surprise_policy.py -q` (**194 passed before adding the
one extra real-engine case**). Wider coaching/replay/interface verification is
recorded below when complete. This follow-up does not claim milestone acceptance,
benchmark calibration, or a release.

CLI-068's tested resume-hint implementation is `eda44dc`; its 91 related
CLI/save checks and 22 documentation checks passed.


AI-037 wider checks initially found 12 missing v14 API/audit registration/default
updates. The production contracts now accept v14 and both audit default paths
share current-tier defaults; all 63 affected existing checks pass unchanged.
Two complete public-fictional-team Hard-v14 audits (seeds 101/307; coach seed 31;
CPU home/away with reversed arrangements) finish after 172/170 plays. Both
reconcile scores/statistics, structured traces, four 900-second periods and save
continuation, with zero illegal selections and zero early-down punts or punt
preference weight. Comparable situation repeats are 11/35 and 2/25; longest
streaks 3/2, no concentration advisories, RZDZ calls 4/2 and all nine ordinary
plays represented. The 0/2 analysis fallback counts remain explicit; targeted
fallback details are retained locally. These two games are smoke evidence, not
benchmark calibration or proof of optimal strategy. The original owner save also
strictly replays read-only using v14 for future Hard decisions.

Targeted seed-307 fallback review: both records are legal two-point-try
offense calls (6 and 4), with no punt in either preference mixture. The
recorded conversion-analysis fallbacks are not early-down punt selections.


Final combined verification: 1,240 passed in 164.74s, with no reported skips or
warnings, across 66 coaching/replay/interface modules. The supported Python
command was `-m pytest -q` on the sorted union under tests/ of
`test_*coaching*.py`, `test_difficulty*.py`, `test_coaching*.py`,
`test_late_half*.py`, `test_*save*.py`, `test_*replay*.py`, `test_*razzle*.py`,
`test_cli*.py`, `test_api*.py`, `test_history_fixtures.py`,
`test_fourth_down_guidance.py`, `test_public_fourth_down.py`,
`test_issue_tracker.py`, `test_priority_docs.py`, `test_release_player_docs.py`.
Ruff check/format on all changed Python files and `git diff --check` pass.
Complete-game audit calls used `audit_game(*sample_teams(), seed=101,
coach_seed=31, policy="hard-v14", cpu_side="home")` and the reversed samples
with seed=307 and cpu_side="away"; default replay checkpoints remain active.
No private team chart or owner save content is committed. The running owner
interpreter remains on its loaded policy until restart. No push, release or
full milestone acceptance is claimed.

AI-037 tested implementation: `24b3977`. Its final 1,240-case selection,
focused cases and complete-game audits are recorded above. AI-037 and CLI-068
are resolved for owner review, not closed pending confirmation. This is an
owner-feedback follow-up, not a new milestone acceptance or release.

## Owner-requested late-half sequence audit (2026-11-04)

Audit only; no production behavior changed. Before this phase, consulted Paydirt
`paydirt/play_resolver.py:704-815`: it documents the blank-defense Hail Mary and
separate table outcomes, but its T1 calculation uses the tens digit. That distance
implementation is deliberately not reused: Bowl Bound's approved full-feature
T1 is a new offensive total. Checked the local Bowl Bound reference Advanced I-3
(printed p.14), Basic VI-11 (p.11), and VI-13(E)(i), (F), (G) (p.12).

Reconstructed the reported sequence in a disposable engine using the selected
local charts and exact observed rolls. The ordinary Option uses the human blitz;
its retained out-of-bounds fact costs 10 seconds in the late-half window. Hard
v13/v14 then select two legal Hail Mary actions at 20 and 10 seconds. Both actions
correctly bypass the formation picker and resolve against a blank defense. The
first incompletion costs 10 seconds; the second interception remains pending.
Its distance roll is genuine, and the repeated trace across interception and
end-zone choices belongs to the same uncommitted play. Neither decision consumes
another roll, down, clock charge or committed log entry. The accepted end-zone
interception has an actual nine-yard-deep return origin. Completing a touchback
produces own 20, charges the play's 10 seconds exactly once, and advances halftime.
Private reconstruction details remain only in ignored local audit storage.

Two presentation defects remain open, not resolved: CLI-069 (pending reports
fall back to Boot-leg/A Standard instead of Hail Mary/blank defense) and CLI-070
(the context displays raw excess distance rather than the actual nine-yard depth
for beyond-end-line interceptions). Both defects were also reproduced using
fictional teams, both possession directions and a sentinel roll proving no
premature return lookup. The engine's recovery and return arithmetic are correct;
the pending scoreboard still describes the pre-play state until the play commits.

Supported Python validation command:
`/Users/rtulloh/work/bowl_bound/.venv/bin/python -m pytest -q
tests/test_hail_mary.py tests/test_optional_clock.py tests/test_timing.py
tests/test_turnovers.py tests/test_interception_context.py
tests/test_coaching_shared_contract.py tests/test_issue_tracker.py`:
**123 passed in 2.93s**, no reported skips or warnings. These checks establish the
audited mechanics, not optimal late-half AI strategy. No running process, owner
save, private chart, or production code was modified. No milestone acceptance or
release is claimed.


## Pending Hail Mary presentation follow-up — 2026-11-04

CLI-069/070 correct engine-provided pending labels and interception context.
Before implementation, consulted Paydirt `paydirt/play_resolver.py:704-815`.
Adapt named Hail Mary/blank-defense presentation across table outcomes, without
its incompatible tens-digit T1 arithmetic, NFL rules or runtime dependency.
Bowl Bound retains its approved full-feature distance and internal Play.EIGHT
trace routing; there is no new defensive roll or frontend football calculation.

All four pending constructors (interception, end-zone recovery, pass-interference
penalty and return penalty) now share the existing Hail Mary presentation flag
used by completed reports. The defense-label helper now serves both cases.
The location context uses existing MAX_END_ZONE_DEPTH=9 for interceptions beyond
the defending end line; opposite-goal touchdown and own-end-line safety boundaries
remain distinct. Actual turnover/return rules and arithmetic are unchanged.

On a clean unchanged `a30f112` archive, final focused tests fail 30 cases for
the intended labels/context and pass 59 controls. The corrected source passes all
89. Tests preserve both possession directions, A/F inputs without a defensive
roll, ordinary/RZDZ contexts, goal/nine/ten-yard boundaries, return penalties,
pass-interference accept/decline, touchdowns and safeties. Four small authentic
pre-fix saves use only invented charts and captured commands/rolls, produced by
the archive before applying code. They strictly replay and continue, preserving
command/roll/state digests and ordinary current-Hard upgrade. Pending decisions
commit no new time/down/log/return roll; final completion costs 10 seconds once.

No save schema or digest exception is added: pending reports are returned outside
the committed log, completed labels already match, and decision_context already
is excluded. Changed expectations add the missing identity/location checks; no
existing assertion or football outcome is weakened. The simplify review reuses
the label helpers and existing field constants without a new runtime module.
Focused command: supported interpreter `-m pytest tests/test_pending_hail_mary.py
 tests/test_interception_context.py -q` (89 passed). Cumulative results follow.

Owner explicitly confirms the terminal halftime presentation and flow with
"half time looks good" after the pending interception/touchback sequence. The
completed result, boxed line score/scoring/statistics and reciprocal kickoff
announcement were visible. CLI-058 is closed; UI-060's terminal portion is
accepted while web/browser acceptance stays open. This does not confirm
CLI-069/070 or complete M33. Private transcript/team-specific facts are omitted.

Final cumulative command uses the supported interpreter with `-m pytest -q` on
the sorted union under tests/ of `test_cli*.py`, `test_*save*.py`,
`test_*replay*.py`, `test_*razzle*.py`, `test_api*.py`, `test_hail_mary.py`,
`test_pending_hail_mary.py`, `test_interception_context.py`, `test_session*.py`,
`test_turnovers.py`, `test_regulation*.py`, `test_optional_clock.py`,
`test_timing.py`, `test_coaching_invariants.py`, `test_coaching_shared_contract.py`,
`test_late_half*.py`, `test_history_fixtures.py`, `test_*presentation*.py`,
`test_commentary*.py`, `test_issue_tracker.py`, `test_priority_docs.py` and
`test_release_player_docs.py`: **1,218 passed in 130.90s**, 60 modules, no reported
skips or warnings. Pinned Node 24.22.1 `node node_modules/vitest/vitest.mjs run
 src/test/components.test.jsx src/test/noRules.test.js src/test/playLog.test.jsx`:
**49 passed**. Separate documentation/tracker selection passes **22** cases.
Ruff check/format across **592** files and git diff --check pass.

No frontend production code, API interpretation, serializer, coaching policy or
actual turnover resolver changes. This is relevant regression evidence, not a new
full coverage gate, browser acceptance, milestone completion or release. Owner
interpreter, live source, private teams/logs/saves and servers remain untouched.

CLI-069/070 tested implementation: `bc60bb2bd56650b1f3e7d91fc59067b62801112e`. An additional
post-commit focused run passes **89 in 3.37s**. Both tickets are resolved against
this commit and remain unclosed pending owner play-test. CLI-058 alone closes
from the explicit terminal halftime confirmation; UI-060 remains open for web
acceptance. No push, release or restart of an existing interpreter/server.

## AI-038 — late-half field-goal range (2026-11-04)

Owner reports a CPU field goal from deep in its own territory. The conventional
distance helper correctly computes yards to the goal line plus 17. The late-half
comparison nevertheless admits every engine-legal field goal, bypassing the
existing public maximum; exploration can select a guaranteed miss. This is a
candidate guard defect, not an orientation, chart-import or kick-resolution bug.

Before implementation, consulted Paydirt `paydirt/computer_ai.py:154-221`,
particularly the end-half range guard at 189-198. Adapt range-before-selection,
not its NFL thresholds, time units, chart data or runtime code. Bowl Bound already
uses a 55-yard public conventional ceiling. V15 shares that constant between
candidate eligibility, public fourth-down calls and last-snap kicks. Team/season
range configuration remains separately deferred under AI-031.

The synthetic regression first fails 92 cases with 15 passing controls; the
corrected source passes all 107. Both directions, all difficulties, Q2/Q4,
early downs, own territory and the 55/56 boundary are exercised. Attractive fake
kick utilities verify that an unreachable candidate cannot enter exploration;
failed comparisons still take a legal ordinary fallback. In-range early-down
kicks and public fourth-down/last-snap decisions retain their behavior.

Current normal coaching advances to v15. All prior explicit versions remain
frozen, including a captured v14 call stream. Existing current-load revision
assertions in three modules advance 14 to 15 without changing football
expectations. Four authentic pre-fix pending Hail Mary fixtures still strictly
replay and continue with their exact original commands, rolls and states. API/audit/save
policy registrations include all v15 families. The owner's original save strictly
replays read-only and uses v15 for future Hard decisions. Recorded commands,
rolls, random source, team identity, state digests and schema remain unchanged.
No live process is restarted. Wider verification follows below.

Focused command: `/Users/rtulloh/work/bowl_bound/.venv/bin/python -m pytest -q
tests/test_field_goal_candidate_range.py`: **107 passed in 2.12s**. This is an
owner-feedback follow-up, not full milestone acceptance or a release.

Six more range cases reach Q2 own 24 through journaled synthetic engine commands,
then save/load and preview at every difficulty in both directions. The 93-yard
attempt is absent from candidates and the coordinator requests the human's
defensive formation, without changing saved facts. The range module now has 113
cases; combined range/pending Hail Mary/punt/late-half clock checks pass **261 in
9.29s**. An initial 69-module cumulative run passed 1,432 and failed four old
current-v14 expectations in the Hail Mary fixture test. Those expectations now
use the current revision while all past-fact and continuation assertions remain.

Complete-game smoke audits: public samples, Hard-v15, seeds 101/307, coach seed
31, CPU home/away and reversed arrangements. Games finish in 169/166 plays;
scores, statistics, structured traces and four 900-second periods reconcile.
Saved continuation verifies 159/152 steps, with zero illegal calls and zero
analysis fallbacks. Across 66/56 out-of-range offensive selections, field goals
receive no preference weight and are never selected. No early-down punts occur.
All ordinary calls 1-9 appear, RZDZ counts two per game, comparable repeats 4/21
and 5/32, longest streak two and no concentration advisories. These two games do
not establish statistical calibration or optimal strategy. Ignored local audit
artifacts contain only fictional samples; owner charts and saves remain private.

Final cumulative result: **1,442 passed in 177.23s**, no reported skips or
warnings, across 69 modules. Command: supported Python `-m pytest -q` on the
sorted union under tests/ of `test_*coaching*.py`, `test_difficulty*.py`,
`test_late_half*.py`, `test_*save*.py`, `test_*replay*.py`, `test_*razzle*.py`,
`test_cli*.py`, `test_api*.py`, `test_history_fixtures.py`,
`test_fourth_down_guidance.py`, `test_public_fourth_down.py`,
`test_issue_tracker.py`, `test_priority_docs.py`, `test_release_player_docs.py`,
`test_field_goal_candidate_range.py`, `test_pending_hail_mary.py` and
`test_interception_context.py`. Ruff check and `ruff format --check` pass on all
11 changed Python files; `git diff --check` passes. The two complete-game audit
calls were `audit_game(*sample_teams(), seed=101, coach_seed=31,
policy="hard-v15", cpu_side="home")` and reversed samples with seed 307 and CPU
away, preserving default replay checkpoints and stand-in seed. The owner-facing
source will be advanced only after committing these tested changes. No push,
release, interpreter restart or full M33 acceptance is included.

AI-038 tested implementation is `b120678`. The ticket is resolved for owner
review and remains unclosed pending play-test confirmation. The 1,442-case
cumulative run and two full-game audits above passed on this production code.

## Owner sequence audit — penalty, interception and end-zone return (2026-11-04)

Consulted Paydirt `paydirt/play_resolver.py:136-180` (penalty choice and retained
defense) and `:818-880` (chart lookup). These are structural comparisons only;
no NFL rules, private data or runtime code are reused. Bowl Bound authority is
the published Priority Chart (printed p.34), Basic VI-4 and VI-13, the approved
timing profile, and the maintained priority, penalty and turnover documentation.

A disposable local reconstruction with the selected private teams and exact
reported physical rolls confirms the whole sequence. Defensive incomplete beats
offensive QT without a supplemental roll. A fixed offensive foul rerolls the same
play against the original defensive cell; declining continues the prepared
interception, whose distance takes priority over ordinary defensive yardage.
Accepting the interception and choosing an end-zone return are separate decisions.
The full return distance includes the depth in the defending end zone.

The prior pending normal charge is applied before the next snap; the incompletion
then costs ten seconds. All penalty/interception/end-zone prompts retain the
committed state and consume no time or additional snap. Completing the flagged
turnover costs ten seconds once. A sentinel roll confirms no hidden dice; repeated
trace entries preserve existing consultations. Final possession, down/distance,
spot, score, statistics, log lengths and timing charges reconcile. Private script
and output remain ignored under `private-data/sequence-audits/`; no owner save,
live game or historical chart is modified. No defect or behavior change was found.

Validation: supported Python `-m pytest -q tests/test_resolution.py
tests/test_penalties.py tests/test_session_penalties.py tests/test_turnovers.py
tests/test_optional_clock.py tests/test_timing.py tests/test_interception_context.py`:
**200 passed in 3.65s**. The documentation/tracker selection
(`test_issue_tracker.py`, `test_priority_docs.py`, `test_release_player_docs.py`)
passes **22 in 0.67s**; `git diff --check` passes. This is an audit of an existing sequence, not a new
milestone acceptance or closure of earlier pending owner play-test tickets.

## CLI-071 — halftime-style final summary (2026-11-04)

Owner reports that the final terminal screen has only status and Hard call counts.
Consulted Paydirt `paydirt/interactive_game.py:3834-3844` and `:4245-4265` before
implementation: halftime and final use the same box-score renderer, with opponent
analysis following the final boxes. Adapt the shared renderer and ordering;
do not copy NFL rules, scoring calculations, team data or runtime code.

The CLI now reuses its existing halftime layout for FINAL STATS, SCORING SUMMARY
and TEAM STATISTICS. The engine records committed point deltas by regulation
quarter or overtime round before advancing periods, and supplies immutable final
recap facts. The CLI only aligns these facts. Zero-score periods remain visible,
long team names expand all borders together, and no second-half kickoff footer
appears at full time. Existing halftime text and its API contract are preserved.

The final recap appears once on completion or when opening a finished save,
before Hard call counts. Inspect/save commands leave that recap consumed locally;
a successful load resets both final presentation flags for the replacement game.
The period totals are rebuilt by normal replay, without changing the save schema,
semantic view digests, command journal, dice, coaching policy or football rules.
No new engine field is added to the API view.

Test-first evidence: after correcting fixture setup to use the synthetic engine's
actual automatic touchback and conversion ownership, all six new cases fail on
unchanged production code for the missing final boxes or recap method. Coverage
includes scoring in all four quarters, an unsuccessful final two-point try,
scoreless regulation, two overtime rounds, compact/full rendering, restored final
saves and successful in-session replacement. Final rendering leaves every saved
game fact unchanged; only fresh export timestamp/integrity are excluded from that
comparison. Focused halftime/final/Hard-summary checks pass **25 in 3.39s**.
Further cumulative validation and tested commit reference follow below.

Final focused run: supported Python `-m pytest -q tests/test_final_summary.py
tests/test_halftime_presentation.py tests/test_postgame_call_summary.py
tests/test_issue_tracker.py tests/test_priority_docs.py tests/test_release_player_docs.py`:
**49 passed in 4.08s**. The eight-case final module includes two additional tests
for successful/failed untimed final conversions. Cumulative run: **604 passed in
77.62s**, 40 modules, no reported skips or warnings. Command: supported Python
`-m pytest -q` on the sorted union of `test_cli*.py`, `test_*save*.py`,
`test_*replay*.py`, `test_regulation.py`, `test_overtime.py`, `test_optional_clock.py`,
`test_timing.py`, `test_statistics.py`, `test_conversion_presentation.py`,
`test_halftime_presentation.py`, `test_postgame_call_summary.py`,
`test_final_summary.py`, `test_history_fixtures.py`, `test_api*.py`,
`test_issue_tracker.py`, `test_priority_docs.py` and `test_release_player_docs.py`.
The cumulative run began before those two additional conversion cases were added;
the later 49-case focused run passes both. Ruff check and format check pass on
the five changed Python files, as does `git diff --check`. No frontend change,
full milestone acceptance, push or process restart is included.

CLI-071 tested implementation: `15b6c9e`; all eight final-summary cases pass again
after commit. Resolved pending owner play-test, not closed.

## Private owner game-log audit (2026-11-04)

The owner authorizes auditing the local captured terminal log. Reviewed Paydirt's
shared halftime/final rendering references above, and adapted Bowl Bound's own
`coaching_audit.py:315-339` scoring/statistics/clock reconciliation. In particular,
do not inherit a nonempty-cell assertion: a legitimate defensive blank is still
a valid consulted chart fact.

The capture contains five launches and a rejected load, including abandoned
continuations. Isolated the completed continuation and linked it to its strictly
replayed original checkpoint rather than counting all launches as one game.
All 96 report blocks in the first launch match trace prefixes of the 83 committed
checkpoint plays, and the boundary display matches. On a disposable copy, matched
all 137 report blocks, including exact physical dice, consulted cells, narration
and 119 following displayed checkpoints in the completed continuation. Final
scores, period point totals, statistics, sequential committed play numbers and
all four 900-second clocks reconcile. No pending or unsupported committed result
remains. All observed completed-run CPU punts are fourth-down calls and its
field-goal attempts are within the public conventional range. Earlier abandoned
branches contain the previously tracked AI-037/038 findings.

The capture omits typed input and the CPU formations ignored by three QB Sneaks.
Those hidden formation identities/order and the future coaching RNG cannot be
recovered from trace text. Reconstruction uses explicit harmless formation
placeholders on those ignored-defense snaps; this does not change their football
outcomes, dice, statistics or display. It is audit evidence, not an exact coaching
continuation save or a policy-optimality claim. No historical transcript, chart,
save, local path identifier or detailed report is committed. Local evidence and
the completed game's final boxes remain under ignored `private-data/`.

One new defect is [CLI-072](issues/CLI/CLI-072.md): a QB Sneak names a running back
as the carrier. Verified independently with synthetic charts/roster, without
changing production commentary. The recorded football result is correct. Last-
minute third-and-long run selection is a strategy observation for broader
calibration, not evidence that a legal call or clock transition is wrong.

## Alpha 5 release preparation (2026-11-04)

The owner authorizes merge/push/build/release and explicitly selects only the
existing fictional samples. [Release preparation](release-alpha5.md) records
the Paydirt consultation, sanitized public lineage, synchronized version update,
verification and outstanding browser/network/native gates. Generated charts and
season-validation research remain separate. [DEV-068](issues/DEV/DEV-068.md)
tracks completion; no publication or browser acceptance is claimed by preparation.


Alpha 5 exact-stage validation exposed DEV-069: the new halftime component was
missing from the explicit frontend selection. A meaningful staged-import test
fails before the one-entry manifest fix; 40 packaging cases pass after it. Fresh
exact-stage npm install/build, runtime assembly, isolated entry-point imports and
ZIP inventory/hash checks pass, with exactly the 15 original sample files. The
75-file runtime input remains distinct from a native executable. Metadata, docs,
workflow, standalone/smoke and tracker checks pass 127 cases; full frontend again
has 143 passed and four unavailable after the EPERM hook, exiting 1. No skips
or acceptance criteria are weakened. The owner-requested persistent release goal
continues through a genuine verified build/publication; 403 upstream access and
required local-service/browser failures remain explicit.

## Alpha 5 completed gate receipts and resumed access check (2026-11-04)

Reviewed Paydirt release-readiness notes again on resume: retain explicit failed
checks and separate engineering, calibration and native acceptance claims. The
tested candidate is `170f5e053715ae7c5abb5f73a7019f5ce25cda75`. Its full Python
coverage command exits 1 after 3,947 passes, five launcher EPERM failures and six
wheel build-fixture errors in 1,026.89 seconds; branch coverage is 93.02%.
The combined `4ca8858` predecessor has 3,946 passes and the same failures/errors.
No tests are skipped, weakened or modified to hide these failures.

All seven wheel packaging cases pass separately in an immutable candidate archive
with the verified existing build-backend cache and network disabled. Two isolated
runtime games using only original fictional samples finish with 172/166 committed
plays, four 900-second periods each, eleven strict save/replay checkpoints and
zero missing imports. The corrected temporary smoke probe reconciles elapsed
time rather than nominal charges clamped at period boundaries. This evidence
does not replace the failed complete gate or certify native executables.

DEV-069 is resolved against `170f5e0` after its 40 packaging tests, 127-case
release selection and actual clean-stage frontend/runtime/archive checks; it
remains unclosed pending native acceptance. DEV-068 stays open. The owner resumes
work after an explicit pause; bounded probes still show GitHub/npm 403, loopback
EPERM and Chromium MachPort 1100. No full-gate process remains live, and no
upstream publication occurs. See [release evidence](release-alpha5.md) for exact
scope, command, limitations and remaining authorized steps. Documentation-only
receipt updates require existing documentation/tracker checks, not artificial
behavior tests.

Resume validation: supported Python `-m pytest -q tests/test_release_metadata.py
tests/test_release_package.py tests/test_release_player_docs.py
tests/test_tests_workflow.py tests/test_standalone_build.py
tests/test_standalone_smoke.py tests/test_issue_tracker.py` passes **127 in
3.51 seconds**. Regenerated the issue index; `git diff --check` passes. Only
five documentation/tracker files change in this receipt update, so Python
formatting and a repeat of the unchanged full runtime gate are not required.

## Main-thread Alpha 5 local acceptance — 2026-11-04

After restored execution/network access, implementation `94e6ecb` passes the
complete pinned Python 3.13.17 gate: 3,958 tests in 787.96 seconds, 93.35%
branch-aware coverage. Ruff check/format (602 files), pip check, 147 frontend
unit tests, production build, online npm audit (zero vulnerabilities) and all
54 real-engine Chromium cases pass. Existing install/performance notices remain
recorded in [Alpha 5 preparation](release-alpha5.md). No skips/assertion weakening
or production changes are introduced by the DEV-070/DEV-071 test-harness fixes.
The four staged UI tickets now have valid browser evidence and are resolved;
owner visual/play-test closure remains separate. Exact sample selection and
sanitized-history checks pass. Native builds and publication remain pending.
