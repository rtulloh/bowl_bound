# Milestone 43 — Persistent player-season team statistics

Status: backlog, planning only, 2026-11-07.
Ticket: [DATA-065](issues/DATA/DATA-065.md), Medium priority.

The owner wants to watch teams' performance accumulate over a season. Deliver a
persistent played-season record with completed game history, team records,
points for/against, supported cumulative engine statistics and per-game averages.
Players can resume a campaign after restarting and compare teams as games finish.
Keep separate campaigns using the same historical year independent.

Use finalized engine scoring/statistics and stable game/team identities. Backend
aggregation and exactly-once completion must prevent duplicate totals after
save/load, retries, replay or UI refresh. Define correction/removal and unfinished
game behavior, and keep season storage private by default. Initial UI/CLI scope
and links to any existing season runner should be determined during implementation
planning; a complete new schedule/postseason simulator is not implied by this
request.

## Paydirt consultation

Reviewed local Paydirt docs/historical-seasons.md, especially the distinction
between development diagnostics and a played season, retained final boxes,
team records and source/runtime/chart identities. Adapt structured final-result
accounting and clear campaign identity. The document does not establish a
ready-made persistent player-season UI, so do not claim it can be copied.
Do not inherit NFL schedules, postseason/tiebreak rules, private data or a
Paydirt runtime dependency.

Reviewed Bowl Bound bowl_bound/statistics.py: TeamStatistics already provides
rushing/passing totals, touchdowns, interceptions thrown and sacks, with
college sacks counted in rushing attempts/yards. Use those engine facts;
do not recalculate football credit in the browser.

## Acceptance and validation

Follow DATA-065's complete criteria. Write synthetic tests before behavior
changes; cover multiple games/teams/campaigns, both possession roles, duplicate
completion, correction, unfinished games, persistence, overtime and exact box
reconciliation. Finish applicable API/UI/persistence regressions, documentation
and multi-game save/resume play testing before closure.

This is future feature scope, outside the active Milestone 42 / 1.0.0 correction
release. This documentation change implements no season storage or gameplay.

## Backlog-record validation

Regenerated the issue index with `.venv/bin/python scripts/build_issue_index.py`.
Ran `.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_create_issue.py tests/test_priority_docs.py tests/test_release_player_docs.py -q`: 38 passed.
`git diff --check` passed. These checks validate the ticket/documentation only;
feature acceptance remains pending implementation.
