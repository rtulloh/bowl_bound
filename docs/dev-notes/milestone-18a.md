# Milestone 18a — Engine hardening

## Scope and execution plan

Authorized by the owner after the Milestone 18 review. RULE-002–009 move from 19
to 18a; UI, API hardening and broad refactors remain out of scope.

1. Reproduce and correct goal-line/end-line turnover decisions, then share the
   ordinary return procedure with end-zone recovery returns and preserve depth.
2. Resolve selected full-feature variable distances and defensive turnover spots
   through a shared helper, retaining chart provenance and observed rolls.
3. Preserve offensive recovery down/distance on return fouls; allow penalty decline
   to continue into turnover decisions without rerolling already consulted cells.
4. Verify offered field goals, fourth-down spike eligibility and period-ending
   runoff reports against the approved rules profile.
5. Bump replay engine profile rather than silently accepting old outcomes; exercise
   save/resume, conversions, regulation, overtime, statistics and API transport.
6. Update rules/behavior docs and ticket evidence; run focused and full cumulative
   gates, review and commit with `milestone 18a: harden engine correctness`. Stop
   before starting UI work or restarting the running backend.

### Grilling Notes

**Assumptions verified:** 4/4. Turnover coordinates are offense-relative
(turnovers.py); goal/end lines differ (Basic VI-13 A/B); DS/X/T semantics and
independent offense/defense rolls are specified (Basic VI-3); saves replay engine
commands under a versioned profile (save_game.py).

**Open Questions:** 2 -> 0. Basic VI-13 D(ii)/E(i) specifies white-face depth for
fumbles beyond the opponent end line, versus a fixed nine-yard depth for
interceptions beyond it. Basic VI-13 F(i) specifies touchback, not safety, when
an elected end-zone return never crosses the goal line. These were incompletely
covered by the review; tests must distinguish new possession from own recovery.

**Status changed:** No; READY. Rules and architecture answer the remaining choices.
Tests may expose stale expectations; update only with a documented rule citation.

**Key revision:** Do not blindly mirror special-team code. Preserve an explicit
live-ball return origin (FieldState only permits scrimmage spots) and count depth;
never use its in-field placeholder to measure a live return or reuse an old save
profile after rule fixes.
Rollback is the dedicated milestone commit, not selective reverting of shared rules.

## Test-first evidence

- Initial end-zone regressions: 27 failed, 10 passed before implementation.
- Depth/NO_CHANGE return regressions: 7 failed, 37 passed before implementation.
- Ordinary variable-yardage suite: 8 failed, 1 passed before implementation;
  complete physical face enumeration covers every reference.
- Declined scrimmage turnover fouls: both new cases failed with decline disabled.
- Own-recovery accepted foul: failed with defensive-recovery classification; a
  further boundary test failed first with a premature first down after recovery
  had passed the line to gain. A retreating own return also failed first (second
  and fourteen instead of fourth and three). Preserve the original scrimmage state.
- Field-goal availability, fourth-down spike and distinct boundary-report tests
  each failed before their changes.
- Old-profile rejection failed first by invoking the team loader; corrected
  profile checking rejects before lookup/replay.
- In-field return into own end zone and own-recovery touchdown classification
  each failed before their related turnover fixes.

## Changed expectations

- Basic VI-13 D(ii)/F(i): five-deep recovery and 12-yard return reaches own 7, not
  own 12. End-zone returns with penalties/no-change/fumbles are now available.
- Basic VI-13 D(ii): the nested fumble beyond the opponents' end line now consumes
  a separate observed white-face depth roll before recovery; the full trace grows
  from four to five entries. No existing roll is hidden or invented.
- Basic VI-3: ordinary/supplemental variable outcomes now consume/trace distances
  and commit offensive statistics, rather than remaining unsupported/pending.
- Basic VI-4: declining a prepared turnover foul now enables the real interception/
  fumble flow, instead of requiring acceptance.
- Existing period-runoff tests now require an explicit boundary response while
  still asserting unchanged play log and no extra dice; the old report is not
  returned as if a new play occurred.
- New-test fixture corrections: no-defense synthetic return teams prevent
  unintended three-yard additions; enforcement from own 7 caps five yards at
  three under half-distance, reaching own 4; operation assertions use enum values
  rather than printed matrix abbreviations; DiceSequenceError is the documented
  exhaustion exception; save incompatibility deliberately uses a generic error.
  None weakens an original behavioral assertion or adds a skip.

## Final validation and acceptance

All acceptance behaviors for RULE-002–009 are covered by synthetic regressions.
Final cumulative command: `.venv/bin/python -m pytest --cov -q --tb=short`
— **1,564 passed; 92.84% branch-aware coverage**, above the enforced 75% floor.
No skips or warnings were reported. Focused command:
`.venv/bin/python -m pytest tests/test_engine_hardening.py tests/test_variable_yardage.py tests/test_save_game.py tests/test_return_audit.py tests/test_statistics.py -q --tb=short`
— 190 passed after final acceptance/decline and pending-save boundary cases.

`.venv/bin/python -m pytest tests/test_api_regulation.py tests/test_api_saves.py tests/test_issue_tracker.py -q --tb=short`
— 23 passed for transport, save compatibility and tracker freshness.

The first full coverage run hit the harness's 120-second timeout near completion;
the final run used a 600-second limit and passed in 121.36 seconds.
Additional checks: `.venv/bin/python -m pytest -q --tb=short` — 1,564 passed;
`.venv/bin/python -m pytest tests/test_turnovers.py tests/test_session_turnovers.py tests/test_penalties.py tests/test_penalty_yardage.py tests/test_session_penalties.py tests/test_regulation.py tests/test_optional_clock.py tests/test_scoring.py tests/test_overtime.py -q --tb=short` — 134 passed.

- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: 159 files already formatted.
- `npm test` in `frontend/`: 49 passed.
- `npm run build` in `frontend/`: passed before browser testing (no stale dist).
- `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS="$TMPDIR/bowl-bound-e2e-seasons" npx playwright test`
  in `frontend/`: 14 real-engine Chrome tests passed on isolated port 8123.

Implementation committed as `975ea48`; the 190-test focused command was repeated
against that commit and passed. RULE-002–009 are resolved with that tested commit
recorded, not closed: owner play-test confirmation is still required.

The separately requested [DEV-011](issues/DEV/DEV-011.md) remains open for two
original sample teams in Milestone 19, with a hard gate before GitHub linking or
publication. Filing that ticket is not implementation of the samples.

## Review and operational boundary

Self-review checked priority operand selection, suppressed unused variable rolls,
original provenance, recovery/end-zone origins, penalty decline source continuity,
statistical credit, and boundary responses that cannot duplicate committed snaps.
Broad special-team/engine decomposition was not undertaken: normal end-zone
returns now share ordinary return processing; special-team entry points retain
their existing implementation and cumulative tests. Unsupported end-zone return
penalty endpoints stay disabled with an actionable reason rather than fabricated.

Owner confirmed there are no existing saved games; no migration is needed. Profile
bumping remains a replay-safety guard, not a migration project. The running
private-team backend on port 8000 was not restarted or altered. No historical
charts, saves or private game reports were used or committed. No UI/API-001/DEV-001
work was begun. Nothing is pushed or published. Stop before Milestone 19.
