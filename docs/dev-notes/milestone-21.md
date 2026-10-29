# Milestone 21 — Chart-aware coaching and audits

## Handoff and scope

Owner authorized committing the 20a documentation handoff and proceeding on
2026-10-27. Handoff commit: `1e9e6cf`; runtime checkpoints: `f121c92`,
`ec50e1a`. Track work under AI-001. DEV-020 and CLI-037 remain explicitly open;
named commentary is deferred to 21a/CLI-036. No historical data, dependency
remediation, advanced rules or server restarts are in scope.

## Implementation plan

1. Establish a bounded exact probability analyzer using the existing
   `resolution.resolve_play`, not a second priority chart. Enumerate the physical
   dice with multiplicity (216 offense, 36 defense). Aggregate only equivalent
   dice requests; supplemental/Option/variable rolls remain independent. Return
   rational outcome probabilities, explicit pending result mass and explicit
   unexplored mass when a work bound is reached. Never call pending or unexplored
   results zero-yard plays or committed turnovers. Test this layer first.
2. Evaluate public matchup distributions against current down/distance/spot and
   a documented coaching utility. Before integrating policy, distinguish chart
   resolution from complete football outcomes: penalties, interceptions and
   fumbles still need engine-owned procedures. Use isolated engine evaluation
   where full outcomes are required; do not duplicate those procedures. Benchmark
   repeated/variable charts before choosing cache sizes and evaluation budgets.
3. Add opt-in chart-aware coaching while retaining baseline behavior and old-save
   continuation. Version policy/config explicitly and keep coaching seeds private
   and separate from gameplay randomness. Preserve simultaneous call privacy;
   observations must never receive the human selection or live dice source.
4. Audit probability-aware policy against baseline with independent evaluation
   seeds, both team arrangements and both human sides. Report call frequencies,
   repeated calls in comparable situations, legal fallback counts, result/state/
   clock/statistics reconciliation and save/load parity, not only scores.
5. Document supported scope, analysis limits, launch/config options and private
   audit output. Run focused/cumulative gates, review, and stop for the dedicated
   `milestone 21: add chart-aware coaching and audits` commit.

## Design review

Verified in `dice.py`: physical face multiplicities are non-uniform. Verified in
`resolution.py`: Option, B/QR/QT and variable distances already use injected
dice; fumbles, interceptions and penalties intentionally remain pending here.
Verified in `coaching.py`/`coaching_session.py`: current observations exclude
charts, human selections and gameplay RNG. Verified in `save_game.py`: saves
strictly validate configuration and replay explicit commands; baseline is
currently hard-coded. A new policy must not silently change legacy continuation.

### Grilling Notes

**Assumptions verified:** 4/4 architectural assumptions above.
**Open Questions:** 2 -> 2 implementation gates: exact-tree cost on branch-heavy
charts, and end-to-end outcome evaluation cost. Both are answerable by synthetic
benchmarks; no owner rules decision is required to test the analyzer.
**Status:** READY for probability-layer tests and implementation; policy integration
remains gated on the measured cost and correct treatment of pending procedures.
**Key revision:** a resolved chart distribution is not a complete-game outcome
distribution. Preserve unresolved probability instead of pretending every F is
a lost fumble, every INT is an accepted return or every penalty is zero yards.

## Rollback and privacy

The original opt-in proposal is superseded by the approved difficulty contract:
new CLI/API/browser games default Medium, while legacy saved policies remain
unchanged. Baseline remains available through explicit engine/API configuration
for regression and comparison; do not relabel it as a new difficulty.
Probability analysis is pure and receives chart facts only, never a live engine
or source. Cache only bounded matchup data, not sessions or seeds. Detailed
probabilities derived from historical charts are private; public evidence uses
synthetic fixtures or the two original samples. No release packaging changes.

## Status

Implemented in the uncommitted worktree: exact probability foundation, isolated
engine analysis, Easy/Medium/Hard selection and Easy CLI assistance. See the latest
evidence below and the [public comparison report](coaching-audit-m21.md). Owner
review and the dedicated milestone commit remain pending; no publication implied.


## Probability foundation — initial implementation

