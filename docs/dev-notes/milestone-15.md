# Milestone 15 — timing and regulation flow

## Scope and acceptance

- Immutable quarter clock with shortest-category timing, late-half out-of-bounds
  windows, no two-minute warning, and three timeouts per side/half.
- Engine-owned opening dice toss and kick/receive choices, reciprocal second-half
  kickoff scheduling (corrected in Milestone 30), and quarter/half transitions.
- Post-TD/PAT, field-goal and safety free kicks; carried try fouls are enforced
  on the following kickoff, including half-distance.
- Pending clock management before 20/30-second runoff: timeouts, hurry-up and
  spike are mutually exclusive adjustments. Spike spends a down; kneel loses two
  yards; neither consumes dice.
- Hail Mary at 1–20 seconds of Q2/Q4, outside tries/untimed downs; the rule table,
  QT, T1 distances and PI use actual traced rolls and blank defense.
- Hurry-up S/R table and cancelled-defense false-start/bad-snap hazards, including
  punt F-13 and field-goal F-7. Printed fouls retain their chart semantics.
- Complete the live play, required try and defensive-penalty untimed down at zero;
  resolve expiration once and reject gameplay after regulation stops. Historical
  regular-season ties are final; overtime-era ties stop for Milestone 16.
- UI displays engine-provided quarter, clock, timeouts and legal choices.
- Complete synthetic engine/browser games reconcile clocks and scoring.

## Test-first evidence and changed expectations

Initial timing/regulation tests failed because their modules did not exist.
No-huddle tests demonstrated missing hurried assessment/preparation behavior;
API regulation creation failed validation; the scoreboard lacked quarter/clock
nodes. RULE-001 tests reproduced consecutive-return-foul rejection, missing
literal-TD endpoint, blank-return rejection, lost recursion context, duplicate
pending traces and a penalty dropped before a return-fumble recovery. A nested
recovery test reproduced a wrong-team end-zone chooser. Each has a synthetic
regression. Unsupported end-zone branches are disabled before rolling.

The Hail Mary QT test initially expected -4, but its synthetic team has +4 in that
QT cell. It now follows the fixture, rather than inventing a mandatory sack.
Browser fixtures use supported synthetic season 2002 instead of 2026 and send a
fixed seed while retaining real engine dice/responses. The opening returned
kickoff adds one report and ten seconds. Tests count that report, resolve pending
runoff and expect a scheduled kickoff instead of the old scoring-demo boundary.
Kneel is now an intentional engine action, not a forbidden inherited NFL label.

## Owner decisions

Recorded in the rules profile:

1. Preserve printed fixed-yardage/PI fouls when hurried; special table only for S/R.
2. DEF R total-10 dash means no foul: retain assessment roll, apply no yardage and
   resolve the return on the next chart roll, not an invented zero-yard return.

### Corrected implementation policy — 2026-10-31

Milestone 15 incorrectly interpreted the other player's second-half choice in
Basic V-3 as choosing which team kicks or receives. The choice is the kick type
(normal or onside) by the team assigned to kick. The order is reciprocal: the
opening kicker receives the second-half kickoff, and the opening receiver kicks.
Onside kicks remain unsupported, so the normal kickoff is automatic. See
[Milestone 30](milestone-30.md) and the updated
[rules profile](../rules-profile.md).

## Architecture and compatibility

RegulationGame composes PlaySession rather than duplicating chart/priority rules.
Reports carry semantic timing facts, not descriptions to parse. Clock charges
commit after football decisions and clock choices. Scores remain ledger-derived.
The browser requests regulation explicitly; the API default remains drive mode
for compatibility. Existing in-memory drives are not migrated. The backend serving
the manual game was not restarted.

## Explicit boundaries

Overtime, saves, statistics, computer coaching, alternate/hybrid timing and advanced
kicking remain later milestones. This entry point creates regular-season games;
postseason selection belongs to historical overtime.

Inherited end-zone recovery returns are disabled if their return column contains
non-numeric chains; touchback remains available. Return-foul acceptance whose
enforcement spot cannot be represented is disabled with a reason; decline remains
available. These are explicit limits, not claimed complete chain support. Missing
or ambiguous imported cells never become zero.

RULE-001 hardening preserves rolls once, offers separate same-side foul choices,
delays cancelled fumble recovery and propagates nested recovery/recursion/hurry
context. Opposing return fouls replay only the return, not the interception.
Normalized NO_CHANGE means no advance, not missing data.

UI-005 kick descriptions remain Milestone 19; UI-011 dice colors remain Milestone
20. Nothing was pushed/published, and no private data was added.

## Validation

- `.venv/bin/python -m pytest --cov --cov-branch -q`: 1,326 passed;
  91.61% branch-aware coverage (75% gate). No skips or warnings.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: 111 files already formatted.
- Frontend `npm test`: 32 passed; `npm run build`: passed.
- Frontend `BB_E2E_CHANNEL=chrome npx playwright test`: nine passed, including a
  complete regulation game, quarter transitions and halftime kickoff scheduling,
  clock controls, conversions,
  score reconciliation and final-state immutability. Installed Chrome is used
  because bundled Playwright Chromium is absent.

### Grilling Notes

**Assumptions verified:** 5/5: engine-only timing/legality, conversion-before-
expiration ordering, halftime chooser/reset, immutable completion, and compatibility
without restarting or migrating live sessions. Evidence: timing/regulation tests,
API tests and the complete browser game.

**Open Questions:** 2 → 0. Printed hurry fouls and the DEF R dash were resolved by
explicit owner decisions, recorded above and in `docs/rules-profile.md`.

**Status:** READY. Remaining end-zone limitations are explicit disabled choices,
not silent fallback rules. Overtime/AI/save scope remains deferred.

**Key revision:** prevent unsupported return branches before consuming dice, and
retain recovery-team context through nested fumbles. Rollback is to the unchanged
API drive mode/UI mode selection; there is no persistent schema or save migration.
A restart loses in-memory sessions, so rollback must not casually restart a live game.


Implementation committed as `402f7d142c2cdc6920648250e5dbe29b548dc240`.
Focused acceptance command:

```bash
.venv/bin/python -m pytest tests/test_timing.py tests/test_regulation.py tests/test_hurry.py tests/test_hail_mary.py tests/test_return_audit.py tests/test_api_regulation.py tests/test_issue_tracker.py -q
```

Result: 121 passed. RULE-001 is resolved against this tested commit, not closed;
manual play-test confirmation of its rare branches remains outstanding.
