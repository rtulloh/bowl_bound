# Milestone 33 — Core playability and validation status

## Scope

The owner prioritized five gameplay and fairness tickets for the next milestone:
[AI-027](issues/AI/AI-027.md), [RULE-041](issues/RULE/RULE-041.md),
[RULE-042](issues/RULE/RULE-042.md), [UI-041](issues/UI/UI-041.md), and
[AI-010](issues/AI/AI-010.md). [DEV-059](issues/DEV/DEV-059.md) is included so
routine validation and the slower standalone release build have clear, separate
GitHub status.

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