Added `bowl_bound/coaching_probabilities.py`: replay the pure engine resolver
against hypothetical roll prefixes, expand each new independent dice request
with exact physical weights, and combine matching structured outcomes using
Fractions. Group only offensive total/direct_sum and defensive total; this
optimization is specific to resolve_play and must not be reused for hurried
bad-snap procedures that inspect individual faces. The API accepts no game,
live dice source, human selection or seed.

Retain called/resolved play, operation/source, yards, bounds, penalty facts and
end-zone depth. Penalty/turnover pending mass remains explicit. Engine-rejected
branches retain failed mass without including chart/error text; budget-limited
work retains unexplored mass. Neither is renormalized into a successful result.
`complete` means the resolver tree finished, not completed football procedures.
Default bound: 10,000 prefix evaluations per play/formation.

### Test-first and benchmark evidence

Created self-contained synthetic tests before the module existed: the initial
run failed collection with ModuleNotFoundError for the new module (not an
existing-production regression). Implemented the module, then all 18 initial
cases passed. Added three further independent-reroll/branch-limit/type cases;
all **21** pass. No old tests or expectations changed. Coverage includes all
216 offensive by 36 defensive physical combinations against resolve_play, exact
non-uniform weights, priority, both Option redirects, B/QR/QT, negative DS,
pending F/INT/penalties, bounds, exact unexplored mass, errors, deterministic
repeated analysis and no process-global RNG consumption.

Public-only benchmark: both sample-team arrangements, all nine plays and six
formations: **108/108 complete** distributions, **47,928** resolver evaluations
in **0.882 seconds**. All 108 contain some pending mass. This demonstrates why
a chart distribution cannot yet be called a turnover/score probability model.
Branch-heavy synthetic cyclic supplemental charts remain bounded and explicitly
incomplete. No historical charts were used in these tests or benchmarks.

Focused gate: `.venv/bin/python -m pytest tests/test_coaching_probabilities.py
tests/test_coaching.py tests/test_coaching_contract.py tests/test_coaching_edges.py
tests/test_coaching_saves.py tests/test_resolution.py tests/test_issue_tracker.py
-q --tb=short`: **119 passed in 7.54 seconds**. Ruff lint/format pass (**233
files**). A fresh full Python coverage gate is running against frozen source.

### Remaining milestone work

This is a tested probability foundation, NOT completed Milestone 21. Policy
utility, pending-procedure evaluation, opt-in/save-compatible integration and
independent-seed full-game comparison/call-repetition audits remain pending.
No existing coaching, engine result, save codec, API, CLI or web behavior changed.
No frontend gate is needed for this isolated unreferenced Python module; existing
coaching/save regressions are included above. No milestone-21 commit or publication.


### Cumulative probability-foundation verification — 2026-10-27

The frozen-source `.venv/bin/python -m pytest --cov -q --tb=short` completed:
**1,872 passed in 224.75 seconds**, **93.04% branch-aware coverage** overall;
new probability module **98%**. No skips or warnings reported. This supersedes
the running-gate note above. No production changes followed this run.

The probability foundation remains uncommitted; Milestone 21 is still in
progress, not accepted. Opt-in policy integration, pending-procedure evaluation,
save compatibility and independent-seed comparative audits are still required.

## Owner follow-up — solitaire and difficulty contract, 2026-10-27

The CLI is solitaire-only (CLI-040): remove manual mode, paired-call commands and
TO/TD. T remains the human timeout regardless of offensive/defensive role, and
the computer retains its own legal timeout window (CLI-038/CLI-039).

AI-002 supersedes the initial baseline/chart player-facing difficulty proposal:
Easy 0.3, Medium 0.5 (new-game default), Hard 0.7 in CLI and browser setup.
CLI-041 specifies the Easy-only, default-on Z-toggle helper with numeric-only
dice-weighted estimates and explicit coverage limits. The canonical approved
target is [difficulty-contract.md](difficulty-contract.md). These tiers/helper
are not yet implemented; do not describe chart-v1 alone as satisfying Hard.

