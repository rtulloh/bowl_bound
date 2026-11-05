# API play commentary and highlights

Every report and `view.log` item includes additive `commentary`: engine-generated
announcer-style text using the game's optional local roster snapshot, or generic
roles if names are missing. CLI and web display the same natural play-by-play.
Kicks preserve their complete engine distance/result details after the call.
Automatic kneels/spikes, pending, unsupported, penalty and ambiguous-recovery
reports retain factual wording; clients must not interpret prose to determine
football results.

Each report and `view.log` item also includes additive `highlights`, an array of
engine-classified tags: `interception_pending`, `interception`, `fumble`,
`touchdown`, `conversion`, `breakaway`, and `touchback`. It is empty when the
engine has no highlight. Clients may choose labels and visual styling for these
tags, but must not classify highlights from outcomes, timing, statistics, or
trace details.

`description` and all structured report fields are unchanged. Null reports stay
null. Create/get/action/coached/load responses use the same serialization. Names
are illustrative labels, not player statistics. Phrase selection is stable for
the report number and consumes no randomness. Saves do not contain commentary,
highlights, or rosters. Load may refresh names from current installed rosters.
Commentary and highlights do not change save replay semantics.

For a scrimmage penalty followed by a fumble, the engine completes recovery and
any required return/end-zone choices before exposing the original accept/decline
controls. `pending.decision_outcomes` then contains the known decline field or
scoring result, and the decline label describes it. Pending reports include the
actual recovery rolls in their structured trace. The view's committed field,
score, statistics, clock and log advance only after the original penalty choice.
Clients display these backend facts without predicting recovery or enforcement.
Older saves paused before a fumble's recovery expose a single engine-owned
`fumble:resolve` pending choice first. Selecting it uses the ordinary decision
endpoint; loading and inspecting that pending step consume no new dice. Current
saves use replay profile `bowl-bound-m33-v1`; the JSON schema remains version 1.

## Razzle-Dazzle pending context

A Razzle-Dazzle pending decision includes additive `razzle_context` with the
already declared `defense`, both observed comparison `rolls` (physical black and
white faces), and `free_wildcard` access status. Other pending decisions use null.
These are revealed engine facts, not a future dice source. Choices retain their
unresolved B/QR/QT/Option symbols until selected and rolled; `decision_outcomes`
does not report an exact future result for them. Computer probability estimates
are not serialized. Clients display engine choices and reports without reading
charts or calculating outcome probabilities.

No-change Razzle-Dazzle choices expose `0` in both `label` and
`presentation_value`, even when the underlying cell carries an out-of-bounds
marker. Raw trace cells and gameplay facts retain that marker. Choices also
include nullable `replay_label`, reserved for engine save compatibility; clients
display `label` and the presentation fields. Existing pending saves retain their
original semantic digest and choice IDs.

Pending decisions include nullable `decision_context`, an engine-provided display
string. Interception decisions use it to identify the already-known interception
spot from the intercepting team's perspective, including goal-line or end-zone
locations. It describes the ball before a return; it does not predict the return,
award possession or change the committed `view.state`. CLI and browser display it
beside the choices. This derived context is excluded from save digests.

## Engine-owned play bounds declarations

Regulation views offer `game_actions` with `bounds:oob` and `bounds:ib` only
when a scrimmage play can be selected. Clients submit an offered action through
the game-action endpoint; `view.bounds_declaration` reports the selected value,
and `view.play_modifiers` contains the offered IDs and reasons. The declaration
is mutually exclusive, applies to the next scrimmage play, and is cleared by the
engine after that play. Clients must not apply yardage or clock changes themselves.

Regulation views also provide `defense_name`, `home_timeouts` and `away_timeouts`
as presentation-ready fields. `score.home` and `score.away` remain the explicit
score values. Clients should use these named fields rather than infer the
opposing team or select timeout counts by tuple position; `clock.timeouts` stays
available for compatibility.


Every game response view includes `fourth_down_guidance`, either null or an
engine-owned object containing `action` (`field_goal`, `punt`, or `go`), `label`,
`summary`, `attempt_distance`, `difficulty`, and the declared `aggression`.
Current normal difficulties share the CPU's public policy. Guidance is available
only on an eligible fourth-down scrimmage with a legal kick, for the human offense
(or the current offense in manual mode). Pending mandatory choices, conversions,
overtime and finished games have no guidance. Adapters pass the captured response
view to `SavedGame.fourth_down_guidance`; clients display its text and never compute
kick range, chart probabilities, or the policy. This read-only field consumes no
dice and changes no coaching history, command revision or save contents.


