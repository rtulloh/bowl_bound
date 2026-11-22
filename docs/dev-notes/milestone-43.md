# Milestone 43 — Persistent player-season team statistics

Status: browser play-test candidate.
Ticket: [DATA-065 / #118](https://github.com/rtulloh/bowl_bound/issues/118), Medium priority.

The owner wants to watch teams' performance accumulate over a season. Deliver a
persistent played-season record with completed game history, team records,
points for/against, supported cumulative engine statistics and per-game averages.
Players can resume a campaign after restarting and compare teams as games finish.
Keep separate campaigns using the same historical year independent.

Use finalized engine scoring and statistics with stable campaign, fixture and
game identities. Keep scheduled, in-progress and completed fixtures distinct.
Store each completed engine box once and derive totals and standings from stored
boxes so a correction can recompute them. Store player data locally.

The browser season manager supports NCAA schedule templates where the chart
catalog covers the fixtures, and player-defined leagues with custom teams,
conferences and fixtures. Show overall and conference records and a league
ranking informed by record and strength of schedule. Document any missing
historical opponents and the ranking calculation before play-test publication.

## Paydirt consultation

Reviewed Paydirt's `docs/historical-seasons.md`,
`docs/saved-games-and-standings.md`, `docs/dev-notes/season-ui-design.md`,
`docs/dev-notes/season-ui-acceptance.md`, and its fixture and standings layout.
Adapt its season desk, stable fixture identities, resumable engine checkpoints
and retained final boxes. Bowl Bound uses contemporaneous NCAA conference
affiliation and Bowl Bound rules. NFL divisions, playoff seeding, tiebreakers,
and Paydirt data stay outside this milestone.

Bowl Bound's `bowl_bound/statistics.py` already provides rushing and passing
totals, touchdowns, interceptions thrown and sacks, with college sacks counted
in rushing attempts and yards. Aggregate those facts in the Python domain and
display the returned totals in the browser.

## Acceptance and validation

Follow DATA-065's complete criteria. Write synthetic tests before behavior
changes; cover multiple games/teams/campaigns, both possession roles, duplicate
completion, correction, unfinished games, persistence, overtime and exact box
reconciliation. Finish applicable API/UI/persistence regressions, documentation
and multi-game save/resume play testing before closure.


The preview is staged for GitHub Pages under `/bowl_bound/season-playtest/`. It
uses a dedicated browser database name so play-test campaigns and saves are
independent of the existing Pages game. The validated release manifest supplies
the chart catalog. See [historical schedule coverage](../season-schedules.md)
and [player controls and ranking formula](../web-game.md#play-a-season).

Targeted validation covered the browser bridge, season domain, actual
historical template creation against the staged catalog, packaging privacy,
API save and request bounds, and the season React and opening-screen tests.
The real-engine browser test played two fixtures with reversed home and away
roles, reloaded and resumed the first, then reconciled saved final scores,
games played, and cumulative offense with the two boxes. Upstream runs the
full regression on the feature branch.