The probability-foundation gate above predates evaluator/policy/save/API/CLI
changes and is not evidence for the current worktree. Full-game audit tests are
in test-first draft with their implementation pending. Milestone 21 remains
uncommitted and incomplete; no publication, server restart or next-milestone work.

## Paydirt consultation — difficulty/helper phase

Reviewed local Paydirt read-only before the new difficulty implementation:
`paydirt/computer_ai.py:create_computer_ai` (1310–1334) establishes the
0.3/0.5/0.7 mode split and medium group strength versus hard analysis.
`ComputerAI._choose_early_down` (625–636) tilts category probability while
preserving within-category mixes; `_first_down_offense` (676–696) provides
situational input. Do not reuse its NFL play names, fourth-down historical
percentages, yard lines or inherited rules.

Reviewed `paydirt/ai_analysis.py:OpponentTendencyTracker` (687–852) and
`OpponentModel` (855–929) for committed-history, recent-window and save concepts.
Bowl Bound currently models smoothed per-team legal-call frequencies rather than
copying Paydirt's mutable prediction path. Preview must remain pure and history
is reconstructed from successful snap commands during save replay.

Reviewed `OffenseAnalyzer.get_target_stats` (424–453) and `EasyModeHelper`
(943–999) for exact numeric-only coverage and target ranking. This caught an
initial draft mismatch: priority-annotated/out-of-bounds numeric cells are not
plain numeric evidence. Added three failing synthetic cases, then excluded these
semantic annotations without parsing provenance or PDF colors. Unlike Paydirt's
zero-valued no-coverage record, Bowl Bound retains absent conditional values to
avoid implying a known zero-yard outcome. No private team data was read or copied.

Owner requested making this consultation mandatory for every phase/milestone;
`AGENTS.md` now requires consultation, recorded references/adaptations and explicit
limitations if no relevant Paydirt material is available.

### Difficulty/helper foundation status

Added pure rational numeric estimator (27 initially failing cases, then passing;
three annotation regressions added subsequently). Added separate versioned
Easy/Medium/Hard policies (11 expected initial failures), explicit aggression,
coarse early-down run/pass adjustment, weighted isolated engine evaluation for
Hard, 6-call recent variety, smoothed opponent frequencies, bounded 128-model
cache and replay-reconstructed public history. Extended evaluator mixtures with
six initially failing validation/reproducibility cases and a real-engine weighted
opponent sampling test. Baseline-v1 and draft chart-v1 remain separate.

Focused foundation/coaching/save regressions before the annotation correction:
129 passed in 9.52s. CLI/browser difficulty selection, Easy display/Z toggle and
full-game audits are still pending, so this is NOT milestone acceptance. No commit
or publication; the previous full gate predates all of this work.

## Complete-game audits and public difficulty integration

Consulted Paydirt tests/ai_audit.py:audit_game (82–194) before implementing
the audit phase: adapt independent gameplay/coaching streams, committed-call
counts and semantic reconciliation. Do not reuse monkeypatched NFL engine rules,
global RNG seeding or private historical chart assumptions. Bowl Bound drives the
real solitaire coordinator and a fixed public-only baseline stand-in.

Added coaching_audit.py: reconciles final scoring/statistics, every clock debit
and each 900-second quarter, supported/settled reports, nonempty structured chart
traces, and identical commands/calls/outcomes/state throughout the saved future
after step 40. It fails rather than reporting a completed audit on a mismatch.
Comparable repetition buckets preserve role/side/down/quarter/hurry/OT/legal menus
and group distance (<=3/6/10/long), field (<=20/50/80/deep), clock
(<=60/120/180/ordinary), and tied/one-score/multiple-score lead/deficit. Added a
failing minor-clock/field regression then implemented buckets; material-context
separation has eight tests. All five policies pass the complete-game audit tests.

Public sample comparison compare_policies((101, 307)) completed 24 games across
Easy/Medium/Hard, both sample arrangements and CPU sides (8 per tier). Each had
165–183 reports, 11–33 comparable calls, 0–8 repeated calls, zero fallbacks,
900 seconds reconciled per quarter and verified saved continuation. This is a
correctness/variety check, not a win-rate experiment or proof that Hard is stronger.
Counts include specials and decisions separately from offensive/defensive calls.

