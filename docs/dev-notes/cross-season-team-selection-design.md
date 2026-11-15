# Cross-season team selection — web UI design

Status: design proposal, 2026-11-15.
Tickets: [UI-071](issues/UI/UI-071.md) (this design), [UI-070](issues/UI/UI-070.md)
(cross-year matchup behavior and home-season rules), [UI-009](issues/UI/UI-009.md)
(season-qualified in-game identities).
Milestone: [44](milestone-44.md).

A static, self-contained preview of the proposed screen is at
[mockups/cross-season-setup.html](mockups/cross-season-setup.html); open it in a
browser and use the **Default / Open team picker** toggle. It is a design
artifact only and is not connected to the engine.

This document designs the setup experience for choosing a home and away team from
different installed seasons. It does not implement behavior, add seasons, or
change engine rules. The engine and API already accept independent
season-qualified team IDs and derive rules from the designated home team's
season; see UI-070's verification comment.

## Current behavior and limitations

The setup screen in `frontend/src/App.jsx` renders two native `<select>` elements
(`home-select`, `away-select`) populated from `GET /api/teams`. Each option is
`{name} ({season})` and the value is the canonical `season/team-slug` ID. The
catalog response is:

```json
{
  "teams": [{"id": "2007/cedar-valley", "name": "Cedar Valley", "season": 2007}],
  "problems": [{"id": "2007/broken-team", "reason": "could not be read"}]
}
```

Observed limitations:

- **No independent year control.** Both lists contain every team in every season,
  so a large catalog becomes one long, unsorted-by-year dropdown. There is no
  per-side year filter or grouping.
- **No search.** Finding one school among many seasons requires scrolling the
  entire catalog twice.
- **Cross-year intent is implicit.** Nothing in the setup screen says that the
  two teams may come from different years or that the home team's season governs
  rules. The only hint is the year in each option label.
- **No rules visibility.** The governing home-season rules are not shown before
  start, and unsupported home seasons are not distinguished from supported ones.
- **Catalog problems are dropped.** `listTeams()` returns `problems`, but the UI
  ignores them, so an unreadable team simply disappears without explanation.
- **No swap or recent/favorite affordances.** Changing home/away means re-picking
  both sides, and repeated matchups require repeating the full selection.
- **Defaults are hardcoded.** The sample Cedar Valley/Harbor Tech IDs are chosen
  when present; otherwise the first two catalog entries are used, which may be
  the same school in different years or an arbitrary pair.

The engine/API side is not the gap: `POST /api/games` loads `home` and `away`
independently, and `SavedGame.new` freezes `rules_season` from the home chart.
The work is selection clarity, scaling, rules visibility and end-to-end
verification.

## Design goals

1. **Same-year play stays one obvious path.** A player who does not care about
   cross-season matchups should not have to understand a new concept.
2. **Independent years are explicit.** Each side owns its year and team; changing
   one side never clears or constrains the other.
3. **The home season's authority is visible before kickoff.** Show which season's
   rules govern and why, sourced from the backend, not inferred in the browser.
4. **Identity is season-qualified everywhere.** `2007 Cedar Valley` and
   `2012 Cedar Valley` are distinct, selectable, and distinguishable in-game.
5. **The catalog scales.** Grouping, filtering and search must remain usable with
   many seasons and hundreds of teams, on desktop and mobile.
6. **The design leaves room to grow.** More seasons, richer team metadata,
   favorites, neutral-site games and tournament setup should fit without
   replacing the setup flow.

## Information architecture

The setup screen becomes a single **matchup builder** with three regions:

