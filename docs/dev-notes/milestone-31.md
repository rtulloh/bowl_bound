# Milestone 31: Make legacy save tests runtime-neutral

## Paydirt and Bowl Bound references

Reviewed local Paydirt save handling before planning:

- `../paydirt/paydirt/save_game.py:41-44` stores a format version and timestamp.
- `../paydirt/paydirt/save_game.py:143-146` checks its save format version before
  loading team charts. It does not pin the Python runtime.

Do not copy Paydirt's compatibility behavior: its save format does not persist
Bowl Bound's deterministic Python random state, command journal, or chart
fingerprints. Keep Bowl Bound's documented Python major/minor compatibility
guard. Adapt only the old test fixtures' runtime metadata so their tests exercise
legacy state-digest replay under the active interpreter.

## Reproduction

Upstream workflow `41196615596` ran on commit `24194b4` with Python 3.13.17. The
pre-M27 fixture files declare Python 3.12, and `loads_game` rejects a runtime
mismatch before replay. The same focused tests pass locally on Python 3.12.8,
which matches the fixture metadata.

## Acceptance

- Both pre-M27 digest tests pass under Python 3.13 after test-only metadata
  adaptation and checksum resealing.
- Legacy commands, rolls, engine profile, and state digest remain byte-for-byte
  unchanged in the checked-in fixtures.
- A genuinely mismatched save runtime remains rejected by `loads_game`.
- Run the complete regression gate on the workflow's Python 3.13.17 runtime.

Tracked work: [DEV-050](issues/DEV/DEV-050.md).

## Validation

- Test-first reproduction on local Python 3.13.1, before the test fix:
  `/tmp/bowl-bound-py313/bin/python -m pytest tests/test_save_game.py::test_pre_m27_normal_timing_digest_remains_loadable tests/test_save_game.py::test_pre_m27_clock_choice_save_loads_without_restoring_runoff_action -q`
  failed both tests at the documented Python-major/minor compatibility check.
- Focused save tests: `/tmp/bowl-bound-py313/bin/python -m pytest tests/test_save_game.py -q`
  — 67 passed on Python 3.13.1; `.venv/bin/python -m pytest
  tests/test_save_game.py -q` — 67 passed on Python 3.12.8.
- Full Python regression on Python 3.13.1:
  `/tmp/bowl-bound-py313/bin/python -m pytest --cov --cov-report=term-missing -q`
  — 2,607 passed; 93.27% total coverage (75% required).
- `/tmp/bowl-bound-py313/bin/python -m ruff check .`,
  `/tmp/bowl-bound-py313/bin/python -m ruff format --check .`, and
  `/tmp/bowl-bound-py313/bin/python -m pip check` passed.
- Frontend on Node 24.22.1: `npm ci --ignore-scripts`, `npm test` (120 passed),
  `npm run build`, and `npm audit` (zero vulnerabilities) passed.
- Browser regression: `BB_E2E_SEASONS=/private/tmp/bowl-bound-browser-samples-20261031 npm run test:e2e`
  passed all 33 tests. The isolated fixture path uses `/private/tmp` because
  macOS `/tmp` is a symlink and the sample installer refuses symlinked paths.
- CI pins Python 3.13.17; the local full regression used Python 3.13.1. Confirm
  the exact upstream workflow passes after the tested commit is pushed.