Added CLI/API/browser difficulty integration red-first: eight Python interface
failures and three browser selector failures before implementation. CLI exposes
only Easy/Medium/Hard, defaults Medium, and refuses any explicit -d on --load.
API defaults Medium at the new-game boundary; legacy explicit policies remain
accepted but conflict with difficulty. New/load/get report the persisted policy.
Existing SavedGame.new default and legacy saved future streams remain unchanged.
Old CLI unimplemented-Hard expectations are intentionally replaced by real-Hard
invocation and rejection of legacy player-facing tier names; old chart saves
still load as chart-v1. Browser expected payloads intentionally gain difficulty.

Easy helper integration: five expected red terminal tests, then default-on numeric
rankings, separate situation/clock tips, situational-only defense advice and Z.
Preference is terminal-local and resets on successful load; never part of gameplay
saves. The preservation test excludes only regenerated export timestamp/integrity,
not any game state, seed, journal, dice or digest. Defensive prose may use the word
coverage; the exclusion assertion checks numeric coverage statistics.
No browser helper, Medium/Hard helper, manual CLI, or private data changes added.

Latest focused CLI/interface regression: 65 passed in 7.92s. Frontend initially
117 passed/1 failed because a preexisting postseason payload expectation omitted
new Medium difficulty; corrected while retaining exact game_type validation.
Cumulative Python gate is running; final regression/acceptance still pending.

## Review checkpoint — completed integration, awaiting owner review

Expanded the comparison red-first to include baseline by default: the matrix
contract initially reported 24 instead of 32 games, and the report lacked team
arrangement/score metadata. Added these without changing game policy behavior.
The complete 32-game results and distribution review are in
[coaching-audit-m21.md](coaching-audit-m21.md). In particular, Hard's rare punting
and formation-B preference are explicitly visible for tactical owner review.

Validation before the last audit-metadata-only change passed 1,990 Python tests,
93.06% branch-aware coverage, and all 29 real-engine browser tests. The last
focused audit/helper run passed 23 tests in 20.22 seconds. On the final source:
Ruff lint passes; formatting passes for all 123 Python files; frontend 118 tests
pass and the production build succeeds under Node 24.22.1. All 29 browser tests
pass again in 3.3 minutes against that build. Final cumulative Python rerun is
in progress; append its result before accepting this checkpoint.

Earlier interrupted gates are NOT passes: the 360-second Python run stopped at
72%, a focused run hit 120 seconds, and the first browser attempt timed out after
partial results. The timed-out browser left its own synthetic server process;
only that known test-owned process was stopped before rerunning. No existing
owner gameplay server was restarted. All checks were subsequently retried.

Three initial difficulty-browser failures were a test serialization error:
re-encoding parsed saves through JavaScript Numbers rounded private 63-bit coach
seeds and correctly failed integrity validation. The fixture now uploads the
original JSON text, like the application; no production save check was weakened.
The focused browser test then passed all three difficulties.

New helper tests compare every saved gameplay fact, excluding only regenerated
saved_at/integrity export metadata. Added an initially failing expanded-help Z
control check, then included the Easy-only toggle in the legal help menu.
The postponed helper setting is terminal-local and resets after successful load.

Exact cumulative commands (repository root unless noted):

~~~sh
.venv/bin/python -m pytest --cov -q --tb=short
.venv/bin/python -m ruff check bowl_bound backend tests
.venv/bin/python -m ruff format --check bowl_bound backend tests
.venv/bin/python scripts/build_issue_index.py
~~~

Frontend commands (frontend working directory):

~~~sh
PATH="$HOME/.nvm/versions/node/v24.22.1/bin:$PATH" npm test
PATH="$HOME/.nvm/versions/node/v24.22.1/bin:$PATH" npm run build
PATH="$HOME/.nvm/versions/node/v24.22.1/bin:$PATH" BB_E2E_CHANNEL=chrome BB_E2E_SEASONS="$TMPDIR/bowl-bound-m21-difficulty-seasons" npx playwright test
~~~

