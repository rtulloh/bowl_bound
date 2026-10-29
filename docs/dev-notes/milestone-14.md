# Milestone 14 — scoring and conversions

## Scope and acceptance

- Engine awards touchdowns (6), field goals (3), and ordinary safeties (2).
- A touchdown offers the scoring team a dedicated one-point PAT or two-point try.
- PAT resolution uses one real offensive roll and only normalized PAT outcomes.
  The synthetic test enumerates all 216 physical offensive combinations and
  deliberately conflicts PAT data with the field-goal column.
- Two-point tries begin at the opponent 2, preserve normal priority, called/resolved
  plays and actual chart traces, and finish after one completed live play.
  Accepted/offsetting/pre-snap fouls can replay; defensive conversion TD returns
  award two, not six or another conversion.
- Successful two-point tries can retain defensive 5Y/15 fouls for the following
  kickoff; the approved DEF15 typo interpretation retains fifteen yards.
- An immutable append-only scoring ledger links every award to a committed report.
  Score totals derive solely from the ledger. Duplicate decisions cannot award twice.
- Thin API exposes engine phase, status, scoring and carried kickoff penalties.
  The UI displays conversion choices/status and the scoring ledger without rules.
- Real-engine Chrome tests drive touchdown → PAT and touchdown → two-point try.

## Test-first evidence and changed expectations

`tests/test_scoring.py` first failed to collect because the scoring module did not
exist. After adding the ledger/PAT module, session scoring tests demonstrated eleven
expected failures: touchdowns ended the demo immediately, conversions were unknown,
and ordinary safety outcomes were unsupported. Carry-forward tests then demonstrated
two missing-choice failures. Frontend tests failed on premature Final wording and
a missing scoring-ledger component before implementation.

Prior assertions changed for specific new rules, not to weaken coverage:

- An offensive or defensive touchdown now awaits the scoring team’s conversion
  instead of immediately setting finished. Further snaps remain blocked.
- Safety-producing penalty declines are now enabled; declining applies exactly
  one two-point safety and closes the pending decision.
- The API refuses play while a conversion is pending and after it completes.
- Null field state displays engine status rather than unconditionally saying Final.

The browser fixture makes dedicated synthetic PATs good on every roll so its
expected seven-point total is independent of randomly selected seeds. PAT failures
are separately tested in the engine and session, including an away scorer.

## Boundaries and follow-ups

No clock, regulation, post-score kickoff scheduling, safety free-kick scheduling,
final-try eligibility, or overtime restriction was added; those are Milestones 15–16.
Carried kickoff penalties are recorded, not yet marked against a scheduled kickoff.
Advanced blocked-PAT options remain unavailable. Existing ordinary variable-yardage
and turnover-return limitations are not silently rerolled or treated as zero.
[RULE-001](issues/RULE/RULE-001.md) records inherited turnover-chain edge cases for
Milestone 15 hardening; the conversion tests do not claim to cover those rare paths.

[FLOW-001](issues/FLOW/FLOW-001.md) tracks the premature Final wording; the general
usability findings and user-requested labels remain assigned to Milestone 19.
The running manual-test backend was not restarted because its sessions are in memory.

## Validation

- `.venv/bin/python -m pytest tests/test_scoring.py tests/test_session_scoring.py tests/test_api_scoring.py tests/test_session.py tests/test_session_penalties.py tests/test_session_turnovers.py tests/test_session_special_teams.py tests/test_special_teams.py tests/test_api.py -q` — **167 passed**.
- `.venv/bin/python -m pytest --cov -q` — **1,222 passed**, **91.40%** branch-enabled coverage (75% floor).
- `.venv/bin/ruff check .` — passed.
- `.venv/bin/ruff format --check .` — **101 files** already formatted.
- `npm test -- --run` in `frontend/` — **31 passed**, including no-client-rules checks.
- `npm run build` in `frontend/` — passed.
- `BB_E2E_CHANNEL=chrome npx playwright test` in `frontend/` — **7 passed** against the real API/engine.
- `.venv/bin/python scripts/build_issue_index.py` and `.venv/bin/python -m pytest tests/test_issue_tracker.py -q` — index regenerated; **17 passed**.

No skips or warnings in the final gate. An intermediate cumulative run failed
only because newly reported tickets had not yet regenerated the index; the index
was regenerated and the complete gate rerun successfully. No historical/private
charts or live-game records were added. No publication or push was performed.
