# AI-035: late-half CPU clock investigation and review plan

This is an isolated test-first checkpoint on `fix/late-half-coaching`, based on
`6c1289c`. The original `7420d41` checkpoint left production unchanged; the
approved implementation and current validation are recorded below. The reported live incident was a
valid Q1-to-Q2 transition, not halftime; no kickoff was due. The following defect
is a separate fictional scenario, not a reconstruction of that private game.

## Reproduced defect

A tied Q2 game has 30 seconds displayed. A completed third-down, three-yard rush
leaves fourth-and-seven at the opponent 17: the approved shared public policy
chooses a 34-yard field goal. The prior rush still has a pending normal 30-second
charge. All three current difficulties on either side select the kick without
using an offered clock modifier. The engine correctly commits that prior charge
and ends the half **before any field-goal roll**.

The same request in Q1 works because the next play can run in Q2. At the Q2
boundary, the engine already offers a useful own timeout (10-second charge), or
hurry with no own timeouts (20-second charge). Both controls permit a real
fictional field goal. Thus the engine timing is correct; CPU command sequencing
discards its own intended scoring opportunity. A running call alone is not the
defect.

`tests/test_late_half_cpu_clock.py` has **12 meaningful red cases / 12 green
controls** in 1.38s: three tiers, both sides, zero/three own timeouts; Q1 controls;
actual timeout/hurry followed by a successful synthetic attempt; and frozen-v11
execution with an empty dice source proving no field goal was rolled. An initial
control used an abbreviated called-play label; it was corrected to the engine's
exact `Field goal attempt` label before these final counts. No assertion is
skipped or weakened.

## Reviewed bounded implementation

1. Add `RegulationView.normal_timing_ends_period: bool = False`, populated from
   the Boolean already calculated by `RegulationGame.view`. It describes the
   pending completed play's default charge, not the next play's outcome. The API
   already adapts the view with `asdict`; it exposes this same Boolean without
   calculating clock semantics. No UI rule or chart interpretation is added.
2. Add an explicit clock-policy method, for example
   `clock_decision(observation, *, normal_timing_ends_period: bool = False)`.
   The baseline implementation delegates to existing `decision`. The coordinator
   calls this method only at the existing `clock_choice` boundary, with the
   engine fact and existing own-side filtered legal choices. Difficulty v12
   specializes it; versions 1–11 delegate unchanged. This avoids adding a new
   observation field to seeded selection or analysis.
3. For v12 Easy/Medium/Hard only: when the CPU owns the offense, normal timing
   would end Q2/Q4, score is tied or trailing, and the existing shared public
   fourth-down policy selects a field goal, use its offered own timeout first.
   A timeout must leave positive time: at ten seconds or less it cannot help.
   If none is offered, use offered hurry when it preserves that attempt. If
   neither exists, leave existing behavior intact. Never use an opponent's
   timeout, force a new rule action, inspect a kicker chart, or consume dice to
   choose the clock action. Q1/Q3 and a Q4 lead do not acquire new urgency.
4. Re-plan after that legal modifier: the engine's actual charged clock now
   precedes the same public-policy field goal. Do not add a future reservation,
   change `timeout:`/`timeout_after:` semantics, alter CLI AT, or manufacture a
   timeout for natural 10-second outcomes. Mandatory continuations still settle
   before any clock-choice policy is called.

No general run/pass urgency adjustment, last-snap long-pass policy or broad
clock-utility rewrite is included. A full effective-next-call clock projection
for every ordinary analysis is deferred unless an additional focused red case
justifies it. The demonstrated boundary can use one existing engine fact.

## Version and save compatibility

- Introduce explicit normal policy v12 and register its immutable profile and
  supported factory/default identities; do not silently modify v11. Under
  canonical AI-026, ordinary Easy/Medium/Hard loads upgrade to the current named
  tier, including legacy explicit difficulty revision files. Only an explicit
  `preserve_development_policy=True` audit load retains a recorded revision.
  Existing completed commands and actual rolls replay unchanged. No release/
  package version is bumped. The original plan incorrectly promised ordinary
  loads would retain v11; review corrected that claim before implementation.
- Preserve every existing `CoachObservation` field and all baseline, difficulty,
  one-action and RZDZ analysis seed inputs. The new engine Boolean is supplied
  separately to the clock method. Re-run frozen seeded contracts for versions
  1–11, including v11 bounded RZDZ.
