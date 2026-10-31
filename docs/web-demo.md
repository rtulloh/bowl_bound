# Web game (Milestones 10–20)

A thin browser front end over the real engine. Regulation games begin with the
engine’s offensive-dice toss, kick/receive decision, and opening kickoff. The engine
owns the quarter, clock, timeouts, scoring, legal choices, and final status; the
browser never runs its own clock. Tied games use the selected historical overtime profile.

## Run it

Use **Node.js 24.22.1 LTS** with its bundled **npm 11.19.1** for frontend
development/builds/tests. From the repository root, `nvm install` and `nvm use`
select the version pinned in `.nvmrc`; other version managers should select that
same version. `frontend/.npmrc` rejects installs with unsupported Node/npm
versions. This does not change your global Node default.

Node 18 is end-of-life. The [24.22.1 security release](https://nodejs.org/en/blog/release/v24.22.1)
includes the [eMudhra CA compromise mitigation](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases).
This frontend uses Node for development/build/test tooling; the deployed web
backend is Python and serves static assets. Updating Node does not patch system
or Python certificate stores or audit third-party npm dependencies automatically.

```bash
nvm install
nvm use
.venv/bin/python -m pip install -e '.[web]'
.venv/bin/python -m bowl_bound.sample_teams         # original fictional teams
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m backend --seasons seasons        # http://127.0.0.1:8000
```

The server binds to this computer only. `--host` with a non-local address is refused unless
you also pass `--allow-remote`, because there is no authentication. For development, run
`npx vite` in `frontend/` (port 5173, proxying `/api` to port 8000) next to the backend.

Teams are read from `seasons/<season>/<team-slug>/` exactly as described in the
[team file format](team-bundle.md). A team that cannot be read is listed as a problem, and
its file contents are never echoed.

## What it shows

Pick a home and away team (the public Cedar Valley/Harbor Tech samples are the
default when present), choose **Regular season** or **Postseason** and your
**Control mode** on setup, then **Start game**. **Human home / computer away**
is selected by default; **Two-sided manual play** remains the last menu option.
The supported home season (1940–2023) selects the regulation and overtime rules. Resolve
the toss choice on its own **Opening toss** screen before entering the playing
screen for kickoff. A one-second animated coin flip reveals the recorded result
before kick/receive choices appear. Reduced-motion preferences skip animation and
delay. Kick/receive buttons appear before the collapsed toss audit;
the field, scoreboard, statistics and clock modifiers do not compete for space
during that decision. The winner and choices still come from the engine, not a
new browser coin toss. A failed decision stays on this screen; a saved unresolved
toss loads back into it. Computer-owned choices advance automatically. Kickoff
controls sit directly below the scoreboard/status, above the field.
In **Two-sided manual play**, select both an
offensive play (1–9) and defensive formation (A–F); the second selection submits
the play immediately. Against the computer, choosing your single call submits it.
Both manual selections clear after every submission, even if possession stays the
same or a request fails. There is no separate Snap button. Alternatively, select a human
home/away control mode for the [computer opponent and difficulty](coaching.md): only your
side’s controls appear, simultaneous calls stay private until resolution, and
computer-only turns advance automatically. The opening coin adopts Paydirt’s
presentation, but displays the engine dice-toss winner, never a second browser-generated
winner. Charts, actual dice,
Priority Chart, supplemental/Option rerolls, field position, and descriptions all
come from the engine. Open **Detailed dice and chart audit** to inspect every
consulted roll and cell. Colored dice show Black, White 1, White 2, Red and Green
with individual faces, accessible labels and engine-supplied totals. **Toss dice
audit** preserves recorded opening/overtime rolls. Kick summaries identify teams, origin, flight distance,
landing spot/depth, return distance and resulting possession/spot. Required
choices name the deciding team and move keyboard focus to an enabled choice.
Play buttons expose their selected state; new plays always require fresh calls.
High-contrast event badges emphasize existing recorded fumble recovery, interception,
touchdown and breakaway-roll facts in the latest result and play log. A pending
interception is labeled as a decision, not a committed turnover. A breakaway
lookup is labeled **Breakaway roll**, not a promised large gain. Fumble and
touchback badges can appear together without rewriting the engine description;
conversion outcomes are labeled **Conversion** rather than another touchdown.
Badges never parse chart cells/prose or calculate yardage thresholds or results.
Compact log dice inherit the light panel's dark text and retain recorded totals.
The in-game screen has no control-mode box or Pause/Resume button. Open **Game**
in the header for **New game**, **Save game** or **Load saved game**; the dropdown
overlays content without moving the play controls. Escape dismisses it. Only a
stopped automatic turn shows **Retry computer**.

Punt (**P / Punt**), field goal (**F / FG**) and kneel (**K / Kneel**) appear
alongside numbered plays in the same panel when the engine offers them, not in
separate Special Teams/Clock & Game Actions boxes. The play number or abbreviation
is above the short name; tooltips/accessibility retain the full engine label.
Kickoff (**KO**) and Hail Mary (**HM**) use the same panel; offered timeouts
live beside Hurry-up in the modifier row. These are display abbreviations, not
additional rules or keyboard bindings.
Unsupported **Q / Sneak** stays absent. Kicks and kneels resolve immediately
without a defensive formation. A punt is rolled before the receiver chooses a fair catch or return;
marked punts suppress returns. The engine schedules the opening, second-half,
post-score and safety free kicks. Home season determines kickoff placement and
free-kick touchbacks, even for mixed-season opponents.
Receiving a live kick in the end zone offers a touchback or return; the depth counts against
the return. Kickoffs out of bounds offer own-35 possession or a five-yard re-kick.
Field-goal chart yardage is measured from the line of scrimmage, not the statistical kick length.

A **touchdown** awards six points and asks the scoring team to choose a **one-point PAT**
or **two-point try**. The PAT consults only that team’s dedicated PAT outcomes, with one
real offensive roll. A two-point try starts at the opponent 2; select a play and defense
to resolve once (accepted/offsetting penalties can replay the try). A defensive touchdown
return on a try awards two points, never six or another conversion. The scoring ledger
lists committed awards and their play numbers; misses do not create a scoring award.
A field goal awards three, a safety two to the opponent, and neither offers a conversion.
The required conversion finishes before a post-touchdown kickoff or expiration.
A safety schedules the conceding team’s free kick from its own 20.

The scoreboard shows the engine’s **quarter, game clock, and remaining timeouts**.
The visible **Play modifiers** row keeps **Hurry-up mode**, **Timeout**, **Spike**,
**OOB** and **IB** together (wrapping on narrow screens). The engine applies
standard play timing automatically when you choose the next action; there is no
runoff or Continue control. If timing ends Q1 or Q3, the selected play starts in
the next quarter. If it ends a half or game, the engine shows the required
halftime, overtime or final state without running another play. Kneel is the play
for deliberately using time. Timeout and spike remain one-shot engine decisions;
unavailable controls stay disabled.
IB/OOB declarations remain disabled pending their engine implementation, including
the applicable five-yard cost and exceptions. Their approved interaction is
mutually exclusive, for one play only, then reset—not a persistent mode.
**Hurry-up mode** stays selected across plays, timeouts, possession changes,
quarters and halftime until you toggle it off; unavailable situations simply
suspend its application. Before a snap it selects the offered legal hurry action,
never duplicates reductions or skips football decisions. The optional strip also
retains the explicit one-snap hurry choice. New/loaded games start with fresh
selections and mode off. Hurry commits next-snap S/R hazards; a spike spends
another down without dice. Kneel
loses two yards without dice. Hail Mary appears only with 1–20 seconds left in
Q2/Q4, outside conversions/untimed downs. At halftime the other toss participant
chooses kick or receive; both teams reset to three timeouts. Q1/Q3 transitions
preserve the field situation. Final games reject every gameplay request.
**Four failed downs** hand
the ball over, and the field shows the same ball spot from the other team's side. An interception
requires the defense to choose a return or an incomplete pass; a fumble resolves its recovery and
any authorized return. A defender recovering in its own end zone chooses a touchback or return.
Ordinary and supplemental DS/X/T1–T3 yardage uses the full-feature physical dice
method, including independent offensive/defensive distance rolls. Each consulted
roll is visible in the engine trace; the resolved play advances state and timing.

## Team statistics

Expand **Team statistics** to see each team’s rushing, passing, sack and total-offense
summary. Sacks are already included in net rushing totals; do not subtract them again.
Only committed offensive snaps count: pending choices, penalties that cancel a play,
kicks/returns and all conversions are excluded as documented in the
[college statistics policy](statistics.md). Full-series overtime counts; paired tries
do not. Labels and values come from the engine, not browser calculations.

## Overtime

Historical regulation ties remain final through 1994 and in the 1995 regular season.
1995 postseason and 1996+ games enter a fresh engine-owned toss when tied. Its winner
chooses offense or defense first; series start at the opponent 25, with no kickoff
or game clock. The scoreboard shows **OT1**, **Untimed**, and one timeout per team
per round; unused timeouts never carry over. First possession alternates each round.

The engine requires two-point conversions from OT3 in 1997–2020 and from OT2 in
2021–2023. Paired two-point tries replace full series from OT5 in 2019–2020 and OT3
in 2021–2023. Bowl Bound tries retain the approved opponent-2 spot. Both teams get
their series/try before scores are compared; a defensive score during a normal
series ends the game immediately, but a defensive return on a try does not erase
the other attempt. Winning second-series touchdowns omit unnecessary conversions.
There is no fixed overtime-round cap. Regulation hurry-up, spike, Hail Mary and
clock modifiers are unavailable during overtime.

## Architecture

| Layer | Owns |
| --- | --- |
| `bowl_bound/session.py` | One-play resolution, choices, scores, descriptions, and traces |
| `bowl_bound/regulation.py`, `timing.py`, `overtime.py` | Toss, clock, timeouts, period/series boundaries, historical overtime and kick scheduling |
| `bowl_bound/statistics.py` | Immutable offensive credits, college team totals and display rows |
| `bowl_bound/save_game.py` | Versioned private saves, command/dice journal, deterministic engine/coaching reconstruction |
| `bowl_bound/coaching.py`, `coaching_session.py` | Public-observation baseline policy, legal fallbacks, side ownership and concealed simultaneous-call coordination |
| `backend/app.py` | Validation, team discovery, in-memory sessions (50 at most), JSON |
| `frontend/src` | Drawing what the engine sent |

The browser holds no football rules. A test scans the front-end source and fails if it
contains Paydirt play names, down/distance arithmetic, or priority handling.

## API

| Request | Result |
| --- | --- |
| `GET /api/health` | `{"status": "healthy", "service": "bowl-bound"}` |
| `GET /api/version` | Public `version` and PEP440 `python_version`; see [versioning](versioning.md) |
| `GET /api/teams` | `{teams: [{id, name, season}], problems: [{id, reason}]}` |
| `POST /api/games` | Body `{home, away, seed?, mode?, game_type?, start_yards_to_goal?, difficulty?, coach_policy?}`; choose `difficulty` or `coach_policy`, never both; omitted policy means Medium; `game_type` is `regular` (default) or `postseason`; browser sends `mode: "regulation"`; returns `{game_id, seed, coach_policy, view}` |
| `GET /api/games/{id}` | `{game_id, seed, coach_policy, view}` |
| `GET /api/games/{id}/save` | Private JSON download; no chart tables; does not advance dice or choices |
| `POST /api/games/load` | Raw save JSON body; returns independent `{game_id, seed, coach_policy, view}` after validation; 422 invalid/incompatible/unavailable teams, 413 over 2 MiB |
| `POST /api/games/{id}/snap` | Body `{play: "1"-"9", defense: "A"-"F"}`; returns `{report, view}`; 409 while a blocking engine decision is pending |
| `POST /api/games/{id}/kick` | Body `{action}` (`kickoff`, `punt`, or `field_goal`) selected from `view.actions.special`; returns `{report, view}`; 409 while a decision is pending or after demo completion, 422 for an unavailable action (including kicks during a two-point try) |
| `POST /api/games/{id}/decision` | Body `{choice}` from `view.pending.choices`; returns `{report, view}`; 409 if nothing is pending, 422 for an unknown or disabled choice |
| `POST /api/games/{id}/action` | Body `{action}` (`kneel`, `hail_mary`, `timeout:home`, `timeout:away`) from `view.game_actions`; returns `{report, view}`; report may be null for administrative actions; 422 outside regulation mode |
| `POST /api/games/{id}/coach` | Body `{human_side: "home" or "away", human_call?}`; one automatic action or simultaneous play, returning `{report, view, turn}`; no computer call in previews |

Creation/current-view endpoints accept optional `?human_side=home` / `away` and
return human-only `turn` controls. Human kick/decision/action endpoints accept the
same query and validate those controls under the game lock. See the
[coaching API contract](coaching.md#api). Manual endpoints remain compatible.

`difficulty` is `easy`, `medium` or `hard`. Explicit `coach_policy` is `baseline`,
`chart-v1`, `easy-v1`, `medium-v1` or `hard-v1`; it is an alternative versioned
interface, not a second difficulty override. Example public-sample create body:

```json
{"home":"2007/cedar-valley","away":"2007/harbor-tech","seed":7,"mode":"regulation","difficulty":"hard"}
```

Loading restores the saved policy and reconstructs its committed-call history;
setup selections never replace it. See [save compatibility](saves.md#schema-and-compatibility).
POST bodies are bounded before JSON validation: 16 KiB for ordinary commands,
2 MiB for save imports, including chunked uploads; excess is 413. Registry access
updates least-recently-used order. Evicted IDs return 404, but already captured
in-flight games finish safely. Commands and matching views share a per-game lock.
Team ids look like `2007/cedar-valley` and are checked against a strict pattern, so they cannot
leave the seasons folder. Invalid input is 422, an unknown game or team is 404, and a snap
after the drive ended is 409. The seed is returned so a drive can be reproduced.

The API keeps the original `mode: "drive"` default for compatibility with focused
one-drive clients/tests; `start_yards_to_goal` applies only to that mode. The web
UI explicitly requests regulation. No existing in-memory drive is converted.

Regulation phases add `opening_choice`, `kickoff`, `clock_choice`, `halftime_choice`,
`final` and `overtime_choice` around `scrimmage`, `conversion_choice` and
`two_point_try`. `view.status` supplies display text. A null field is not finality.
`view.finished` guards completion; overtime choices are not finished games.
`view.clock` contains quarter/remaining seconds, formatted labels and timeout counts;
`view.timing_log` audits committed time charges. `view.clock_optional` authorizes
next-play controls during `clock_choice`; `view.clock_modifiers` supplies compact
labels and exact decision IDs. Next-play requests commit normal prior timing in
the engine, once, before consuming any new dice. A period-ending runoff advances
the period without executing the requested next play; use the returned view.
Explicit `clock:runoff` remains accepted for older clients, but is not offered in
current engine views or user interfaces. Toss/halftime choices may return a null
report. Conversion IDs remain `conversion:kick` and `conversion:two`; the
two-point setup consumes neither dice nor a log entry. `ot:offense` / `ot:defense`
select the overtime toss winner’s first-series role. `view.overtime` supplies round,
series, first/offensive team identities, paired-try and mandatory-two flags;
`view.overtime_toss_rolls` records the fresh toss. Display engine clock labels, not
a regulation countdown, in overtime.
`view.scoring` contains immutable awards with `number`, `play_number`, `team`, `kind`,
and `points`. The score is derived from these awards, not calculated by the browser.
`report.statistics` carries committed offensive credit. `view.statistics` contains
`home`/`away` numeric team totals and engine-formatted `rows` (`label`, `home`, `away`);
see the [statistics contract](statistics.md#contract). These fields are additive in
both drive and regulation modes; views/clock choices do not add statistical plays.
`view.kickoff_penalties` retains accepted defensive 5Y/15-yard try fouls until
regulation schedules and marks the following kickoff, including half-distance.

## Tests

- `tests/test_session.py`, `tests/test_api.py`, `tests/test_web_launcher.py`: engine session,
  API and launcher, all on synthetic teams. Original selectable samples and their
  outcome coverage/complete-game/save checks are in tests/test_sample_teams.py.
  See [sample teams](sample-teams.md) for reproducible installation and CC0 terms.
- `frontend/src/test`: component tests and the no-rules scan (`npx vitest run`).
- `frontend/e2e`: Playwright drives the production build against the real API and engine
  (`BB_E2E_CHANNEL=chrome` uses an installed Chrome).

## Save and resume

Open **Game → Save game** to download a private JSON file, including while a decision is
pending. After a refresh/server restart, choose it through **Load saved game** on
setup; during play use **Game → Load saved game**. Loads use the mode selected on
setup (human home/computer away by default); they clear hurry mode and fresh-call selections.
Loading validates matching local teams and creates a separate game with the same
choices, clock, history, statistics and future dice; invalid loads do not replace
the current game. No automatic save/resume is implied. See the
[save guide and compatibility contract](saves.md).

## Limits

Live sessions remain in memory: restarting the backend loses unsaved games. Save
before stopping it; downloaded files can be loaded afterward with matching local
teams. No authentication; this is a local game, not multiplayer access control.
Difficulty defaults to Medium; Easy/Hard adjust coaching, never dice odds.
Hard uses bounded chart-aware engine analysis, not exact win probabilities.
Historical season support is limited to 1940–2023
major-college profiles.
Alternate/hybrid timing and advanced kick options remain unavailable.
Some inherited end-zone recovery-return chains and end-zone return-foul acceptance
remain unavailable, with disabled choices and an engine explanation; touchback or
decline remains legal. See the [Milestone 15 review](dev-notes/milestone-15.md).
Historical teams are private; use [original fictional samples](sample-teams.md)
for reusable tests and demos. See the [attribution notes](ATTRIBUTION.md).

Routine scrimmage and clock-choice status prompts below the scoreboard are
screen-reader-only to avoid repeating the play-panel instructions and taking
vertical space. Kickoff, required-decision, and final status remain visible.

The play log retains each engine description and now shows the recorded before/after
team, down/distance, field position and yardage. Expand an entry’s **Dice and chart
audit** for every observed roll, its total and consulted cell, including supplemental
rolls. Terminal plays without an after-state do not invent a new field position.
The browser neither recomputes yardage nor explains outcomes by parsing chart text.

Play summaries and log headings use the same friendly defense names as the
selectors, prefixed by their chart letter (for example, `C Short yardage (wide)`).
Expanded chart audits retain `Formation C` as the exact lookup identifier.
This wording change preserves legacy-save verification and does not alter dice,
chart selection, or game outcomes.

Each play-log entry also shows a compact, always-visible recorded-dice line,
for example `offense: [1, 2, 3] → 15 · defense: [2, 1] → 3`. Brackets list
physical faces and the arrow shows the engine-recorded lookup total; the UI
does not add faces or calculate outcomes. Supplemental/repeated trace rolls
remain in recorded order, with full cells available in the expanded audit.
Entries with no recorded rolls do not invent a dice line.

Report/log responses expose additive engine-generated
[`commentary`](api.md), with optional illustrative roster names; semantic
descriptions and downloadable saves remain unchanged.

Live results and play logs render API commentary as escaped text, falling back
to legacy descriptions only when commentary is absent. Long optional player
labels wrap in compact/mobile views; no client-side actor mapping is performed.
