# Milestone 34 — two-phase college chart generator

Status: in progress; owner requested independent parallel work with Milestone 33
on 2026-11-02. Engine baseline: `03d1992d3a3811cf89879bce985e23937e3a3dc0`.
No fit from this branch applies automatically after engine/coaching changes.

## Paydirt consultation

Reviewed `/Users/rtulloh/work/paydirt/docs/chart-generator.md`,
`docs/chart-generation-workflow.md`, `docs/dev-notes/statistical-chart-generator.md`,
`docs/dev-notes/chart-generator-tuning-tool.md`,
`docs/dev-notes/generated-chart-completeness-audit.md`, `generate_charts.py`,
`generate_nflverse_charts.py`, `tune_charts.py`,
`paydirt/chart_generator.py`, `paydirt/chart_tuning.py` and
`paydirt/nflverse_play_by_play.py` before implementation.

Adapt: immutable source baseline, explicit calibrated profiles, empirical weighted
quantiles, regularized opponent effects, paired candidate seeds, separate unused
validation seeds, joint outcome metrics and failure retention. Reuse Bowl Bound's
own codec, normalization, physical dice, engine, save replay and audit contracts.
Do not reuse NFL family classifiers, 10–39 probabilities, the 18-yard run cap,
NFL sack accounting, tactical cell layouts, coefficients or historical matrices.
Also reviewed the synthetic source/generator/tuning and runner tests in
`tests/test_chart_generator.py`, `test_chart_tuning.py`,
`test_chart_tuning_runner.py`, `test_nflverse_play_by_play.py` and
`test_generate_nflverse_charts.py`, including denominator, paired-seed,
source-precedence and opponent-adjustment cases.
There is no Paydirt runtime dependency. Reference studies and learned bounds stay
in ignored `private-data/chart-generator/`.

## Phase A acceptance

- Source identity/hash/scope and game completeness are explicit.
- Source-neutral evidence preserves penalties, turnovers, sacks, scoring yardage
  and special teams; uncertain play families remain inferred or unknown.
- All 810 cells and 30 PAT results load through the production codec.
- Determinism, weighted probabilities and safe private output have synthetic tests.

## Phase B acceptance

- Separate real-engine simulation/refinement command, bounded profiles, immutable
  candidates, paired training seeds and held-out validation.
- Joint completion/interception/sack/efficiency/fumble/special-team assessments;
  scoring/volume/clock/call diagnostics and uncertainty remain visible.
- Multi-seed completed-game reconciliation and save replay, both possessions;
  retain failures and best candidates. Distinguish mechanics study from a matched
  historical schedule fit. Repeated two-team games cannot establish historical fit.
- Synthetic tests, full regression and documented private play-test commands.

## Source selection

The public SportsDataverse ESPN-derived Parquet releases contain 2007 and 2008.
The initial file audit finds all 13 Ohio State and 14 LSU scheduled games, including
LSU's conference championship and the January title game under season 2007.
Event-level completeness and official aggregate reconciliation remain under audit.
NCAA-derived bulk data begins in 2013 and cannot supply this pilot.

Primary references checked 2026-11-02:
[ESPN loader](https://cfbfastr.sportsdataverse.org/reference/load_espn_cfb_pbp.html),
[NCAA loader](https://cfbfastr.sportsdataverse.org/reference/load_ncaa_mfb_pbp.html),
[CFBD terms](https://collegefootballdata.com/terms),
[Ohio State 2007 archive](https://ohiostatebuckeyes.com/sports/2018/7/2/2007-football-season),
[LSU statistics archive](https://lsusports.net/fbstats).
Raw snapshots and audits remain private; software licenses do not establish
redistribution rights for all underlying sports content.

## Verification log

- Created isolated Python 3.12 environment; confirmed imports resolve inside this
  worktree, independently of the parallel Milestone 33 engine changes.
- Wrote source, complete-bundle, profile/seed, provenance, CLI and engine tests
  before implementation; missing-module collection failures demonstrated the new
  contracts. Source PAT precedence and accepted no-play penalty tests failed on
  the first implementation, then passed after the corrections.
- `python -m pytest tests/chartgen tests/test_issue_tracker.py -q`: 45 passed
  before later full replay/strength regressions were added.
- Four private pilot smoke games reconciled through the production local-season
  audit; their initial PAT source defect is tracked in DATA-003. Retained those
  artifacts and regenerated a versioned input rather than overwriting evidence.
- Every pilot source has no populated depth/direction observations; generic family
  estimates are explicitly pooled. Official aggregate mismatches remain DATA-002.
- Initial prototype docs: [generator guide](../chart-generator.md).
- Added optional midpoint restoration and final journal replay to the existing
  local-season development runner. The default runner behavior and runtime engine
  are unchanged. This avoids the legacy coaching audit's invalid assumption that
  every rendered trace cell must be nonempty (DATA-004); normalized blank cells
  remain blank. The structural local-season trace validator remains authoritative.
- The complete two-phase synthetic test checks immutable baseline retention,
  disjoint held-out seeds, real complete games, restored continuation, final replay
  and a separate `chart-v10` coaching-policy assessment. Insufficient statistical
  exposure remains a failed fit gate even when mechanics pass.
- Full regression, bounded private refinement and acceptance review pending.
