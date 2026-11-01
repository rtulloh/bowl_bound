# Milestone 22 — Advanced options and coaching follow-ups

## Scope and decision boundary

The canonical scope is [Milestone 22 in the project plan](project-plan.md#22-add-advanced-options-one-at-a-time).
This note maps its options to tickets so each potential change can be triaged and
approved separately. Ticket creation does not authorize implementation. Unsupported
options remain unavailable until their Bowl Bound rule and scope are accepted.

## Paydirt consultation — 2026-11-01

Reviewed the local Paydirt source before preparing the Milestone 22 ticket set:

- `paydirt/interactive_game.py:1040-1066` presents regular versus onside kickoff
  choices; `paydirt/game_engine.py:1160-1200` resolves Paydirt's onside kick. Adapt
  the separation between assigned kicking team and kick-type choice. Do not copy its
  dice threshold, recovery, distance, field spot, or timing; Bowl Bound's Basic VI-8
  controls those details.
- `paydirt/chart_loader.py:222-234` parses its power-rating and yardage-factor
  metadata; `paydirt/cli_charts.py:302-303` displays those fields. This is useful
  evidence that chart metadata and gameplay effects are separate concerns. Do not
  reuse Paydirt's fields or formulas as Bowl Bound behavior.
- `paydirt/play_resolver.py:581-681` has a QB Sneak procedure. It is only evidence
  that the procedure can be isolated and tested; Bowl Bound's Advanced I-2 wording
  is authoritative for any implementation.
- `paydirt/docs/clock-management.md:15` discusses its ruleset's alternate timing.
  Review the concept, but do not copy its timing categories or conclusions into
  Bowl Bound's Advanced VII profile.
- `paydirt/priority_chart.py:12-25` and `paydirt/tests/test_fumble.py:11` show
  Paydirt's own blocked-kick priority and recovery assumptions. Those differ from
  Bowl Bound's charts and must not be reused.
- Searches found no applicable Bowl Bound-style Advanced II Wild Card/run-pass/
  nickel/red-zone defense or option-guess procedure in Paydirt. Its “Wild Card”
  references are playoff-round names, not a defensive call.

No Paydirt code or data is copied, and Bowl Bound gains no runtime dependency.
The local Bowl Bound rulebook remains the implementation authority; no rule is
enabled solely because Paydirt has a similarly named feature.

### Return-rule correction review — 2026-11-01

- Reviewed `paydirt/penalty_handler.py:451-460` for return-foul midpoint handling.
  Its field-coordinate formula illustrates the midpoint rule, but Bowl Bound uses
  yards-to-goal coordinates; the formula is not reused. Basic VI-4(C)(vii),
  documented on pp. 8–9, governs Bowl Bound's marker toward midfield.
- Basic VI-13(D)(iii–iv) and (F)(i–ii), pp. 11–12, distinguish own-end-zone
  fumbles from an elected return that fails to cross the goal line. Preserve those
  separate cases while reviewing RULE-013; do not infer one outcome from the other.
- Basic VI-4 and the prepared-result structure govern acceptance of return fouls
  (RULE-014) and the fixed one-yard F_ENDZONE location (RULE-015). No Paydirt rule
  or private chart data is used for those decisions.

### Shared return-penalty review — 2026-11-01

- Reviewed `paydirt/game_engine.py:700-719` and
  `paydirt/penalty_handler.py:451-460` for return endpoints and midpoint marking.
  These implementations use Paydirt field coordinates and behavior; adapt only
  the separation of return resolution from penalty enforcement. Bowl Bound's Basic
  VI-4(C)(vi–vii), pp. 8–9, controls return fouls, midfield rounding, and endpoints.
- Existing Bowl Bound paths agree for ordinary in-field returns but diverge at
  end-zone and touchdown endpoints. The test-first change will centralize Bowl
  Bound marker/enforcement results and retain the kick-specific touchback spot.
- The shared `ReturnPenaltyResult` now reports field position, touchback, or safety;
  session and special-teams callers commit the appropriate engine result. Synthetic
  tests cover both foul sides, field/end-zone/end-line/touchdown endpoints, return
  yard credit, and the season-specific free-kick touchback spot. Paydirt's endpoint
  and yardage formulas were not reused.

### Per-play bounds declaration review — 2026-11-01

- Reviewed `paydirt/interactive_game.py:829-879` and
  `paydirt/game_engine.py:1816-1910, 2150-2155` for declaration input, the
  five-yard adjustment, and the clock effect. These references confirm that the
  declaration belongs to the upcoming snap and that its adjustment follows
  offensive/defensive resolution. Paydirt's simultaneous-declaration precedence
  is deliberately not reused: RULE-010 requires Bowl Bound to reject mutually
  exclusive OOB/IB requests.
- The Bowl Bound rulebook's Advanced I-4(C) and I-6(C), printed pp. 14–15, is
  authoritative for exceptions and five-yard costs. Standard Timing Chart p. 34
  remains authoritative for Bowl Bound timing. Do not copy Paydirt's clock ranges,
  random timing, or NFL-specific play behavior.
- Paydirt's UI notation is design input only. Bowl Bound's rulebook names the
  declarations but does not prescribe terminal shorthand, so the terminal offers
  O/I shortcuts and explicit `action bounds:oob` / `action bounds:ib` commands;
  it does not infer `7+` / `7-` chart notation. No Paydirt code or data is reused.

### Kneel-out coaching review — 2026-11-01

- Reviewed `paydirt/game_engine.py:3413` and `paydirt/computer_ai.py:154-205`,
  especially the AI's engine-owned `can_kneel_out_game()` check. Adapt the
  separation between engine safety evaluation and policy choice.
- Do not copy Paydirt's thresholds or timing assumptions. Bowl Bound's query
  uses its 30-second kneel duration, opponent timeout's 10-second timing,
  remaining downs, fourth-quarter state, score and the engine's two-yard kneel
  loss to prevent a safety. Legacy coaching policies retain their prior behavior;
  the updated policy uses a new version.

### Situation-aware coaching review — 2026-11-01

- Reviewed `paydirt/computer_ai.py:311-484` for its score/time and field-position
  strategy gates, `computer_ai.py:827-864` for late two-point choices, and
  `offense_strategy.py:83` for bounded conversion scoring. Adapt the separation
  of situation facts from policy preferences and the call-distribution audit.
  Do not copy Paydirt's NFL field-goal distance tiers or thresholds.
- Bowl Bound's rulebook, printed pp. 9–10 (PDF pp. 12–13), makes field-goal
  availability and success a team-chart procedure based on line-of-scrimmage
  distance, and offers kick or two-point conversion choices. The engine and
  imported chart remain authoritative; no fixed NFL kick range is introduced.

### Easy/Medium urgency-mixture review — 2026-11-01

- Reviewed `paydirt/computer_ai.py:559-591` for gradual deficit/time passing
  pressure. Adapt the idea of continuously weighting a complete legal call set;
  do not copy Paydirt's `scores_needed` rounding, exponential scale, clock units,
  or run weights. Bowl Bound v4 uses its own bounded signed pressure profile and
  keeps every offered offensive call possible.
- Pressure uses only engine-provided score, quarter, and remaining time. It
  changes coaching weights, never legal actions, game timing, or engine rules.
  Earlier policy versions retain their saved selection streams.

### Hard repetition review — 2026-11-01

- Reviewed Paydirt `paydirt/offense_strategy.py:9-16,101-110` and
  `tests/test_ai_offense_variety.py:73-118,201-212`. Adapt its bounded recent-call
  discount, situation filtering, decay, and 0.30 floor. Bowl Bound uses its own
  shared public-observation bucket from the coaching audit, including its exact
  down, quarter, overtime, hurry, phase, side, and legal menus; it does not copy
  Paydirt's down/distance-only key or its game-history format.
- Persist no new mutable AI state: committed call history is rebuilt from the
  save journal and pre-snap engine observations. Ship the changed Hard policy as
  v5 so existing policy streams remain stable.

## Ticket coverage

| Milestone 22 change or decision | Ticket |
| --- | --- |
| Advanced II Wild Card, run/pass, nickel-zone, and red-zone defenses | [RULE-019](issues/RULE/RULE-019.md) |
| Defensive guesses specific to SOP/BLP option plays | [RULE-020](issues/RULE/RULE-020.md) |
| QB Sneak, Advanced I-2 | [RULE-021](issues/RULE/RULE-021.md) |
| Scope of additional situational plays not yet named | [RULE-022](issues/RULE/RULE-022.md) |
| Yardage factors, Advanced IX | [RULE-023](issues/RULE/RULE-023.md) |
| Power-rating gameplay effects, Advanced VIII | [RULE-024](issues/RULE/RULE-024.md) |
| Onside kick choice and resolution, Basic VI-8 | [RULE-025](issues/RULE/RULE-025.md) |
| Fake options, all-out kick rush, and free block, Advanced V | [RULE-026](issues/RULE/RULE-026.md) |
| Alternate/hybrid timing decision, Advanced VII | [RULE-027](issues/RULE/RULE-027.md) |
| Razzle-Dazzle, Advanced I-1 | [RULE-028](issues/RULE/RULE-028.md) |
| Elected safeties, Advanced I-5 | [RULE-029](issues/RULE/RULE-029.md) |
| Weather effects, Advanced VI | [RULE-030](issues/RULE/RULE-030.md) |
| Intentional delay, Advanced I-6(B) | [RULE-031](issues/RULE/RULE-031.md) |
| Advanced kickoff/punt choices and punt/kickoff returns, Advanced III-IV | [RULE-032](issues/RULE/RULE-032.md) |
| Guaranteed in-bounds/out-of-bounds declarations, already requested | [RULE-010](issues/RULE/RULE-010.md) |

Other Milestone 22 work is mapped ticket by ticket below. These are existing
coaching, API, CLI, development, flow, rules-correction, and presentation findings,
rather than additional advanced-option features.

| Tracked change | Ticket |
| --- | --- |
| Engine-owned kneel-out safety query | [AI-011](issues/AI/AI-011.md) |
| Score-, time-, chart-, and aggression-aware fourth-down and conversion coaching | [AI-012](issues/AI/AI-012.md) |
| Urgency and lead protection in Easy/Medium play selection | [AI-013](issues/AI/AI-013.md) |
| Situation-bucketed Hard repetition discount | [AI-014](issues/AI/AI-014.md) |
| Easy/Medium defensive situational guards | [AI-015](issues/AI/AI-015.md) |
| Baseline decision-policy safety and fallback reporting | [AI-016](issues/AI/AI-016.md) |
| Preserve disabled choices and engine reasons in coached turns | [AI-017](issues/AI/AI-017.md) |
| Post-game summary of computer call history | [AI-019](issues/AI/AI-019.md) |
| Keep Hard coaching safe for engine-adjusted try spots | [AI-020](issues/AI/AI-020.md) |
| Map coordinator errors to clear client responses | [API-002](issues/API/API-002.md) |
| Bind games to control mode and make repeated coach posts safe | [API-003](issues/API/API-003.md) |
| Improve terminal input errors, case handling, and paused-game loading | [CLI-044](issues/CLI/CLI-044.md) |
| Remove obsolete manual-mode branches | [CLI-045](issues/CLI/CLI-045.md) |
| Share return and recovery rule logic | [DEV-022](issues/DEV/DEV-022.md) |
| Deduplicate team discovery and shared constants | [DEV-024](issues/DEV/DEV-024.md) |
| Document a coaching play-test protocol | [DEV-028](issues/DEV/DEV-028.md) |
| Correct kickoff status while receiver choice is pending | [FLOW-002](issues/FLOW/FLOW-002.md) |
| Correct return-foul midpoint rounding | [RULE-012](issues/RULE/RULE-012.md) |
| Distinguish end-zone return fumbles from non-advances | [RULE-013](issues/RULE/RULE-013.md) |
| Correct return-penalty acceptance and end-zone reasoning | [RULE-014](issues/RULE/RULE-014.md) |
| Correct end-zone trace labels and decline text | [RULE-015](issues/RULE/RULE-015.md) |
| Deliver engine commentary and highlights to the browser | [UI-036](issues/UI/UI-036.md) |
| Enable the Spike control and remove dead timeout mappings | [UI-037](issues/UI/UI-037.md) |

### Ticket coverage reconciliation — 2026-11-01

Checked the generated tracker against the Milestone 22 plan: all 38 tickets
assigned to the milestone have individual mappings above. They cover the 14
advanced-rule items, RULE-010 bounds declarations, nine AI findings, two API
findings, two CLI findings, three development findings, one flow finding, four
return-rule findings, and two UI findings. AI-018 is assigned to Milestone 23 for
full-game coordinator coverage, so its absence here is intentional. No planned
Milestone 22 change is missing a ticket.

The owner explicitly removed a separate normal-runoff action; kneeldown is the
clock-draining play. No ticket is created to restore that rejected behavior.
`IMPORT-012` concerns importing power-rating metadata; RULE-024 separately covers
whether ratings affect gameplay.

## Validation before implementation

Review each ticket and its rulebook text before starting its behavior change. For
an adopted option, write synthetic tests first, verify the expected failure, then
implement only the approved Bowl Bound procedure. Reconcile score, possession,
timing, statistics, structured traces, coaching privacy, and save replay where
affected. If an option is deferred, keep it unavailable and record that decision.