- Exclude only the derived, view-only Boolean from semantic view digests, using
  the existing diagnostic-field mechanism. Keep journal commands, clocks,
  budgets, gameplay rolls, integrity and chart fingerprints strictly checked.
  Verify actual frozen-source synthetic saves load/re-save and continue exactly.
- New runtime code stays in existing manifest-selected modules; add no Paydirt
  dependency or private content. Update coaching/API/save/player guidance with
  the new default and precise limited policy.

## Required focused and cumulative acceptance after review

Turn the twelve red cases green without changing their clock/scoring objectives.
Add boundary controls for 20/30 seconds, 20/30-second prior charges, no useful
modifier, one/zero remaining timeout, both ownership sides, a Q4 lead and tied/
trailing margins, public FG versus punt/go range decisions, and non-clock human
continuations. Verify no double charge, opponent-budget use or extra dice;
re-planning is pure; save/replay preserves the actual chosen method and kick.
Cover the real API/coordinator sequence and frozen historical observations.

Run focused clock/coaching/API/save tests, then applicable full regression and
coaching audit once source is stable. Local browser launch restrictions remain
explicit; collection or API execution is not a browser pass. Keep AI-035 open
until a tested fix is committed, and obtain owner play testing before closure.

## Design input

Consulted local Paydirt `paydirt/computer_ai.py:1138` and `:1193`,
`tests/test_cpu_timeout.py`, `tests/test_timeout_clock_interactions.py` and
`tests/test_half_ending_clock_trace.py`. Reuse public-state and period-boundary
control ideas only. Do not copy NFL thresholds, warning rules, random fractional
runoff, private fixtures or runtime code. Bowl Bound's timing chart, legal engine
clock offers and approved shared public fourth-down policy remain authoritative.

See [AI-035](issues/AI/AI-035.md) and the
[Milestone 33 follow-up log](milestone-33.md).

## Original 7420d41 checkpoint commands and results

```text
.venv/bin/python -m pytest tests/test_late_half_cpu_clock.py -q
# 12 failed / 12 passed in 1.38s: intentional unchanged-production red checkpoint
.venv/bin/python -m pytest tests/test_late_half_cpu_clock.py -k 'not current_cpu' -q
# 12 passed / 12 explicitly deselected in 0.72s
.venv/bin/python -m pytest tests/test_regulation.py tests/test_optional_clock.py tests/test_coaching_session.py tests/test_issue_tracker.py -q
# 74 passed in 3.05s
.venv/bin/python scripts/build_issue_index.py
.venv/bin/python -m ruff check tests/test_late_half_cpu_clock.py
.venv/bin/python -m ruff format --check tests/test_late_half_cpu_clock.py
git diff --check
```

At that original checkpoint, static/tracker checks passed. It did not claim a
full-green implementation, browser pass, full regression, owner confirmation,
push or runtime change. Subsequent implementation evidence follows.

## Implementation checkpoint (2026-11-03)

The owner/parent approved the bounded implementation. The engine supplies its
already-calculated expiration Boolean. The clock-specific method preserves
existing observation structures and all frozen seed inputs. Shared
`timing.TIMEOUT_SECONDS` retains the existing value of ten; regulation imports
that constant and the new preference uses it to reject useless timeouts. No
clock rule or legal offer is changed.

Expanded test-first controls failed 97 / passed 13 on unchanged production,
including absent facts/method and the intentionally new v12 default. After
implementation, a further three meaningful red controls exposed useless timeout
choices with zero/five/ten seconds remaining; the positive-time guard fixes
them. Final focused tests pass **119 in 5.26s**, including the original scoring
objectives, engine fact thresholds, zero/one/three own budgets, both sides,
Q2/Q4 margins, opponent/unsupported/off-scope guards, frozen v1–11 seeded
contracts, ordinary-load upgrade, explicit audit preservation, strict save
continuation and actual API automatic clock-then-kick sequencing.

Six fictional save/view pairs generated by the actual unchanged 7420d41 source
were retained only under ignored private-data. All **12** normal/frozen loads
preserve every pre-existing view fact and physical roll while applying the
intended current-versus-frozen policy distinction. No owner save was accessed.
Fresh cumulative/full validation remains pending at this checkpoint.

