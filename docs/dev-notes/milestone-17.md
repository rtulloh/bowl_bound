# Milestone 17 — College offensive statistics

## Acceptance

- Each committed offensive snap carries immutable, engine-owned statistical credit.
  Team views fold those credits into rushing attempts/net yards/TDs, pass attempts/
  completions/net yards/TDs/interceptions, sacks taken/loss yards and total offense.
  Polling and pending choices cannot increment a counter or consume dice.
- User-approved explicit marker policy: QR is rushing, QT losses are rushing sacks,
  ordinary numeric passing results are completions even at negative yardage, and
  Option uses its resolved play. Bad snaps, kneels and spikes receive team credit.
- Goal-line clipping uses actual gain, not raw chart overshoot. Variable fumble
  locations are retained without rerolling; original-team fumble advances retain
  their category only until the first opposing recovery. Later reacquisition/
  defensive return yardage and touchdowns cannot inflate offensive totals.
- Accepted previous-spot/replayed downs are excluded. End-of-gain enforcement
  retains underlying credit but excludes foul yardage. Own-fumble return fouls
  retain legal advance to the existing engine enforcement base, including its
  midpoint restriction; the statistics module does not duplicate that rule.
- Conversions, kicks/returns and unsupported results are excluded. Full-series
  overtime counts; paired two-point tries and PATs do not. The scoring ledger
  still reconciles all points, including scores absent from offensive totals.
- Two synthetic complete-game audits reconcile both teams independently: a
  144-snap, zero-yard historical tie and a nonzero scoring game with clipped
  passing touchdowns and PAT exclusions. Both reconcile four 900-second periods.
  Focused cases cover sacks, turnovers, penalties, pending decisions and overtime.
- The API transports credits/totals without adding rules. The browser renders the
  collapsible Team statistics table from engine-supplied labels and values.
  A real-engine Chrome regression checks displayed totals across two committed
  snaps, a pending interception and its final incompletion choice.

## Source and design review

The [college statistics policy](../statistics.md) records the 2026-10-26 user
classification decision and the reviewed public 2022 NCAA statisticians’ manual.
It explicitly distinguishes supported offensive team summaries from a complete
NCAA box score and from reconstruction of historical statistical-reporting changes.
No player identity, contact, foul location or sack is invented from chart prose.

Immutable credits on PlayReport make exclusions auditable and survive period/OT
transitions without counters that polling or decisions could increment twice.
SessionView exposes totals plus engine-formatted rows; regulation composes that
view and the API uses its existing dataclass serializer. No extra API rule logic,
frontend arithmetic or runtime dependency was added.

No tickets are assigned to Milestone 17. UI-013 (persistent hurry-up) and UI-014
(opening coin-toss/human handoff) remain Milestone 19 work. Their ticket/index
changes and the existing OpenCode configuration changes are excluded from this
milestone commit. UI-012/RULE-001 remain resolved pending human play-test confirmation.

## Test-first evidence and changed expectations

1. Corrected an initial fixture enum spelling before meaningful collection. The
   initial 28 synthetic regressions then failed against unchanged production code
   on missing statistics fields; all pass with engine credits/totals.
2. The hurried passing bad-snap regression failed with an invented completion
   before an explicit semantic bad-snap fact preserved its team-rush classification.
3. Frontend tests failed on the absent statistics component before implementation;
   API coverage verifies the existing serializer exposes the new immutable facts.
4. Review strengthened accepted own-fumble-return penalty expectations: the early
   implementation incorrectly discarded the entire advance. Two expanded cases
   failed first, then passed using the existing enforcement policy’s zero-foul
   base, not reimplemented midpoint arithmetic. Declined expectations stay intact.
5. A double-turnover touchdown regression failed first because a later return
   touchdown was being credited as rushing. Credit now stops at first opposing
   possession, including for touchdown attribution, without changing the score.
6. Corrected synthetic dice to actually authorize a defensive fumble return; the
   test now requires observed return evidence. The full-game zero-gain expected
   count is 144 (two 30-second runs plus two 20-second passes per four-down drive),
   not the initial 120 estimate. The nonzero audit also preserves a 77-yard
   second-down situation across quarter boundaries rather than assuming a reset.
7. A QT-to-penalty reroll regression failed first with a stale sack classification.
   Branch selection now stops at the final penalty-reroll boundary, retaining the
   earlier trace but not crediting a discarded branch.
8. No pre-existing test expectations were weakened, and no skips were added.

## Validation

Commands are from the repository root unless noted. All fixtures are synthetic;
the live private-team backend was not restarted and its in-memory game was not discarded.

- `.venv/bin/python -m pytest --cov -q`: 1,426 passed; 92.53% branch-aware coverage (75% floor); statistics module 100%.
- `.venv/bin/python -m pytest tests/test_statistics.py tests/test_api_statistics.py -q`: 46 passed.
- `.venv/bin/python -m pytest tests/test_issue_tracker.py -q`: 17 passed.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: 125 files already formatted.
- `npm test` in `frontend/`: 44 passed.
- `npm run build` in `frontend/`: production build passed.
- `BB_E2E_CHANNEL=chrome npx playwright test` in `frontend/`: 12 real-engine Chrome tests passed.

No skips or warnings in the completed checks. No historical-team files were required.
## Limits and operational notes

- Supported totals and exclusions are documented in [statistics.md](../statistics.md);
  player, kicking/return, first-down, possession-time and drive/red-zone summaries
  are not claimed. No save/resume or AI work is included.
- Existing unsupported gameplay options stay unavailable; statistics do not invent
  results for them. The public NCAA PDF was reviewed in memory, not added to git.
- The running backend predates this implementation. It needs a user-coordinated
  restart to load overtime/statistics, which would discard unsaved in-memory games.
  No automatic restart was performed.
- Nothing is pushed or published. Stop after Milestone 17 review and commit; do
  not begin Milestone 18 automatically.