Regulation views add nullable `armed_timeout` (`home`/`away`), semantic boolean
`conditional_timeout`, and the engine's `armed_timeout_label`. The primary web
`game_actions` offer `timeout_after:<side>`: request/cancel an eligible timeout
for the selected next call. Coached responses offer only the human's own side.
Submit the engine ID to the action endpoint. Selection consumes no play, clock,
budget or dice. Mandatory continuations/save/load preserve it. At the final
supported report, use one timeout and 10 seconds only if normal timing would
allow a post-play timeout (more than 10 seconds); otherwise clear it unused.
Unsupported outcomes preserve the intent. No-time plays, tries and period
boundaries do not invent a charge. Clients never compute this eligibility.

Legacy `timeout:<side>` remains an unconditional next-play reservation with its
original replay/API semantics and menus; current browser controls prefer the
new conditional action when offered. Actual spent timeouts still record
`timeout:<side>` plus 10 seconds in `timing_log`. Existing
`clock:timeout:<side>` decisions retain their completed-play meaning. Overtime's
legacy action retains its immediate budget rule and has no conditional intent.
The new semantic flag is hashed when true; its false default and view-only
conditional action offers are omitted when validating legacy save digests.

Regulation `clock_timing_label` explains a completed play's still-pending normal
charge. It is engine-generated presentation and excluded from semantic save
digests. Response reports/log entries add nullable `timing_label`, generated from
the captured regulation view's recorded timeout charge. Pending reports do not
claim a timeout was consumed. Clients display these labels without deriving
timing or joining chart results. Old command and replay semantics remain strict.


Regulation views include engine-owned Boolean `normal_timing_ends_period`. It
is true only while a completed play awaits its default time charge and that
charge would expire the current quarter. It predicts no future play result and
spends no time, budget or dice. Current coaching uses it at the existing clock
choice boundary to preserve an eligible public-policy field goal before Q2/Q4
expiration. Clients pass through this fact and never calculate timing semantics.
The derived field is excluded from legacy semantic save digests; actual clocks,
commands and rolls remain strictly validated.

Regulation views may include `review`: an engine-authored `kind`, `title`, ordered
`lines`, and acknowledgment `action`. Adapters show these facts and hold automatic
presentation until `/action` receives the offered `review:continue`. The action
changes no football state, clock, dice, scoring or statistics. Existing direct
football commands remain valid for older adapters and dismiss the previous
review. Report `announcements` retain ordered engine commentary alongside the
original report; they are not additional plays. Neither field enters coaching
observations or football semantic integrity. Acknowledgments remain journaled.

## Read-only chart book

`GET /api/games/{game_id}/charts?side=home|away` returns the engine-authored
chart book for one of the game's frozen matchup teams. `side` is required and
restricted to `home` or `away`; no file paths or arbitrary team IDs are accepted.
Unknown games return 404 and invalid sides return 422. The endpoint is available
in manual and coached games without submitting a call or preparing a turn.

The response contains `team`, `season`, explanatory `note`, `offense` and
`defense` tables, a color `legend`, `symbols`, `formations` and a shared
`priority` reference. Each table has
`key`, `title`, `roll_label`, `columns` (`key`, `label`) and ordered `rows`
(`label`, `description`, `cells`). Cells contain display `label`, normalized
`color` and accessible `description`. Offense has 30 rows and 12 columns
(plays 1–9 plus B/QR/QT); defense has 30 rows (A–F, totals 1–5) and nine columns.
Color categories are red/green/white/black/yellow, with `unclassified` for facts
without a normalized color. The client displays these facts without interpreting
CSV strings or resolving football. Source provenance and private paths are omitted.

`priority` contains a `table` in the same display format, its explanatory `note`,
a `legend` of operation labels/descriptions, and ordered exception `notes`.
The first 13 columns reproduce the ordinary printed reference; the marked 14th
column displays the approved defensive `(B)` extension. Its 12 rows group
equivalent offensive facts. Every operation is derived with the engine's pure
resolver, without dice or a second behavioral matrix. It is identical for both
sides; the team tables remain the selected game's frozen loaded CSV charts.

The browser also supports `/?charts=<game_id>&side=home|away&view=offense|defense|priority`
as a read-only standalone shell, using this same endpoint for both matchup
teams. It does not mount game setup or submit commands. Unknown/expired games
show recovery controls rather than creating a replacement match.

Reads do not alter revision, pending decisions, coaching state, dice, clock,
statistics or the save journal, and do not reveal a selected computer call.
