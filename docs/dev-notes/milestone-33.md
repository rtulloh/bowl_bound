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

Changed existing expectations are limited to the scrimmage fumble decline label
(completed recovery/possession instead of unresolved recovery) and three assertions
of the current replay-profile identifier. The label fixture now supplies its
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