The system python3 resolves to Python 3.9 here, so its issue-index command failed
on unsupported union annotations; rerunning with the supported project venv
succeeded. No interpreter/dependency remediation was mixed into this milestone.

Owner requested allowing npm test while work was running. The existing project
OpenCode config already permitted npm test; added only the missing exact Node
24.22.1 absolute-PATH invocation rule. JSON validates; preserve this local config
change separately rather than mixing it into the milestone commit.

No commit/push/publication yet. AI-001, AI-002 and CLI-041 remain open pending
tested commit references and owner play-test; DEV-016, DEV-020, CLI-036/21a and
CLI-037 remain separate. Stop here for milestone review, not the next milestone.

## Final frozen-source Python gate

After the defensive-helper wording correction, reran the complete suite against
unchanged production source: `.venv/bin/python -m pytest --cov -q --tb=short`
passed **1,991 tests in 300.86 seconds, 93.10% branch-aware coverage**. No skips
or warnings were reported. This supersedes the earlier concurrent run (1,991
passed, 93.04%) and the prior 1,990-test checkpoint. Focused helper/estimator
regression passed 36 tests; Ruff lint and formatting also pass. Frontend remains
118 unit tests, successful production build and 29 real-engine browser tests.

Implementation and automated validation are ready for owner review. The
32-game public comparison and Hard tactical limitations remain as documented.
No milestone commit, push, publication or next-milestone work was performed.

## Full review before acceptance — 2026-10-27

Owner requested a full review of every milestone since the last one (18a, 19,
20, 20a, 21) with a Paydirt consultation. Record: [full-review-2026-10-27.md](full-review-2026-10-27.md).
Forty tickets were opened. Two block this milestone's acceptance as High:
[AI-003](issues/AI/AI-003.md) (Hard utility never punts; root cause of the audit
observation previously recorded as a limitation) and [AI-004](issues/AI/AI-004.md)
(tries evaluated as scrimmage). Also required before the milestone commit:
AI-005, AI-006, AI-009, CLI-042, CLI-043, DEV-025 and the commit split in DEV-026.
The Milestone 21 acceptance claim above is withdrawn until these are resolved and
the 32-game comparison is regenerated.

## AI-003 remediation kickoff

Review tickets committed separately as `6d678d4` (17 tracker tests passed).
Before fixing valuation, revisited Paydirt `computer_ai.py:281–454`: its explicit
fourth-down score/time/position guards are useful tactical test inputs, but its
NFL kick ranges, global RNG calls and thresholds are not reused. Paydirt has no
expected-points model to borrow. Bowl Bound will use a documented bounded
field-position preference, not claim calibrated EPA or copy NFL scoring tables.
Keep the draft legacy chart-v1 evaluator unchanged; apply the correction only to
new Hard analysis. Added synthetic made-FG, goal-line scoring and obvious-punt
regressions for both sides before changing implementation.

## AI-004 remediation kickoff

Paydirt cross-check (AI-022 there, `interactive_game.py:2713–2715`) reproduced
a try selected on stale post-touchdown state, even selecting QB_KNEEL. Do not
reuse that path. Bowl Bound will add the explicit public phase to observations
and construct isolated try sessions using the existing two-point engine phase;
no duplicate conversion rules or scoring. Preserve legacy observation digests
and legacy analysis streams explicitly. Red-first tests use real RegulationGame
normal-OT conversions and paired try-only rounds, both possessions, offensive
and defensive viewpoints, plus cache separation from identical scrimmage spots.

## AI-003/AI-004 implementation checkpoint

Regenerated the 32-game comparison after both High coaching fixes: all finished,
all saved continuations matched, all four 900-second quarters reconciled, no
analysis fallbacks. Hard punted 20 times instead of 2. Updated the public report;
AI-009 still limits its tactical validity because the stand-in cannot punt/kick.
Phase now keys the uncommitted new-tier streams; Easy/Medium paths change too.
Baseline results and legacy analysis serialization remain unchanged.

Broader focused run initially found a stale legacy-hash test: it built the old
input from asdict excluding hurried but not the newly added phase. Corrected the
test to assert the exact original input-field allowlist and also assert phase
changes never affect baseline-v1 calls. No baseline behavior changed.

