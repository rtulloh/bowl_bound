# Milestone 21 remediation commits

## Foundation checkpoint

The owner requested one committed fix at a time, High to Low, on 2026-10-27.
The difficulty implementation was still uncommitted when review found AI-003 and
AI-004. Checkpoint the prerequisite implementation separately, without either
fix, so each following ticket can have an independently reviewable commit.
This is NOT milestone acceptance: the review tickets remain open.

Paydirt consultation and implementation evidence are recorded in the in-progress
`milestone-21.md` and `difficulty-contract.md`. The prior frozen foundation gate
was 1,991 tests with 93.10% coverage. Exporting the staged checkpoint for a
separate test run was denied by the harness; no export was performed. This
checkpoint relies on that earlier foundation gate, not the 2,013-test gate which
includes the fixes. No historical data, private charts, local configuration
changes or publication are included.

The uncommitted RULE-011 tests/notes are paused until AI-003 and AI-004 commits
are complete. Full regression is required again after the ticket queue is done.

## AI-003 — Hard field-position valuation

Prerequisite checkpoint: `c4f0589`. Revisited Paydirt
`computer_ai.py:281–454` before remediation: use its situational tests as design
input, not its NFL ranges, global RNG or thresholds. No relevant expected-points
model was available there. Six synthetic regressions failed before the fix:
negative made-FG value, weak goal-line touchdown value and insufficient punt
preference, each for both sides. The legacy-value check already passed.

Hard now uses an explicitly documented bounded quadratic field preference; legacy
chart-v1 retains its utility. Focused evaluator/tier/chart-policy gate: 64 passed.
The subsequent combined AI-003/AI-004 full gate passed 2,013 tests with 93.17%
coverage, frontend 118, browser 29, lint/format/build. That combined evidence is
not claimed as an isolated AI-003 checkout gate. AI-003 remains open pending
play-test confirmation; tactical audit validity still depends on AI-009.

## AI-004 — phase-correct try analysis

AI-003 fix committed as `69771f5` before this ticket commit. Paydirt AI-022 and
`interactive_game.py:2713–2715` demonstrate stale post-touchdown context; do not
reuse that selection path. Five red-first tests showed six-point try estimates
and missing phase context. Four further red-first cases exposed str-enum identity
validation. Added the public phase and engine-owned two-point sandbox, canonical
try-start validation, cache separation, both sides/viewpoints, paired OT tries
and a no-kickoff ordinary-OT regression. Baseline hashes and legacy chart-v1
analysis serialization deliberately exclude the new phase.

Validation: combined full gate 2,013 passed, 93.17% coverage (326.51s), frontend
118, browser 29, build, Ruff lint and format. The 32-game public comparison
finished with reconciled clocks and saved futures and zero analysis fallbacks;
Hard punted 20 times versus 2. This is not evidence of greater playing strength;
AI-009 remains open. Both tickets remain open until tested-commit references and
play-test acceptance are recorded. A fresh full gate is required after all tickets.

## RULE-011 — return-fumble new series

AI-004 committed as `bd2edc4` before resuming this ticket. Revisited Paydirt
`game_engine.py:929–943`: its shared return chain starts a fresh series, while
Paydirt RULE-017 shows why an original-play recovery must retain scrimmage
context. Added 19 red-first failures covering both possessions, in-field/end-zone
returns, recovery with/without advancement, touchdown classification, exact dice
traces, session integration, fourth-down outcome labels and replay-profile bump.

Thread new-series context through return fumbles. A returner recovering its own
fumble does not consume a down. Original-offense own recoveries still use the
original line to gain, but are labeled turnover_on_downs when appropriate.
Replay profile advances to bowl-bound-m21-v1, without migrating private saves.
The profile test initially expected a specific engine-profile message; the save
loader intentionally exposes only its generic incompatible-save error. Assert
that existing public contract while retaining exact profile and no-team-lookup
assertions; no loader error behavior was changed.

