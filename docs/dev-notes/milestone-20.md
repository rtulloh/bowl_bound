# Milestone 20 — Baseline computer opponent

## Scope and decisions

Implement the canonical baseline opponent and UI-011. The owner approved automatic
computer turns, pausing whenever a human call or decision is required. Support a
human on either side and retain two-sided manual play. Do not restart port 8000
automatically, change historical teams or begin chart-aware Milestone 21.

## Paydirt source audit

Inspected paydirt/computer_ai.py at bfaf8410cb586149f06f98bf98ecca572cae360d
(MIT, rtulloh). Adapt its balanced/situational call mixtures, legal fallback idea,
and separation of coaching randomness from gameplay dice. Do not copy its engine
class, NFL play names, field-goal +17 arithmetic, route restrictions, era settings,
chart analyzers or global random state. No Paydirt runtime dependency.

## Implementation plan

1. Test a pure baseline selector receiving only immutable public observations and
   engine-offered legal action IDs. Use deterministic coaching randomness derived
   from public observations, never the gameplay seed, dice source or hidden call.
   Audit fallback choices and call variety, not just game completion.
2. Give engine decisions explicit home/away ownership (names can be identical).
   Add a coordinator that asks for exactly one human call when needed, plans the
   computer call without seeing it, and executes one engine command per request
   under the existing game lock. Reject invalid/disabled input without rolling.
3. Provide optional human-home/human-away controls and bounded automatic computer
   requests. Pause for human calls/choices, errors, final games and save/load.
   Do not reveal a computer call before the human submits their simultaneous call.
4. Supply explicit dice role/color/face/total metadata from observed engine rolls,
   including both white dice, tosses, supplemental and recovery rolls. Present
   text labels as well as colors; never consume/reconstruct rolls for display.
5. Keep m19 saves compatible: additive presentation metadata must not alter their
   semantic view digest. Control mode is a browser preference, reset on load.
   Test old-format digests and identical future engine/coaching continuation.
6. Validate synthetic/public-sample unit, API and browser games with either human
   side, clock/OT/conversion/turnover choices, fallback audits, save continuation
   and full regression gates. Update docs/attribution and UI-011 with tested
   commit evidence; stop for review and the milestone commit.

### Grilling Notes

**Assumptions verified:** 6/6: roadmap scope, UI-011 requirements, Paydirt source and
license, simultaneous play interface, current save digest contract, and chooser
name ambiguity were checked in their owning modules.
**Open Questions:** 1 -> 0 (automatic turns approved by owner).
**Status:** READY. Remaining policy weights are baseline preferences constrained
by engine legality, not new football rules; synthetic audits can refine them.
**Key revision:** do not import Paydirt’s coupled ComputerAI class or use gameplay
seeds; isolate the selector and preserve current saves despite added dice labels.

Rollback is the dedicated milestone commit; the live m19 server stays running.

## Implementation and review

- Added independent `BaselineCoach` and immutable public `CoachObservation`,
  including an explicit public overtime flag. No charts, history contents, human
  simultaneous selection, gameplay seed, RNG or future rolls enter the selector.
- Added engine-owned decision-side metadata for tosses, halves, clock, conversions,
  kicks, ordinary/return penalties, interceptions and end-zone recoveries.
- Added private simultaneous-call planning and atomic saved-game/API coaching
  commands. Only human controls are serialized before resolution. Invalid human
  input leaves dice and command journals unchanged. Manual endpoints remain.
- Added both human sides, manual mode, serialized automatic requests, pause/resume,
  error/final stops, a 12-consecutive-action safety pause and save/load exclusion.
  Loaded games reset to manual; both sides’ unsubmitted selections remain private.
- UI-011: observed rolls now carry die role/color/label/face and authoritative total
  metadata. Both white dice are distinct. Compact results, toss and chart audits
  use only recorded rolls; all 216 offensive and 36 defensive combinations are tested.
- Old m19 digests and documents lacking coaching metadata remain loadable. The
  browser now downloads opaque save text, avoiding large-integer rounding (DEV-013).
  No historical charts, dependencies, publication settings or live process changed.

### Reviewed refinements and changed expectations

The initial public-observation-only stream would make calls predictable to someone
who knows the policy. A separate private 63-bit coaching seed now salts those
streams, is persisted in private saves, and is excluded from previews. It never
uses gameplay RNG/seed. Old m19 documents acquire this seed once when loaded; new
exports preserve future coaching. There is still no mutable coaching PRNG state.

Exact trace assertions were extended with the new additive dice metadata while
retaining every previous face, total, chart cell and consulted-roll assertion.
The exact observation-field assertion gained only the public overtime flag:
a forced regression showed an untimed clock could otherwise activate late
regulation kneeling. Overtime no longer activates those clock preferences.
API coaching fixtures fix the independent coaching seed so their ordinary-play
assertions do not randomly exercise a pending interception instead. The ordinary
interception and ownership tests remain separate and strict.

Save-client tests now expect opaque text rather than a parsed object. Both the
client and Blob tests first demonstrated exact precision corruption; preserving
the text fixes browser integrity checks without relaxing the save codec. The
first Chrome gate passed all four computer games and 17 existing checks, but its
save/refresh/load check failed, exposing that bug. No skip or weakened assertion
was used. The final rerun passed all 22 Chrome checks, including save/refresh/load.

### Acceptance gates

Final worktree validation (2026-10-26):

- Focused coaching/API/compatibility/edge-case/issue checks: **68 passed**.
- Full Python gate: **1,653 passed**, **92.82% branch-aware coverage** (75% minimum).
- Ruff lint and format checks: passed (183 Python files formatted).
- Frontend: **69 tests passed**; production build passed.
- Isolated real-engine Chrome gate: **22 passed**, including four full coached
  games and the exact-text save/refresh/load regression.
- No skips or warnings were reported by these final gates. Implementation commit:
  **`9ab530f`**. The 68 focused coaching/API/compatibility/edge/issue checks were
  repeated against that committed implementation and passed. UI-011 and DEV-013
  are resolved against it; closure still awaits owner play-testing.
- Milestone acceptance self-review found no remaining blocker. The CLI requested
  by the owner is separately scheduled as 20a; no CLI implementation is included.

- Pure policy audits cover every offensive/defensive call in comparable public
  situations, relative passing preference, deterministic calls, enabled legal
  fallbacks and explicit empty-set failure.
- Six complete public-sample engine games (three gameplay seeds, either human side)
  reconcile scoring, quarter timing and identical coached save continuation.
- Forced synthetic cases cover identical team names, interceptions, defensive
  scores/conversions, penalties, end-zone recovery/touchback without invented
  rolls, overtime toss/mandatory-two/paired tries, and untimed clock strategy.
- Browser acceptance covers both public-team arrangements and either human side,
  private controls/requests, automatic actions, exact dice facts, all displayed
  statistics, scoring and 900 seconds per regulation quarter.
- Applicable cumulative commands: `.venv/bin/python -m pytest --cov -q --tb=short`,
  `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`; in `frontend/`,
  `npm test`, `npm run build`, and
  `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<isolated-public-fixture-dir> npx playwright test`.
- Chart-aware strategy remains Milestone 21. UI-011/DEV-013 closure awaits owner
  play-testing after tested commits; no next milestone has started.
