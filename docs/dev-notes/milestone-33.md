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