RULE-011 focused command: `.venv/bin/python -m pytest
tests/test_return_fumble_series.py tests/test_turnovers.py tests/test_return_audit.py
tests/test_engine_hardening.py tests/test_session_turnovers.py tests/test_save_game.py
tests/test_statistics.py tests/test_difficulty.py tests/test_coaching_try_evaluation.py
tests/test_coaching_saves.py tests/test_issue_tracker.py -q --tb=short`: **270
passed in 18.21s**. Includes a fresh-series save/resume and next-snap assertion.
Full end-of-queue regression remains required; no next ticket started before commit.

## AI-005 — journal before derived coaching history

RULE-011 committed as `effb7d9` before starting this Medium-priority ticket.
Paydirt consultation: `ai_analysis.py:707–731` records mutable derived tendency
history, and `tests/test_ai_save.py` exercises restoration. It has no matching
command-tape transaction to borrow. Preserve Bowl Bound’s engine-command journal
as authoritative, with policy history reconstructed on replay, rather than copying
a mutable serialized tracker. This is fault-injection hardening, not a currently
reachable normal-input bug: the engine already validates the same call IDs.

Red-first tests inject failures before and after the history update for all three
tiers, require the completed snap to be journaled exactly once with consumed dice,
then restore and compare the next coached command with an uninterrupted reference.

AI-005: all six fault-injection cases failed before the ordering change. Focused
command: `.venv/bin/python -m pytest tests/test_coaching_journal_order.py
tests/test_coaching_saves.py tests/test_save_game.py tests/test_difficulty_interfaces.py
tests/test_difficulty.py -q --tb=short`: **103 passed in 17.07s**. The history error
remains visible; only the journal ordering changes. Documentation explains recovery
by save/reload and warns that the engine snap is already completed. No unrelated
behavior or test expectations changed.

## AI-006 — evaluator dispatch and errors

Prior ticket AI-005 committed as `ca4e993`. Paydirt consultation:
`paydirt/play_resolver.py:26–44` has its own Hail Mary special-table play, not
Bowl Bound authority. Bowl Bound `regulation.py:480–485` calls 8/A with Hail Mary
and hurry flags; the isolated evaluator must match that path, not reuse Paydirt’s
NFL table. Keep legacy diagnostic field turnover_rate for compatibility but
explicitly document that it measures a possession-loss proxy, not football
turnover statistics. Only declared evaluation/engine decision failures should
become failed samples; unexpected ValueErrors must remain visible.

AI-006 focused gate: `.venv/bin/python -m pytest
tests/test_coaching_evaluator_contract.py tests/test_coaching_evaluation.py
tests/test_chart_coaching.py tests/test_difficulty.py tests/test_resolution.py
tests/test_supplemental_resolution.py tests/test_coaching_try_evaluation.py
tests/test_coaching_valuation.py tests/test_coaching_contract.py
tests/test_chart_coaching_contract.py tests/test_coaching_probabilities.py
-q --tb=short`: **175 passed in 5.67s**. An initial command named nonexistent
test_supplemental.py and collected nothing; corrected to the actual suite above.
The first spy also blocked physical dice choices; narrowed it to opponent-call
populations, preserving real physical dice and testing uniform/weighted paths.

## AI-009 — measured audit evidence

AI-006 committed as `5789715` before starting this ticket. Paydirt consultation:
`tests/ai_audit.py:50–52, 121–140, 180–193, 202–246` provides hash-derived seeds,
normalized selected-call weights, redacted error output and observational
concentration/streak/small-sample summaries. Adapt these development-only ideas
using Bowl Bound public observations and seeded local RNG, not Paydirt’s global
random patching, NFL situation bands or schedule/standings dependencies.

Audit changes must preserve actual policy draws, allow stand-in kicks on fourth
down, derive replay/legality evidence from checks, reconcile observed period
score deltas against final totals and the ledger, and offer a public-sample JSON
runner. New red-first tests include deliberate replay and score mismatches.

AI-009 focused command: `.venv/bin/python -m pytest
tests/test_coaching_audit_evidence.py tests/test_coaching_audit.py
tests/test_coaching_audit_buckets.py tests/test_coaching_audit_matrix.py
-q --tb=short`: **38 passed in 38.07s**. Ruff lint/format pass (130 files).
Regenerated matrix with `.venv/bin/python -m bowl_bound.coaching_audit
--seeds 101 307`: all 32 complete, 5,123 replayed continuation commands, 5,520
committed normalized preference vectors; zero observed illegal CPU selections
or analysis fallbacks. Scores, clock debits, period totals, statistics and saved
futures reconcile. The JSON runner first failed safely on unsigned hash seeds;
a red-first seed-range test now enforces the existing 63-bit save contract.

