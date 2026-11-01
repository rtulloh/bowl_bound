# Milestone 32 — Local full-season game-log audit

## Scope

Build a reproducible, local-only 12-game-per-team season audit for imported Bowl Bound
teams. Keep seasons separate, use the production game and coaching paths, and place
detailed logs under ignored `private-data/`. The runner must not run in CI or be included
in app packages. See [DEV-007](issues/DEV/DEV-007.md).

## Paydirt consultation — 2026-10-31

Reviewed the requested local Paydirt runners:

- `tests/run_full_season.py:32-117` builds a deterministic schedule, reconciles final
  scores against scoring records, continues after independent game failures, and reports
  progress. Adapt these validation and failure-handling patterns; use Bowl Bound's own
  game state and scoring ledger.
- `tests/run_all_games.py:1-360` aggregates game scores, quarter scores and statistics.
  Its parsing of terminal output is brittle; do not copy that approach. Read structured
  engine views and traces directly.
- `tests/run_ai_audit.py:27-111` and `tests/ai_audit.py:32-100` use stable per-game seeds,
  machine-readable reports and play-selection observations. Adapt reproducible seeds and
  private call summaries; do not reuse Paydirt decision policies, NFL rules, charts or data.
- `tests/test_full_season_runner.py` exercises scheduling and game-audit failures with
  synthetic test doubles. Adapt its synthetic schedule/audit coverage; real Bowl Bound
  historical teams and logs must stay outside ordinary test collection.

No Paydirt implementation or data is copied, and Bowl Bound gains no runtime dependency.

## Acceptance evidence

- The generated schedule gives every readable team exactly 12 games against teams from
  the same chart season, with deterministic seeds and balanced home/away assignments.
- Every game reaches a legal final state; score-ledger totals reconcile; unsupported,
  incomplete, or malformed traces fail that game and preserve diagnostic evidence.
- Per-period score deltas reconcile to the final score; aggregate statistics match
  report credits; the timing log accounts for all 900 regulation seconds in each
  quarter.
- Reports include structured engine logs and coaching-call summaries, but no absolute
  paths. Historical input data and full reports remain ignored under `private-data/`.
- Synthetic tests cover schedule, reproducibility, validation and failure continuation.
- Run locally on each imported season and review the resulting private reports. Do not
  add historical chart files, PDFs, rosters, logs or output reports to Git.

## Local run evidence — 2026-11-01

Using master seed `20311031`, the runner completed all 120 scheduled games across the
seven locally installed chart seasons. The first pass had 120 games pass score-ledger,
state, and trace checks. A review found that the acceptance audit should also compare
quarter scoring, statistics, and regulation timing, so those checks and per-game evidence
were added before a final run. That expanded run exposed a runner error where a baseline
punt suggestion on fourth down was checked against scrimmage calls alone and replaced by
play 1. A synthetic test reproduced the choice and verified dispatch through the engine's
kick path; the runner now retains the legal punt and kick/action choices.

After the fix, the same seed completed **120/120 games with no failures**, with 12 games
per team and six home/six away. All reports reconciled scoring ledgers, per-period scores,
report-derived statistics, structured traces and 900 regulation seconds in each quarter.
The run recorded zero coaching fallbacks across 22,818 engine reports. These generated
results are only playtest evidence, not historical results or balance claims. Full logs
remain ignored under `private-data/local-season-audits/`.

Validation: `.venv/bin/python -m pytest -q tests/test_local_season_runner.py
tests/test_issue_tracker.py` (45 passed); Ruff lint and format checks passed for the
runner and synthetic tests. The issue-index builder completed successfully. Record the
dedicated milestone commit hash here after committing.
