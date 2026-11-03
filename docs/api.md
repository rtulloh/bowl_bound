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


Regulation views add nullable `armed_timeout` (`home`/`away`) and the engine's
`armed_timeout_label`. Legal `game_actions` may offer `timeout:<side>` to arm or
cancel that side's next-play timeout. Coached responses offer only the human's
own action. Submit the ID to the existing action endpoint; the null report and
unchanged clock mean no play or timeout has been spent. A subsequent completed
legal play consumes it once and records `timeout:<side>` plus 10 seconds in
`timing_log`. Pending continuations preserve the modifier; no-time elected
safeties and period boundaries clear it unused. The API/frontend never infer
eligibility from counts, possession or phase. Existing `clock:timeout:<side>`
decisions retain their prior-play meaning; overtime's action retains its own
existing immediate budget rule.