Matrix-test expectation intentionally changes from two reused coach seeds to
32 independent hashed CPU seeds and 32 stand-in seeds, plus repeatability checks.
The observation wrapper also excludes subsequent concealed-turn preview draws.
A serializer regression preserves Counter mappings without dataclasses.asdict
reconstructing counted pairs. Full Python gate is running against frozen code;
frontend tests 118 and production build pass under Node 24.22.1.

AI-009 browser gate completed: **29 passed in 3.3m**, Node 24.22.1,
`BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<synthetic-fixture-directory> npx playwright test`
from frontend/. Issue-index validation: **17 passed**. Cumulative Python result
remains pending; no next ticket implementation started.

AI-009 cumulative gate completed: `.venv/bin/python -m pytest --cov -q
--tb=short`: **2,070 passed in 369.53s, 93.28% coverage**, no reported skips
or warnings. Frontend 118, browser 29, production build and Ruff lint/format
passed. This validates active AI-009 source, not final milestone acceptance;
AI-006 rejected-chart save replay remains a documented separate follow-up.

## AI-006 — named chart-error save follow-up

AI-009 committed as `2f32a2e` before starting this production follow-up. Revisited
Paydirt `tests/test_ai_save.py` persistence tests: it stores opponent metadata,
not a command/error replay journal, so there is no matching codec allowlist to
reuse. Bowl Bound must explicitly recognize ChartResolutionError while retaining
unknown-error rejection and exact replay matching. Synthetic rejected-chart
regression checks recorded error, restored state and next physical dice.

AI-006 follow-up focused command: `.venv/bin/python -m pytest
tests/test_chart_error_saves.py tests/test_save_game.py tests/test_coaching_saves.py
tests/test_coaching_evaluator_contract.py tests/test_coaching_evaluation.py
tests/test_resolution.py tests/test_supplemental_resolution.py -q --tb=short`:
**163 passed in 14.04s**. Red-first: 1 expected failure, 1 safety test passing
after correcting required test IDs. Only add ChartResolutionError to the codec’s
known error names; retain exact replay, no migration/profile bump. Documentation
is limited to this development evidence because player save format is unchanged.

## CLI-042 — runnable help example

AI-006 follow-up committed as `c05f4d9`. Paydirt consultation:
`paydirt/__main__.py:264–280` documents easy|medium|hard and compact display;
retain the reference command `python3 -m paydirt --play -d hard --away
1983/Bears --home 1983/Vikings --compact` as design input only. Bowl Bound
examples must use public sample teams and supported Medium difficulty.
A synthetic/public-sample regression extracts the exact argparse epilog command,
passes it through the real parser and checks the created policy.

CLI-042 red-first command failed on baseline (argparse exit 2). Changed only
epilog example to medium. Focused CLI/help/solitaire/difficulty-interface gate:
**44 passed in 4.05s**. docs/cli.md already correct; no new player-guide edit
needed. Parser rejects baseline as before.

## CLI-043 — bounded helper work and edge coverage

CLI-042 committed as `8e78aaf`. Paydirt consultation: `ai_analysis.py:425–473`
caches numeric target summaries and excludes symbolic rows; its run bias uses
NFL chart columns and different thresholds, so keep Bowl Bound exact dice,
normalized facts and current policy weights. Do not copy raw-token parsing.
Separate cheap engine-owned helper availability from numeric advice generation
so off/unavailable prompts never analyze charts; enabled prompts analyze once.
Add synthetic phase/toggle, away-chart, signed rendering, all-play physical-face,
ranking/truncation and Medium clamp/symbolic-fallback regressions.

