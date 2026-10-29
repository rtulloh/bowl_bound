# Milestone 13: basic special teams

## Acceptance review

- Engine-owned kickoff, punt, field-goal, return, fair-catch, and end-zone decisions
  are available through `PlaySession`, the API, and browser controls. No football
  calculations or chart interpretation were added to the API or frontend.
- Home-season policies cover kickoff boundaries and free-kick touchbacks; synthetic
  tests cover both possession orientations and mixed seasons.
- Punt markers suppress returns, including redirected FG/KO distance lookups.
  Reception decisions do not reroll the kick.
- Field goals compare chart yardage to LOS-to-goal, accept `NG`, award three points,
  and give missed kicks to the opponent at its own 20 or the advantageous hold spot.
  The functional wrapper requires the opponent chart for blocked-kick returns.
- Kick/return fouls cover full-feature S/R assessment, accept/decline, separate
  multiple-foul choices, offsetting fouls, pre-snap cancellation, midpoint and
  half-distance enforcement, and kickoff-out-of-bounds alternatives.
- Fumbles, blocked kicks, recovery-return chains, end-zone depth, touchbacks,
  touchdowns, and safeties use engine procedures and complete structured traces.
  Retained scrimmage-kick chains preserve the original fourth-down line to gain.
- Pending choices leave field state, score, and committed log untouched. Session
  and API tests reject competing actions, invalid choices, and duplicate decisions.
- A real-engine browser regression punts, waits for the receiving decision, then
  commits a fair catch once. The score and action controls remain engine-owned.

## Test-first evidence and corrected expectations

The initial farther-out missed-field-goal regression failed because the partial
resolver always awarded the own 20. Session tests initially failed on missing
`actions.special`/`kick`; API tests failed with 404 before adding the kick route.
Additional failing regressions exposed returnable marked end-zone punts, failure
to re-kick after accepted kickoff fouls, wrong series handling after retained free
kicks, free-kick touchback spots leaking into recovery returns, fourth-down state
lost in a return-fumble chain, and unnecessary variable rolls on offsetting fouls.

The initial close-in miss expectation (`yards_to_goal=92`) was wrong: from the
opponent one, the receiving team prefers its own 20 (`80`) over its own eight
(`92`). From the opponent 30, the hold gives the receiver its opponent 37 (`63`).
Both cases now have explicit independent expectations (Basic VI-6). A draft
defensive-foul/return-touchdown test was corrected to select **decline**, not
**accept**: Basic VI-4(A) offers the play result or penalty yardage. Its six-point
assertion was retained; no assertions were weakened and no skips were added.

## Validation

Run from the repository root unless a working directory is indicated:

```bash
.venv/bin/python -m pytest tests/test_special_teams.py tests/test_session_special_teams.py tests/test_api.py -q
.venv/bin/python -m pytest --cov -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

From `frontend/`:

```bash
npx vitest run
npx vite build
BB_E2E_CHANNEL=chrome npx playwright test
```

Final validation: **106 focused tests**, **1,175 cumulative Python tests**,
**90.95% branch-enabled coverage**, Ruff lint/format checks, **28 frontend tests**,
production build, and **5 real-engine browser tests** all passed. There were no
skips or warnings. The installed Chrome channel is used because the bundled
Playwright Chromium is not installed.

Local private-chart smoke validation separately loaded the verified 2002 teams,
ran kickoff/punt/field-goal procedures for both kicking sides with seeds 0–499,
and selected legal pending choices until each procedure completed: **3,000 cases,
zero failures**. Only aggregate counts were printed; no historical chart cells,
provenance, rosters, or reports are included in this change or required by CI.

## Scope boundary

Scoring still ends this possession demo. Automatic post-score/safety free-kick
scheduling, conversions, clocks, and complete-game reconciliation belong to
Milestones 14–17. The safety free-kick procedure itself is tested. Onside kicks,
advanced kicking/block decisions, and advanced kickoff fair catches are not
exposed. No next milestone is included, and nothing is pushed or published.