```text
┌──────────────────────────────────────────────────────────────┐
│  Bowl Bound                                                  │
│  Build a matchup                                             │
├──────────────────────────────────────────────────────────────┤
│  [ Home card ]            ⇄ swap            [ Away card ]    │
│   Year: 2007  ▾                              Year: 2012 ▾    │
│   Team: [ Search teams…            ▾ ]       Team: [ …    ]  │
│   2007 Cedar Valley                          2012 Harbor Tech│
├──────────────────────────────────────────────────────────────┤
│  Rules: 2007 home season governs this game   [details ▾]     │
│  Regular season ▾   Difficulty ▾   Control mode ▾            │
│  [ Start game ]                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Home card** and **Away card** are visually parallel and independently
  editable. Each contains a year selector and a team picker.
- **Swap** exchanges the two complete selections (year + team) and updates the
  rules banner. It never mutates either team's identity.
- **Rules banner** states the governing home season and expands to a
  backend-provided summary. It is informational, not a rules editor.
- **Game options** (game type, difficulty, control mode) remain below the
  matchup, unchanged in meaning.

### Same-year fast path

On first load, choose a default season (the newest installed season, or the
sample season when the public samples are present) and set both cards to that
season. The away team defaults to a different team in the same season when one
exists. A player can start a same-year game without touching the year controls.

A compact **"Use same season for both teams"** toggle is shown only when the two
years differ. Enabling it sets the away year to the home year and keeps the away
team if that team exists in the home season; otherwise it clears the away team
and focuses the away picker. This is a convenience, not a mode: the underlying
state is always two independent `(season, team)` selections.

### Independent year selection

Each card has its own year control. Changing the home year:

- updates only the home team list and the rules banner;
- leaves the away year and team untouched;
- clears the home team only if the current home team does not exist in the new
  year, and then focuses the home picker with an inline explanation.

Changing the away year behaves the same way for the away side. This directly
avoids Paydirt's shared-season behavior, where changing the season clears both
selections.

Year controls list only **installed** seasons, newest first, with a count of
readable teams. Seasons with no readable teams are shown disabled with a reason
rather than silently omitted. The control must not imply that every historical
year is available.

### Team picker

Use a searchable combobox per side rather than a native select once the catalog
is large:

- The closed control shows the season-qualified identity, e.g.
  `2007 Cedar Valley`.
- Opening it shows teams for that card's year, sorted by name, with a search
  field that filters by team name and slug.
- Typing filters within the selected year by default. A visible hint offers
  **"Search all seasons"**; choosing a result from another season updates that
  card's year and team together. This keeps the common case narrow while making
  cross-year discovery possible from either side.
- Each result shows the team name and year; the same school in two years appears
  as two distinct results.
- Keyboard support: arrow keys move the active option, Enter selects, Escape
  closes, and focus returns to the trigger. The combobox exposes
  `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`
  and an accessible name (`Home team`, `Away team`).
- A native `<select>` fallback remains acceptable for small catalogs and is the
  baseline for tests; the combobox is a progressive enhancement, not a
  requirement for correctness.

The picker must allow the same school on both sides, including the same school
in different years. Duplicate rejection is by canonical ID only, never by
display name.

### Rules visibility

Before start, the rules banner reads, for example:

> **2007 home-season rules govern this game.** Kickoff placement, touchbacks,
> timing and overtime follow 2007. Both teams keep their own charts and rosters.

The summary comes from the backend, keyed by the selected home season and game
type. The browser displays the returned text and supported/unsupported status;
it does not map years to rules. A proposed contract (final shape to be settled in
UI-070 implementation):

```json
{
  "season": 2007,
  "supported": true,
  "summary": "2007 home-season rules govern this game.",
  "details": ["Kickoffs from the 30", "Touchback to the 20", "..."],
  "game_type": "regular"
}
```

If the home season is unsupported, the banner becomes an error state, the start
button is disabled, and the message names the season and the supported range.
The away season never selects rules. Changing home/away or either year refreshes
the banner; a stale response must not overwrite a newer selection.

### Errors and catalog problems

- `GET /api/teams` `problems` are surfaced in a collapsible **Unavailable teams**
  note, grouped by season, with the safe reason already returned by the API.
  They are not silently dropped.
- A missing or unreadable selected team produces an inline error on that card
  and keeps the rest of the selection intact.
- A failed game creation shows the backend's actionable message and leaves the
  matchup builder populated so the player can correct it.
- No fallback to a current-year, newer-team or NFL rules profile is offered.

## State and identity contract

Setup state is two independent selections plus game options:

```text
home = { season: number, teamId: "2007/cedar-valley" }
away = { season: number, teamId: "2012/harbor-tech" }
gameType, difficulty, control
```

- `teamId` remains the canonical `season/team-slug` string used by the API and
  saves. The year control is a filter over the catalog, not a second source of
  truth; `teamId` always determines the season.
- Display labels are derived as `"{season} {name}"` for setup and in-game
  surfaces, coordinated with UI-009. The browser must not parse labels to
  recover identity or rules.
- The start payload remains `{home, away, mode, game_type, difficulty}`. No new
  engine field is required for cross-season play.
- Save/load continues to restore both team IDs and the frozen home-season rules;
  the setup screen is not shown for a loaded game and cannot retroactively change
  its rules.

## Scaling and future expansion

- **Grouping:** year controls are the primary grouping; the team picker is scoped
  to one year. An "all seasons" search result list groups by year with sticky
  year headers.
- **Search:** client-side filtering is sufficient for the current catalog. If the
  catalog grows into thousands of teams, move filtering to a query parameter on
  `/api/teams` without changing the selection contract.
- **Virtualization:** render long result lists with a windowing component only
  when measured list sizes justify it; do not add it preemptively.
- **Favorites and recents:** store season-qualified IDs in local storage and show
  them above the year-scoped list. This is a later enhancement and must not
  become a second identity source.
- **Richer metadata:** conference, division, rating and logo fields can be added
  to catalog entries and displayed in results without changing the picker's
  contract.
- **Future modes:** neutral-site games, tournaments and multi-game seasons can
  reuse the same two-card matchup builder and add options below it. A neutral
  site must still designate which team's season governs rules explicitly.

## Accessibility and responsive behavior

- Every control has a visible label; year and team controls are associated with
  their card via `aria-labelledby`.
- The rules banner uses a live region so a year change announces the new
  governing season without moving focus.
- Selection is never conveyed by color alone; selected cards and results use
  text and `aria-selected`/`aria-pressed` as appropriate.
- On narrow screens the cards stack vertically with the swap control between
  them; the combobox opens as a full-width listbox and remains keyboard operable.
- Touch targets meet the existing button sizing conventions; the picker does not
  rely on hover.

## Phased implementation

Each phase is independently testable and should be committed separately under
Milestone 44. Behavior changes follow the project's test-first rule.

1. **Extract and split selection state.** Move setup into a `MatchupBuilder`
   component with independent home/away year and team state, same-year defaults,
   swap, and season-qualified labels. Keep native selects initially. Tests:
   changing one year does not clear the other side; same school in two years is
   selectable; swap preserves both IDs; start payload is unchanged.
2. **Add the searchable team picker.** Year-scoped combobox with search, all-season
   search, keyboard and screen-reader behavior, and a native-select fallback.
   Tests: filtering, cross-year result selection, duplicate-name handling,
   keyboard navigation and mobile layout.
3. **Surface rules and catalog problems.** Add the backend rules-summary contract
   and banner, unsupported-season error state, and the unavailable-teams note.
   Tests: supported/unsupported home seasons, away season never governs, stale
   response handling, actionable creation errors.
4. **Verify end to end.** Browser tests for same-year, cross-year, same-school
   different-year, swapped home/away, human/manual modes, chart identity and
   save/load. Assert actual engine behavior across a supported rules boundary,
   not only rendered text. Update setup/player documentation.

## Non-goals

- No engine, rules-profile or chart changes; no new seasons or 2024+ rules.
- No cross-era balancing, normalization or roster substitution.
- No neutral-site, tournament or season-campaign setup in this design.
- No favorites/recents implementation in the initial phases.
- No browser-side rules inference or fallback to another season's rules.

## Paydirt consultation

Reviewed local Paydirt `paydirt-web/frontend/src/components/Game/TeamSelectPhase.jsx`
and `paydirt-web/backend/routes.py` (`/api/seasons`, `/api/teams`), plus
`docs/seasons.md` and `docs/dev-notes/issues/FLOW-020.md`.

Applicable findings:

- Paydirt's setup uses one shared season selector; changing it clears both team
  selections, and game creation submits one season for both teams. FLOW-020
  records the same limitation and the request for independent selections.
- Paydirt's team grid is a click-to-assign card layout with explicit
  player/opponent badges and a home/away choice. The card metaphor and clear
  selected-state labeling are worth adapting.
- Paydirt documents that the home team's season rules apply, including
  cross-season games. Bowl Bound already implements that policy; adapt the
  visibility, not the NFL rules.

Deliberately not reused: the shared-season selector and its clearing behavior,
the single-season game-creation payload, Paydirt's NFL rules and season data,
its private charts, and any runtime dependency. Bowl Bound keeps its own
season-qualified IDs, home-season policy and engine authority.