CLI-043 corrected fixture assumptions before implementation: regulation needs a
supported season; this public kickoff automatically touches back; drive mode
continues after a punt, so finished-phase test uses an actual timed regulation
touchdown/conversion. Red-first final baseline: **6 failures, 47 passed**.
Focused command: `.venv/bin/python -m pytest tests/test_helper_edges.py
tests/test_cli_easy_helper.py tests/test_player_coaching.py tests/test_cli.py
tests/test_cli_games.py tests/test_difficulty.py tests/test_difficulty_interfaces.py
tests/test_save_game.py -q --tb=short`: **213 passed in 17.73s**. Only analysis
work scheduling changes; eligibility, saves and policy expectations unchanged.

## AI-007 — immutable versioned preference profiles

CLI-043 committed as `42e43be`. Paydirt consultation: `season_rules.py:18–54`
groups AI thresholds in behavior dataclasses. Adapt named frozen Bowl Bound
profiles, not NFL era thresholds, mutable configuration or YAML loading.
Capture pre-refactor seeded call matrix for all five persisted policies before
extracting constants; profiles must not alter hashing, seeds, samples or utility
arithmetic. Audit reports name both policy behavior and audit profile.

AI-007 focused command: `.venv/bin/python -m pytest tests/test_coaching_profiles.py
tests/test_coaching.py tests/test_chart_coaching.py tests/test_chart_coaching_contract.py
tests/test_difficulty.py tests/test_coaching_valuation.py tests/test_coaching_try_evaluation.py
tests/test_coaching_saves.py tests/test_coaching_audit_evidence.py -q --tb=short`:
**109 passed in 22.98s**. First 180s invocation timed out before a result;
600s retry completed normally. Pre-refactor call digest unchanged. Red-first
profile check failed on missing module while compatibility snapshot passed.

Independent read-only review found no concrete correctness issues: all five RNG
contracts retained; both potential formulas matched original numeric expressions
across 79,200 valid field/side combinations; frozen scalar profiles and JSON
profile names verified. Reviewer focused checks: 2 passed. Index tests: 17 passed.

## AI-008 — shared policy plumbing and explicit hooks

AI-007 committed as `1bad70b`. Paydirt consultation: `computer_ai.py:39–66`
keeps analysis/strength capabilities explicit and RNGs isolated; adapt explicit
Bowl Bound hooks, not its mutable optional model/strategy graph or NFL behavior.
Consolidate candidate/cache/mixture logic with policy hooks for public opponent
weights, evaluator utility and preference weighting/selection namespace. Declare
baseline no-op committed-history/status interfaces; remove concrete-tier dispatch.
Promote observe_game with a compatibility alias for existing tests/imports.
Document exact chart analysis as an intentional library-only foundation.

AI-008 red-first: **5 expected failures** for explicit hook/status, generalized
commit dispatch, weighted analysis API and public observation builder. Focused:
`.venv/bin/python -m pytest tests/test_coaching_shared_contract.py
tests/test_coaching_profiles.py tests/test_coaching.py tests/test_chart_coaching.py
tests/test_chart_coaching_contract.py tests/test_difficulty.py
tests/test_coaching_valuation.py tests/test_coaching_try_evaluation.py
tests/test_coaching_saves.py tests/test_coaching_session.py tests/test_coaching_edges.py
tests/test_coaching_journal_order.py tests/test_coaching_audit_evidence.py
-q --tb=short`: **132 passed in 24.40s**. Existing tests unchanged; golden
seeded calls and journal recovery assertions retained. Review requested.

AI-008 independent review found no concrete compatibility/regression issues.
Reviewer focused shared-contract/journal/difficulty/chart suite: **35 passed**
using `.venv/bin/python`; initial system python3 failed collection on unsupported
union syntax, not a code failure (DEV-027 tracks system-Python workflow).
Ruff lint/format pass (136 files).

## DEV-025 — documentation contract reconciliation

AI-008 committed as `4a5695d`. Paydirt consultation: `docs/ai-difficulty.md:5–43`
separates player difficulty, numeric helper coverage and unchanged dice odds.
Keep that explanatory separation, but replace its chart-analysis wording with
Bowl Bound’s actual 32-sample real-engine evaluator; no NFL assumptions.
Correct save profile/policy/history, explicit policy alternatives, API tables and
the owner-approved contract. Documentation-only: run existing interface/save
regressions and validate the public-sample JSON example, without artificial tests.

