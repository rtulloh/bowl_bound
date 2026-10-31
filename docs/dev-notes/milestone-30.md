# Milestone 30: Fix second-half kickoff order

## Paydirt and Bowl Bound rule references

Reviewed relevant local Paydirt implementation and tests before planning:

- `../paydirt/paydirt/game_engine.py:5707`: the second-half kickoff is assigned
  to the opening receiver.
- `../paydirt/tests/test_half_ending_score_flow.py:121-140`: synthetic tests
  verify the second-half kickoff after either half-ending score path.

This assignment matches the reciprocal order confirmed by the owner. Adapt only
the deterministic assignment and test pattern; do not import Paydirt/NFL rules,
engine code, data, or dependencies.

`docs/reference/bbrules2007.pdf`, Section V.3 (PDF page 7, printed page 4), says
the other player has a choice at the beginning of the second half. The current
implementation misreads this as choosing whether to kick or receive, allowing
the same team to kick off both halves. The owner clarified that the second-half
choice is kick type (regular or onside) for the team assigned to kick. The
first-half kicker receives the second-half kickoff, and the opening receiver
kicks. Onside kicks are unsupported, so the regular kickoff is the only
available action and no choice prompt is needed.

## Acceptance

- Both possible opening kick/receive elections produce the fixed reciprocal
  second-half kickoff.
- Halftime does not offer a kick/receive choice or consume an extra play or dice.
- The second-half clock and timeout budgets are set correctly, and the assigned
  kickoff is the next legal action.
- The normal kickoff is automatic because onside kicks are unsupported.
- Compatible pre-M30 saves still replay; old halftime choices are not offered to
  players and are handled only for supported legacy save replay.
- Rules-profile, roadmap, ticket, and milestone notes record the source wording
  and corrected interpretation.

## Validation

- Test-first evidence: before the engine change,
  `.venv/bin/python -m pytest tests/test_regulation.py::test_halftime_schedules_reciprocal_kickoff_and_resets_timeouts -q`
  failed for both opening choices because the engine exposed `halftime_choice`.
- Focused engine, save, timing, CLI and sample tests: 190 passed.
- `.venv/bin/python -m pytest --cov --cov-branch -q`: 2,606 passed; 93.29%
  branch-aware coverage (75% minimum).
- `.venv/bin/python -m pytest tests/test_issue_tracker.py -q`: 18 passed.
- `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`: passed.
- `git diff --check`: passed.
- In `frontend/`, `npm test`: 120 passed across 16 files.
- In `frontend/`, `npm run build`: passed.
- In `frontend/`, `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<isolated synthetic root> npm run test:e2e`:
  33 passed against the real engine. Node emitted its environment warning that
  `NO_COLOR` is ignored when `FORCE_COLOR` is set; there were no skipped tests.

All browser fixtures used the fictional sample teams and synthetic charts.
