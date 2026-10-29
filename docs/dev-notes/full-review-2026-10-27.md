# Full code review — 2026-10-27

Covers every milestone since the Milestone 18 full review (commit `77d32ec`):
**18a** (engine hardening), **19** (human-playable UI), **20** (baseline
computer opponent), **20a** (terminal play-testing) and the uncommitted **21**
(chart-aware coaching, difficulty tiers, Easy helper, audits). Four independent
read-only reviews were run — one per area — plus a read-only survey of the local
Paydirt repository for AI, helper, audit and documentation ideas. Findings were
checked against code before ticketing; they include reproduced defects and
untriggered maintenance risks, not 40 independently reproduced failures.
All evidence is synthetic/public-safe; no historical charts, saves or private logs were used.

## Verified High findings

- [AI-003](issues/AI/AI-003.md): Hard's one-action utility makes any possession
  change cost a fixed minimum, so Hard almost never punts and scores a made field
  goal negative. Root cause of the "two punts in eight games" audit observation.
- [AI-004](issues/AI/AI-004.md): two-point tries and overtime series are
  evaluated as ordinary scrimmage from the 2 (no phase in the observation).
- [RULE-011](issues/RULE/RULE-011.md): a returner recovering its own return
  fumble receives second down and offensive labels instead of a new series.

## Tickets opened

| Area | Tickets |
| --- | --- |
| Coaching (21, fix before commit) | AI-003, AI-004, AI-005, AI-006, AI-007, AI-008, AI-009, CLI-042, CLI-043, DEV-025, DEV-026 |
| Coaching follow-ups (22) | AI-011, AI-012, AI-013, AI-014, AI-015, AI-016, AI-017, AI-019 |
| Engine rules (22, except RULE-011 moved to 21) | RULE-011, RULE-012, RULE-013, RULE-014, RULE-015, DEV-022 |
| API / UI / flow (22) | API-002, API-003, UI-036, UI-037, FLOW-002, CLI-044, CLI-045, DEV-024, DEV-028 |
| Test coverage and tooling (23) | AI-010, AI-018, RULE-016, UI-038, DEV-023, DEV-027 |

Milestone assignment follows the tracker rule: findings in shipped milestones go
to the next relevant follow-up milestone, not back to the accepted milestone.
Rule and behavior fixes are assigned to 22 and coverage/tooling to 23; the owner
may prefer a dedicated hardening milestone (as 18a was) and can reassign.

## Paydirt consultation

Reviewed read-only: `paydirt/computer_ai.py`, `ai_analysis.py`,
`offense_strategy.py`, `game_engine.py` (kneel-out query, call history),
`tests/ai_audit.py`, `tests/run_ai_audit.py`, `tests/semantic_audit.py`,
`tests/run_full_season.py`, `tests/test_ai_*.py`, `docs/ai-difficulty.md`,
`docs/ai-auditing.md`, `docs/dev-notes/ai-playtesting.md` and its AI tickets.

Adopted as ideas (tickets above): engine-owned kneel-out query; score/time/
aggression-aware fourth-down and two-point rules; bounded urgency gradient with
run floor; situation-bucketed, decayed, floored repetition discount shared with
the audit; situational defensive guards ahead of learned weights; named behavior
profile; audit probability vectors, concentration warnings, ledger/period
reconciliation and redacted errors; RNG-neutrality tests for every coaching
path; exact-mixture tests via patched coach RNG; play-test protocol.

Deliberately not reused: NFL field-goal tiers and 1983 tendencies, two-minute
warning/no-huddle/spike/OOB mechanics, onside kicks (Bowl Bound defers advanced
kick options to Milestone 22), cross-game AI persistence, UI-side chart-strength
defaults (violates the engine-is-source-of-truth rule), and lazily seeded AI
streams derived from the dice RNG state (Bowl Bound's per-observation hash is
more robust). Paydirt's own defect history (AI-010, 011, 013, 019, 020, 021) was
used as a list of anti-patterns to avoid.

## Items verified correct

Concealed-call privacy in API, CLI, saves and error text; analysis dice never
touch the gameplay tape; Hard history reconstructs identically after load;
legacy baseline/chart-v1 digests unchanged; Easy helper never zeroes excluded
cells and ranks limited estimates last; goal-line versus end-line
classification, nine-deep interception cap, white-face depth roll, declined
penalty continuation without rerolling, own-recovery foul enforcement with
half-distance, spike withheld on fourth down, field-goal availability and
period-boundary behavior; no NFL rule assumptions in reused UI components;
CLI shortcut bindings never collide within a single state across sampled games.
