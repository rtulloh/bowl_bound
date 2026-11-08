# Milestone 45 — Measured simulation improvements after 1.0.0

Status: scheduled and deferred; execution has not started.
Owner direction: 2026-11-07.
Tracking ticket: [DEV-080](issues/DEV/DEV-080.md).
Release target: the release after 1.0.0; choose its version during release planning.

## Goal and activation

Improve Bowl Bound simulation mechanics, coaching and supported team behavior
by reconciling the outcome-related backlog, then evaluating one ticket at a time
against a frozen baseline. Establish whether each proposed correction actually
changes results and whether the evidence supports retaining it.

Begin only after 1.0.0 is published and its required release acceptance is
complete, AND the owner explicitly says to start this goal (for example,
"start the simulation-improvement goal" or "start that" in this context).
Publication alone does not activate this goal. No background campaign, new
implementation lane or season run is started by recording this plan.

This is the next planned release effort after Milestone 42. Milestones 43 and 44
retain their existing identities and feature scope; their numbers do not override
this explicit execution priority. The owner may change that priority later.
Do not add this campaign to 1.0.0's acceptance criteria.

## Paydirt consultation and Bowl Bound boundaries

Reviewed local Paydirt docs/dev-notes/game-to-season-qualification-plan.md,
especially trustworthy measurement, complete-game accounting, actual-calendar
season runs and frozen repeated-season comparisons. Also reviewed the owner's
Paydirt proposal for backlog reconciliation and measured single-ticket changes.

Adapt exact input/runtime identities, complete fixture accounting, independent
mechanics checks, explicit unknowns and separated development/held-out evidence.
Do not reuse NFL rules, schedules, statistical conventions, postseason formats,
historical team data or a Paydirt runtime dependency.

Use Bowl Bound's selected-year college rules and statistical credit, actual
conference membership and complete available regular-season schedule, including
interconference games. Document the BCS/poll/selection model and its limitations.
Simulated postseason qualification follows simulated results; historical
postseason replay is a separately labeled comparison. Missing opponents or
fixtures must be reported, never silently removed or replaced with fictitious
games to claim a complete historical season.

## First actions after activation

1. Read the completed 1.0.0 acceptance notes and inherited limitations. Review all
   ticket statuses against actual HEAD, including purportedly resolved findings.
   Verify existing fixes before closing stale entries; preserve the required
   gameplay confirmation and evidence. Do not require a new code change for
   every investigation.
2. Create an outcome-impact inventory: ticket, current status, mechanism, affected
   situations/teams, supporting evidence, likely materiality, dependencies and
   proposed measurement. Distinguish gameplay/coaching/chart changes from
   observer/reporting changes and presentation-only work.
3. Freeze a finite ordered ticket queue and the baseline: release/runtime/source/
   chart identities, generator and coaching versions, season rules, fixture
   inventories, selection policy, commands, seed roles and acceptance metrics.
   Establish reproducible game and season baselines before judging changes.
   Reuse valid registered seed families and protect existing held-out families;
   choose run counts and meaningful-effect criteria before examining outcomes.
4. Prioritize reproduced mechanics defects, then supported coaching deficiencies,
   then material chart/source limitations. Initial screening candidates are
   [AI-032](issues/AI/AI-032.md), [AI-031](issues/AI/AI-031.md),
   [DATA-049](issues/DATA/DATA-049.md) and
   [DATA-060](issues/DATA/DATA-060.md). These are candidates, not a finding that
   every ticket requires implementation or a silent milestone reassignment.
   Existing season-runner and fixture-qualification work must be verified before
   using the runner to make historical comparison claims.

## One-ticket execution and measurement

Only one ticket may have an active implementation/change under evaluation.
Independent read-only review may accompany it. Do not combine unmeasured
mechanics, coaching and chart changes into one candidate.

For each ticket:

1. State a falsifiable mechanism and expected exposure/effect before editing.
   Record whether the ticket is still reproduced, already fixed, unsupported
   or genuinely investigative.
