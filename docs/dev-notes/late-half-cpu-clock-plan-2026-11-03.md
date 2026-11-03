# AI-035: late-half CPU clock investigation and review plan

This is an isolated test-first checkpoint on `fix/late-half-coaching`, based on
`6c1289c`. **Production code is unchanged.** The reported live incident was a
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

## Proposed bounded implementation (review required before production edits)

1. Add `RegulationView.normal_timing_ends_period: bool = False`, populated from
   the Boolean already calculated by `RegulationGame.view`. It describes the
   pending completed play's default charge, not the next play's outcome. The API
   already adapts the view with `asdict`; it exposes this same Boolean without
   calculating clock semantics. No UI rule or chart interpretation is added.
2. Add an explicit clock-policy method, for example
   `clock_decision(observation, *, normal_timing_ends_period: bool = False)`.
   The baseline implementation delegates to existing `decision`. The coordinator
   calls this method only at the existing `clock_choice` boundary, with the
   engine fact and existing own-side filtered legal choices. Difficulty v12 may
   specialize it; versions 1–11 delegate unchanged. This avoids adding a new
   observation field to seeded selection or analysis.
3. For v12 Easy/Medium/Hard only: when the CPU owns the offense, normal timing
   would end Q2/Q4, score is tied or trailing, and the existing shared public
   fourth-down policy selects a field goal, use its offered own timeout first.
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
  supported factory/default identities; do not silently modify v11. Existing
  saved games retain their recorded policy. An existing v11 game does not gain
  the new strategy merely by loading it. No release/package version is bumped.
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

## Checkpoint commands and results

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

Static/tracker checks pass. No full-green implementation, browser pass, full
regression, owner confirmation, push or runtime change is claimed here.
