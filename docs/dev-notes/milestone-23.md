# Milestone 23 — Regression-gate follow-ups

## Scope

Resolve the public-safe findings in the 2026-11-01 review of milestones 22 and
32. Each ticket remains independently test-first, committed after focused checks,
and resolved only after tested implementation. Owner play-testing is required
before gameplay or UI tickets are closed.

## Paydirt consultation — 2026-11-01

Reviewed the local Paydirt repository before beginning the follow-up work:

- `tests/run_full_season.py:33-117` validates final state, period scores, score
  ledgers, and conversion periods independently. Bowl Bound will adapt this audit
  discipline for DEV-054 through DEV-056, while retaining its college rules and
  local-only data policy.
- `tests/test_onside_kick.py:44-128` exercises both recovery boundaries and ball
  coordinates. Its boundary-test organization is useful for Bowl Bound special
  teams, but its NFL engine behavior and chart data are not reused.
- `tests/test_save_game.py:1-130` compares restored state and continuation. Bowl
  Bound instead verifies command-and-dice replay with its own synthetic charts;
  Paydirt save format and team data are not reused.

No Paydirt runtime dependency, rules implementation, private data, or schedule
logic is added.

## Ticket work

### RULE-033 — 2026-11-01

- Synthetic tests first reproduced wrong numbered Wild Cards stopping Option runs.
- The resolver now requires both Play 5 and the exact Option branch before the
  Wild Card stop applies. The focused Advanced II, resolution, and coaching
  evaluation regression set passed before commit.

### RULE-034 — 2026-11-01

- Synthetic tests first showed that an exact WCRZDZ call recorded an incomplete
  pass without applying the normal state transition.
- The no-dice result now uses the ordinary prepared-play path. This preserves the
  required incomplete timing, statistics, turnover-on-downs behavior, regulation
  integration, and save replay without duplicating transition logic.

### RULE-035 — 2026-11-01

- Synthetic penalty-reroll tests first reproduced stale conditional-defense
  doubling for QR, QT, Sprint Out, and Boot-leg outcomes. They also cover a
  PASS guess changing from incorrect before the reroll to correct afterward,
  plus W-marked free defenders.
- The shared conditional-defense predicate now evaluates the rerolled resolved
  play and cell. Penalty preparation and the Razzle-Dazzle decision path retain
  the Advanced II call metadata so that they can make that assessment without
  guessing from a stale resolution.
