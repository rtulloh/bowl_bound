# Milestone 35 — Optional coffin-corner punts and halftime summary

## Owner direction and scope

On 2026-11-02 the owner requested coffin-corner punt support after asking whether
it was in Milestone 33. The owner confirmed Milestone 35 because Milestone 34 is
already assigned to the separate chart-generator workstream. Track the engine
and adapters in RULE-043 and coaching in AI-030. Do not add this feature to
Milestone 33, the generator branch, or alpha 4. Other deferred special-team
options remain outside scope.

On 2026-11-03 the owner requested scheduling the missing halftime announcement
and summary in the next milestone. Milestone 35 is the next planned gameplay
milestone after the active M33/M34 workstreams, so [CLI-058](issues/CLI/CLI-058.md)
moves here from M23. Include a visible one-time first-half recap before the
scheduled second-half kickoff, including automatic computer-owned kickoff paths.
This scheduling change implements no behavior and moves no other CLI backlog.

## Paydirt consultation before planning

Reviewed local Paydirt `paydirt/game_engine.py` (`_handle_punt`),
`paydirt/computer_ai.py` (`_fourth_down_decision`), and
`tests/test_punt_roll_metadata.py`.

Adapt the separation between a predeclared punt choice and engine resolution,
and regression coverage preserving the actual punt roll through touchback and
no-return early exits, for both possession sides and penalty procedures.
Do not reuse Paydirt's numeric subtraction/OOB thresholds, NFL field-goal
heuristics, global random selection, raw-string interpretation, or team data.
Verify Bowl Bound's authoritative procedure and normalized chart semantics first.
Reconsult relevant implementation/tests when actual implementation starts.

For the added halftime scope, reviewed local Paydirt
`paydirt/interactive_game.py:3061-3077` and `3834-3855`,
`tests/test_halftime_ownership.py:64-95`, and `docs/playing.md:210-212`.
Adapt the distinct halftime banner/box-score presentation and synthetic tests
covering several half-ending paths. Keep Bowl Bound's engine authoritative for
period/try completion, halftime facts, kickoff ownership and statistics. Do not
copy Paydirt's NFL timing, kickoff procedures, mutable random patches or its
mandatory Enter pause; a new pause is not part of this scheduling request.

## Planned acceptance

- Confirm the Bowl Bound rule and explicit option-enable contract before coding.
- Add synthetic failing tests, then engine-owned legality and resolution.
- Cover legal adjustment boundaries, field position, special-result precedence,
  returns/touchbacks, applicable recoveries/penalties, clock, scoring/statistics,
  complete traces and save/replay continuity.
- Add thin API/CLI/browser controls and AI-030 comparisons with equivalent human
  guidance. Preserve the approved public-information policy; document and review
  any proposed change to information available to coaches separately.
- Add CLI-058's one-time halftime announcement, score-by-quarter/first-half total,
  scoring events and supported team statistics from engine-owned facts. Cover
  ordinary period ends, scoring and pending-decision paths, both human sides,
  computer-owned automatic kickoffs and save/resume. Show the recap before any
  second-half kickoff report without changing timing, dice or kickoff ownership.
- Complete focused and full regression gates, review synthetic/public-safe
  documentation, record tested commits and actual play-test confirmation, then
  make the dedicated Milestone 35 commit. This note records planned work only.