DEV-025 existing gate: `.venv/bin/python -m pytest tests/test_difficulty_interfaces.py
tests/test_coaching_saves.py tests/test_chart_error_saves.py
tests/test_return_fumble_series.py tests/test_save_game.py -q --tb=short`:
**104 passed in 16.10s**. TestClient verified documented public-sample JSON body,
all five explicit policies through create/save/load/get and ambiguous rejection.
The first smoke script assumed baseline serialized an explicit coach_policy key;
corrected to config.get("coach_policy", "baseline"), matching the optional schema.

## DEV-026 — commit-scope review (2026-10-28)

Paydirt consultation: local `AGENTS.md:1–70` separates engine authority, privacy
and phase workflow; adapt focused validation/commit boundaries, not NFL rules.
`c4f0589` deliberately checkpointed an incomplete foundation, including the
owner-requested solitaire/timeout changes. It is not milestone acceptance.
Retroactively splitting that checkpoint would rewrite history; not performed.
Subsequent ticket fixes are independent commits, including AI-007 `1bad70b`,
AI-008 `4a5695d`, DEV-025 `983a756`; permission request alone is `6cae885`.
Current `git status --short` shows only user-owned AGENTS.md/opencode.json
modifications. They are neither staged nor discarded, and remain outside the
acceptance commit. DEV-026 acceptance wording now reflects this non-destructive
boundary review rather than requiring unauthorized commits of user work.
OpenCode V2 configuration documentation consulted for the local config review;
no config migration or permission broadening is part of this ticket.
Documentation-only: issue-index tests and final cumulative gate apply.

## Final-source validation — source 41da5fd

Public-only 32-game runner repeated with seeds 101/307. All finished and
reconciled; 5,123 continuation commands, 5,520 committed vectors, zero observed
illegal CPU selections/fallbacks. A JSON comparison removing only behavior_profile
and audit_profile exactly matches the earlier AI-009 result. Eight games per
behavior profile; all use coaching-audit-v1. No changed gameplay expectations.
Frontend under Node 24.22.1: `npm test` **118 passed**; `npm run build` passed.
Repository-wide `.venv/bin/python -m ruff check .` passed;
`.venv/bin/python -m ruff format --check .`: **312 files already formatted**.
Python coverage and real-engine browser gates are still running.

Final browser gate FAILED: **27 passed, 2 failed in 27.2m**. Both human-away
complete games failed (automatic-turn poll and test deadline); tracked immediately
as DEV-029. Unchanged isolated retry launched. No assertions/timeouts weakened.
The all-green acceptance claim remains blocked; fresh 32-game audit is not a
substitute for a passing browser gate.

DEV-029 focused unchanged retry: `npx playwright test e2e/milestone20.spec.js
--grep "human=away"` with the same Node/Chrome/public-sample environment:
**2 passed in 51.6s**. Does not establish original failure cause. Full unchanged
browser rerun launched; no assertion/timeout/runtime changes.

Final Python coverage gate on runtime source `41da5fd`:
`.venv/bin/python -m pytest --cov -q`: **2,133 passed in 385.03s**,
**93.42% branch-aware coverage**, no reported skips/warnings. Tested fixes now
record their dedicated commit references and are resolved, not closed; owner
play-test confirmation remains outstanding. Metadata generation initially
rejected unquoted all-digit hash 5789715 as a YAML integer; quote it explicitly.

Final unchanged browser repeat: **29 passed in 3.4m**. Command (frontend cwd):
`PATH="$HOME/.nvm/versions/node/v24.22.1/bin:$PATH" BB_E2E_CHANNEL=chrome
BB_E2E_SEASONS="$TMPDIR/bowl-bound-m21-final-e2e"
npx playwright test`. Both formerly failing human-away cases passed (26.9s,
27.1s). No timeout/assertion/production changes. DEV-029 remains open with
intermittent/investigating tags; passing repeats do not establish its cause.
All final gate components now have passing results. This verification checkpoint
is not owner play-test confirmation or milestone acceptance; no next milestone
started. No push, publication, private chart/save changes or config cleanup.
