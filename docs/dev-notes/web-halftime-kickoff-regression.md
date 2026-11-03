# Web halftime kickoff regression — 2026-11-03

The owner requested frontend tests proving that a second-half kickoff occurs.
Read-only inspection of the current owner game found Q1-to-Q2 continuation, so
the reported absence of a kickoff there is correct. No Q2-to-Q3 kickoff defect
has been reproduced. A distinct halftime recap remains planned in
[UI-058](issues/UI/UI-058.md) and [Milestone 35](milestone-35.md).

## Paydirt consultation

Reviewed local Paydirt `tests/test_halftime_ownership.py:64-95` and
`paydirt-web/frontend/src/test/halftimeFromEngine.test.jsx`. Adapt the explicit
halftime-versus-other-quarter controls, kickoff ownership checks and engine-owned
presentation facts. Do not copy NFL timing/kickoff rules, client-generated
football state, private teams or a new pause/Continue interaction. Outstanding
tries/penalties and recap ordering remain part of M35 acceptance.

## Added checks

`frontend/e2e/halftime.spec.js` adds six focused real-engine browser cases:
both opening receive/kick choices across manual, human-home and human-away
control. They verify Q2-to-Q3 kickoff scheduling, reciprocal kicking/receiving
sides, timeout reset, human kickoff controls or automatic computer execution,
one recorded kickoff/return with both structured traces in expanded Play history,
and save/resume without a duplicate kickoff. Two Q1-to-Q2 controls verify ongoing
possession and ordinary scrimmage continuation without a kickoff.

`tests/period_fixtures.py` builds synthetic, replayable saves through normal
engine commands against the browser harness's invented Guidance teams. It does
not patch saved state/checksums, mock API responses or advance an owner game.
`tests/test_web_halftime.py` independently exercises those same saves through
the real API, including computer-owned kickoff and post-kickoff save replay.

The fixture leaves a completed zero-yard run's normal timing pending at 0:10.
Selecting the next call commits that timing. Halftime schedules a kickoff before
another scrimmage roll; a Q1 break permits the selected Q2 scrimmage play. The
last history row's pending-clock explanation correctly clears once timing commits,
so only that presentation field changes in the existing halftime history rows.
Initial test expectations that required byte-identical timing labels, or that
incorrectly blocked the next Q2 snap at a Q1 boundary, were corrected to these
documented existing engine contracts; no production behavior was changed.

## Verification

This is a tests/documentation change, not an implementation of halftime recap or
new coaching behavior. No new release or runtime play-test server is needed.

- `PYTHONPATH=. .venv/bin/python -m pytest tests/test_web_halftime.py tests/test_regulation.py tests/test_save_game.py -q --no-cov`:
  **120 passed**, including all eight new API fixture cases.
- `PYTHONPATH=. .venv/bin/python -m pytest tests/test_issue_tracker.py -q --no-cov`:
  **18 passed**; regenerated the issue index with `scripts/build_issue_index.py`.
- Frontend `npm test`: **131 passed**; `npm run build`: passed, using Node 24.22.1.
- Focused Ruff lint/format checks passed for both added Python files.
- `npm run test:e2e -- halftime.spec.js --list`: eight browser cases collected.
- Real browser execution was attempted against the synthetic backend using
  `BB_E2E_SEASONS=/private/tmp/bb-halftime-e2e.BkSTYK npm run test:e2e -- halftime.spec.js`.
  The backend started, but **all eight cases failed before test execution** because
  Chromium's macOS Mach port bootstrap was denied (`Permission denied (1100)`).
  Browser assertions are unverified here; they are neither skipped nor reported
  as passing. The initial `/tmp` path also hit the sample installer's symlink-parent
  guard because macOS `/tmp` points at `/private/tmp`; passing the resolved path
  allowed the backend to start without changing production safeguards.

The browser-enabled regression gate must run these cases before publication.
This local tests-only checkpoint is not a full regression or M35 acceptance claim.