Focused/cumulative checkpoint: **365 passed in 44.77s** across difficulty/
profiles/coordinator, strict saves, API, RZDZ, timing and new clock controls.
Fresh pinned frontend: **131 in 4.99s**, production build 739ms, npm audit zero
vulnerabilities. npm ci reports the existing whatwg-encoding deprecation;
Vitest reports its jsdom performance recommendation. Ruff check/format 566 files,
pip and diff checks pass. No new skips are hidden. Full regression remains
pending, and this does not constitute owner play-test confirmation.


--- 2026-11-03 — final-source regression ---
Implementation aa578d7 and merged driver checkpoint 007056b passed the fresh
complete Python gate: **3,630 passed in 923.40s, 93.20% branch-aware coverage**,
exit zero. The earlier interrupted run is not acceptance evidence. Focused
merged clock/halftime/API/save/tracker checks pass **145 in 8.75s**. Final Ruff
check/format covers 569 files; pip check, zero-vulnerability npm audit, production
build, frontend 131, 1,267 local Markdown links and diff checks pass. Existing
npm deprecation and Vitest advisory remain documented above.

All 48 browser cases in eight files collect. Fresh real-engine halftime browser
execution fails at Chromium launch before assertions with macOS MachPort1100:
one failed and seven not run under fail-fast, plus its cleanup error. This is
an execution limitation, not a browser pass; no sandbox bypass, skip or assertion
weakening was used. The temporary test server exited; owner servers and games
were untouched. Complete-game coaching/replay and private local-season audits
follow separately. Owner play-test confirmation is still required for closure.


--- 2026-11-03 — completed audit / tested resolution ---
Tested runtime **aa578d7**, merged regression checkpoint **007056b**. The public
32-game matrix (seeds 101/307; baseline-v2 and Easy/Medium/Hard-v12; both sample
orientations and CPU sides) passes mechanics and strict saved-future replay:
5,449 reports, 11,748 trace consultations, 5,347 replayed steps, each regulation
quarter reconciles to 900 seconds, and no illegal choices. All nine ordinary
calls and all six defenses occur for every policy; 672 comparable choices have
117 repeats, maximum within-bucket streak four, and zero concentration warnings.
Current tiers select 15 own timeouts. These are audit observations, not quotas
or calibration claims.

Three initial-try analysis fallbacks (one Easy, two Medium) remain explicitly
reported under AI-034. Isolated uniform-opponent reanalysis reproduces only the
known `hypothetical try did not settle` limitation; it does not reconstruct
historical opponent weights. All 135 forced RZDZ choices have zero fallbacks.
No unresolved samples are zero-filled or hidden.

The separate private local-season baseline mechanics audit passes **120/120**,
zero errors/fallbacks, 22,192 reports and six overtime games. It reads local
private bundles without modifying them; all detailed artifacts remain ignored.
This is baseline mechanics evidence, not current-v12 coaching calibration.

AI-035 is resolved pending owner play testing. The original reported Q1-to-Q2
transition remains valid, unrelated to the synthetic defect. Browser execution
is still blocked as recorded above; no full browser gate or fresh milestone
acceptance is claimed. No push, main merge, release, tag or owner-game mutation.


Final commands (run from the isolated worktree with the supported shared
`/Users/rtulloh/work/bowl_bound/.venv/bin/python` interpreter):

```text
python -m pytest --cov --cov-report=term-missing -q
# 3,630 passed / 923.40s / 93.20%, exit 0, at 007056b
python -m bowl_bound.coaching_audit --seeds 101 307 --policies baseline-v2 easy-v12 medium-v12 hard-v12
# 32 reconciled games with saved-future replay, exit 0
python scripts/run_local_season.py --seasons /Users/rtulloh/work/bowl_bound/seasons --games-per-team 12 --seed 20311031 --output private-data/late-half-validation/private-season-007056b
# 120 passed / 0 failed / 0 fallback, exit 0; detailed output private
npx playwright test e2e/halftime.spec.js --max-failures=1
# Chromium launch denied (1100) before assertions: 1 failed / 7 not run
```

The commands labeled `python` above identify the supported interpreter, never
system Python 3.9. Complete audit JSON/logs and original-source fictional golden
saves stay below ignored `private-data/late-half-validation/`. No extra full
run was repeated after the final source passed; the acceptance follow-up is
metadata/documentation only.