Added four red-first factory validation cases: raw strings/None/bool must not be
accepted as SessionPhase (a str Enum compares equal but fails identity checks).
Factory now requires the enum, refuses noncanonical try starts, and a separate
ordinary-overtime regression forbids hypothetical kickoffs.

## RULE-011 correctness dependency

Owner authorized working tickets High-to-Low. Move RULE-011 from 22 to 21 because
its incorrect return-fumble series affects engine rollouts used for coaching
evaluation. Do not start advanced-option work or silently reopen 18a acceptance.
Revisited Paydirt `game_engine.py:929–943`: its shared return chain starts a new
series, but the cross-check RULE-017 there shows that this must not reset an
original scrimmage recovery. Bowl Bound will explicitly distinguish those cases,
preserve actual roll traces, and bump its replay profile rather than reinterpret
old saves under the changed down rules. No private save migration is attempted.

## Per-ticket commit workflow — owner update

Owner explicitly requires each ticket fix to be committed before starting the next,
with focused regressions as needed and a full gate after the queue is complete.
Foundation checkpoint `c4f0589` is explicitly incomplete, not milestone acceptance.
AI-003: `69771f5`; AI-004: `bd2edc4`. Exact commands and per-ticket evidence are in
[m21-remediation-commits.md](m21-remediation-commits.md). RULE-011 has 270 focused
passing regressions (18.21s), including corrected return series, fourth-down
labels and replay-profile/save continuation checks. No private save migration.

## AI-009 audit correction — 2026-10-28

The earlier stand-in limitation notes are superseded by this remediation: the
stand-in can punt/kick, per-call normalized preferences are measured, save
verification counts compared future commands, and illegal selections are counted
and rejected. Added concentration/streak/small-sample evidence, independent period
score reconciliation, hash-derived per-game seeds and a redacted public-only JSON
runner. [Updated comparison](coaching-audit-m21.md): all 32 games reconcile with
5,123 compared continuation commands and 5,520 committed preference vectors.
This is descriptive audit evidence, not proof of stronger Hard coaching or
milestone acceptance. Other review tickets remain open.

## Remediation verification checkpoint — 2026-10-28

The requested High-to-Low remediation queue is independently committed through
`41da5fd`; details and consultation references are in
[m21-remediation-commits.md](m21-remediation-commits.md). Eleven tested fixes
now have commit references and resolved status, not play-test closure.
DEV-026 records the non-destructive commit-boundary review; the original
checkpoint was not rewritten and user-owned process/config edits remain local.

Final runtime source: **2,133 Python tests passed in 385.03s**, **93.42%
branch-aware coverage**; **118 frontend tests**, production build and repository
Ruff lint/format pass (Node 24.22.1; 312 Python files formatted). Fresh public
32-game audit exactly preserves previous game evidence, with only profile names
added: 5,123 replay commands, 5,520 vectors, zero observed illegal CPU selections
or fallbacks. These figures do not claim Hard is optimal or stronger.

The initial final browser gate failed 2/29 human-away complete games. Both passed
an unchanged focused retry in 51.6s, then the full unchanged suite passed
**29/29 in 3.4 minutes**. No assertions, deadlines or runtime code changed.
DEV-029 remains open because the original failure cause is not established.
All final gate components have passing results; the original failed run remains
visible. Owner review/play-test, the DEV-026 boundary limitation and disposition
of intermittent DEV-029 remain before milestone acceptance; do not begin 21a.

## Owner-approved validation follow-up deferral — 2026-10-28

Owner approved deferring intermittent DEV-029 to later cleanup after the unchanged
focused and full browser reruns passed. Reassigned to Milestone 23; remains open
and not fixed, with original failure evidence preserved. DEV-029 no longer gates
Milestone 21 acceptance. Separately, AGENTS.md consultation guidance was committed
with owner approval as `a2571ff`; local opencode.json edits remain untouched.
The owner requested next-milestone ticket planning, recorded in
[milestone-21a.md](milestone-21a.md). This is not an assertion of completed M21
owner play-test/acceptance or authorization to start M21a runtime implementation.
