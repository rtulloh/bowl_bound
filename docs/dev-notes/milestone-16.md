# Milestone 16 — Historical college overtime

## Acceptance

- Home season and regular/postseason game type are frozen at creation. Regulation
  ties remain final in 1940–1994 and the 1995 regular season; 1995 postseason and
  1996+ use overtime. Unsupported seasons/types fail instead of falling back.
- A separate recorded offensive-dice toss offers offense or defense first. Normal
  series begin first-and-ten at the opponent 25. First possession alternates after
  tied rounds; there is no round cap, kickoff, or running overtime game clock.
- Conversion restrictions follow the approved historical table: no mandatory two
  through 1996, OT3+ in 1997–2020, OT2+ in 2021–2023; paired tries from OT5 in
  2019–2020 and OT3 in 2021–2023. Tries retain Bowl Bound's two-yard spot.
- Each team receives one timeout per round, with no regulation/round carryover.
  Hurry-up, spike, Hail Mary and regulation clock modifiers stay unavailable.
- Turnovers finish their live return/penalty choices before the next series. Normal
  defensive scores end the game; defensive try returns do not erase the other
  attempt. Second-series winning touchdowns omit unnecessary conversions. Finals
  reject snaps, kicks, decisions and game actions without reopening.
- Synthetic tests cover repeated rounds, both series, scoring/ledger agreement,
  successful/missed tries, field goals, defensive touchdowns and safeties, fumble
  recovery/loss, penalty replays, and successful-try penalty carry to the next series.
- The API transports engine views and accepts game type/OT timeouts. The browser
  selects game type and displays engine labels/actions without implementing rules.
  A real-engine Chrome test plays a 0–0 regulation tie into a completed overtime.

## Source and design review

The approved profile's four overtime eras remain authoritative. The public 2023
NCAA rulebook, Rule 3-1-3(d–h), printed FR-48–49, corroborates equal series and the
exception for defensive scores **other than on the try**. Both paired tries remain
necessary: two defensive returns can tie the round. The source was examined in
memory and is linked as S7 in [the rules profile](../rules-profile.md); no source PDF
or historical chart was added.

Architecture review retained composition: immutable overtime profile/round state
in `bowl_bound/overtime.py`, orchestration in `RegulationGame`, and real chart
resolution/ledger in `PlaySession`. Presentation owns no overtime decisions.
The existing successful-try board-game carry policy relocates the next overtime
series, including half-distance; labels do not promise a nonexistent kickoff.
Legacy carry decision IDs/transport fields remain compatible and are documented.
This is not wholesale adoption of NCAA post-possession penalty enforcement.

No tickets are assigned to Milestone 16. UI-010/UI-013 remain Milestone 19 work;
existing UI-013/index and OpenCode permission changes are excluded from this commit.
No saves, AI, college-statistics implementation, or Milestone 17 work was started.

## Test-first evidence and changed expectations

1. The initial 23 synthetic overtime cases failed against the unchanged engine
   because creation had no `game_type` support.
2. API and frontend game-type tests failed before their changes: extra-forbidden
   request input and missing setup control, respectively.
3. Both overtime carry tests failed first on misleading kickoff labels, then passed
   after session-owned labels/descriptions identified the next overtime series.
4. The old tied-regulation placeholder test now expects a live overtime toss choice,
   not a finished `overtime_pending` state. The accepted defensive penalty/untimed-down
   test likewise reaches overtime only after its required untimed play.
5. The complete-regulation clock audit uses 1994 to retain a genuinely final historic
   regulation tie. It still reconciles all four 900-second periods, the score ledger,
   trace/log counts, and immutable end state. Separate tests cover overtime finals.
6. The existing full-game browser loop can finish an overtime second series with
   kneels, rather than forcing two identical offenses to tie forever.

## Validation

All tests use synthetic teams; the running private-team game was not reset or
restarted. Commands are from the repository root unless a directory is noted.

- `.venv/bin/python -m pytest tests/test_overtime.py tests/test_overtime_extra.py tests/test_session_scoring.py -q`: 57 passed.
- `.venv/bin/python -m pytest --cov -q`: 1,380 passed; 91.97% branch-aware coverage (75% floor).
- `.venv/bin/python -m pytest tests/test_issue_tracker.py -q`: 17 passed.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: 118 files already formatted.
- `npm test` in `frontend/`: 41 passed.
- `npm run build` in `frontend/`: production build passed.
- `BB_E2E_CHANNEL=chrome npx playwright test` in `frontend/`: 11 real-engine Chrome tests passed.

No skips or warnings in the completed checks. No historical-team files were required.

## Limits and operational notes

- Supported major-college profile seasons remain 1940–2023; the historical table
  does not imply complete reconstruction of every intervening NCAA rule.
- Existing unsupported end-zone return/foul choices remain disabled with engine
  explanations. Advanced kick options, alternate timing and persistent hurry-up
  remain deferred under their existing milestones/tickets.
- In-memory games have no save/resume. The running backend must be restarted to
  load this implementation; no automatic restart discards an existing live game.
- Nothing is pushed or published. Stop here for milestone review/commit; do not
  begin Milestone 17 automatically.