2. For a demonstrated behavior defect, write a synthetic regression first and
   show its meaningful failure on the unchanged implementation. Implement the
   smallest correct change. Explain changed expectations and keep engine
   authority, legal-action fairness and chart/source provenance intact.
3. Run focused controls and complete-game confirmation. Compare baseline and
   candidate under the declared fixtures, policies and multiple seeds. Same
   seeds help comparison but do not imply identical dice trajectories after a
   behavior change; retain separate deterministic replay evidence.
4. Measure immediate mechanism exposure and affected team outcomes. Use complete
   actual-season comparisons when needed to establish a claimed season effect;
   stage expensive repetitions according to the predeclared design. Zero
   observed events or wide uncertainty does not establish no possible effect.
5. Give the ticket one supported disposition: accepted correction with measured
   benefit; accepted mechanics correction with little measurable season impact;
   no defect found; already fixed and verified; rejected/regressive proposal; or
   inconclusive/deferred with an explicit reason and follow-up. An accuracy
   hypothesis may be disproved even when its underlying mechanics fix is sound.
6. Review, document and commit that ticket before starting the next. Preserve a
   measured comparison with both the immediately preceding accepted candidate
   and the original 1.0.0 baseline. Revert rejected changes without overwriting
   evidence. Update its canonical ticket, index and tested commit references.

## Metrics and historical comparisons

Report pass/rush efficiency, completion/turnover/sack rates, scoring and
possessions/plays, kicking and relevant timing/penalty behavior. Add team wins,
point differential, opponent-adjusted strengths/weaknesses and applicable
conference-title, BCS/title-game appearance and championship frequencies.
Retain complete game counts, failed runs, distribution/uncertainty estimates and
team-level regressions alongside pooled averages.

Use private 2007/2008 developer charts only where matching baselines exist;
otherwise mark that comparison not applicable and evaluate against supported
historical results. Keep authored tactics and unknown source facts explicit.
Share public-safe causal findings with Paydirt when the owner requests or has
authorized that sharing, while verifying college-specific conclusions locally.

Do not tune to named champions or force historical postseason entrants. Better
historical resemblance is supporting evidence. Acceptance requires correct
mechanics, credible team strengths/weaknesses, no unexplained material
regressions and reproducible measurements. Observer-only corrections improve
measurement confidence and must not be credited as gameplay improvements.
Preserve untouched validation data/seeds where available; do not repeatedly
retune against the same held-out results.

## Required per-ticket report

Record ticket and hypothesis; before/after commits and input identities; exact
commands, seeds and exposure counts; teams affected; mechanism and aggregate/
team metrics with uncertainty; historical/reference comparisons; regression or
missing-data findings; and the final disposition. Distinguish not run,
unverified and failed evidence from passing checks. Keep detailed historical
charts, saves and simulation/audit receipts in ignored private paths.

## Completion and release handoff

The goal is complete when every entry in the frozen queue has a supported
disposition, retained changes pass applicable full regression and gameplay
checks, and a final comparison explains both cumulative changes and remaining
limits. Prepare the next release's candidate and concise change/evidence report;
record new discoveries as tickets rather than silently expanding an endless
campaign. No predetermined improvement in any named team's championship odds
is required.

Every behavior change follows the repository's test-first workflow. Finish the
established full regression gate before any push. A passing season alone does
not replace play/state/clock/scoring/statistics reconciliation. Consult Paydirt
again at each implementation phase, record adaptations and verify them against
Bowl Bound.

## Planning-record validation

This deferred charter changes no runtime, charts or simulation behavior.
Validate the roadmap, ticket metadata and generated issue index using the
existing issue/documentation checks; behavior acceptance begins after activation.

Planning checks completed: `.venv/bin/python scripts/build_issue_index.py`;
`.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_create_issue.py tests/test_priority_docs.py tests/test_release_player_docs.py -q`
(38 passed, no skips or warnings); `git diff --check` (clean). These results
validate the deferred planning record only, not future simulation improvements.
