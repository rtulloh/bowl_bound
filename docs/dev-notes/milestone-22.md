# Milestone 22 — Advanced options and coaching follow-ups

## Scope and decision boundary

The canonical scope is [Milestone 22 in the project plan](project-plan.md#22-add-advanced-options-one-at-a-time).
The owner authorized ticket-by-ticket work on 2026-11-01. This note maps each change
to a ticket and its Bowl Bound rule basis; unsupported options remain unavailable
when the ticket still needs a scope decision.

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

### RULE-021 QB Sneak implementation review — 2026-11-01

- Rechecked `paydirt/play_resolver.py:588-670`, `paydirt/game_engine.py:2860-2930`,
  and `tests/test_qb_sneak.py:88-175`. Paydirt separates the rule procedure and
  tests no-defense-dice behavior, but derives outcomes from its own chart tokens
  and recovery rules. Reuse only the isolation and test organization.
- Bowl Bound's `docs/reference/bbrules2007.pdf`, Advanced I-2 (printed p. 14),
  controls: roll offense only against Play 1; green is one yard, white/yellow no
  gain, red a fumble at the line. Defense rolls nothing unless it specifically
  Wild Cards QB Sneak. Advanced II-1 (printed pp. 16–17) makes QB Sneak and Play 1
  mismatched Wild Card guesses and doubles eligible yardage for an incorrect
  Conditional Wild Card.
- Keep color classification at the chart-normalization boundary, use the
  existing fumble procedure, and retain the actual Play 1 lookup in the trace.
  Do not reuse Paydirt's token interpretation, timing, or recovery flow.

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

### Situational defense review — 2026-11-01

- Reviewed Paydirt `paydirt/computer_ai.py:894-1000,1013-1137` for goal-line,
  red-zone, fourth-down and late-lead defense. Adapt situation-first weighting
  and keep it ahead of Hard analysis. Do not copy Paydirt's field-coordinate
  thresholds, NFL kickoff/clock rules, or learned-model ordering that can return
  before its situational defenses. Bowl Bound uses its public `yards_to_goal`,
  enabled kick options, distance, score, period and clock.
- Preserve the engine's six legal formations in every situation; the coaching
  policy changes their weights, not the legal menu or engine resolution. Ship as
  v6 to keep earlier policy streams intact.

### Baseline decision review — 2026-11-01

- Reviewed Paydirt `paydirt/computer_ai.py:1242-1359` for its decision across
  penalty families and kick phases. Adapt explicit, legal-choice preferences;
  do not copy Paydirt's `PlayOutcome` access or its return, field-position, and
  penalty assumptions into Bowl Bound.
- Bowl Bound's coaching observation currently includes legal choice IDs, not
  prepared penalty outcomes. Do not infer acceptance value by parsing labels or
  duplicating engine resolution. Versioned return/spot preferences and stale
  fallback handling can be tested from current facts; penalty strategy may need
  additional engine-provided facts before it can be meaningfully evaluated.

### Human coaching play-test review — 2026-11-01

- Reviewed `paydirt/docs/dev-notes/ai-playtesting.md` and
  `paydirt/docs/ai-auditing.md`. Adapt the before-dice decision review and
  separate coaching choices from outcomes. Do not copy Paydirt's NFL teams,
  calls, thresholds, or balance conclusions; use Bowl Bound's offered engine
  actions and local team charts. Keep historical charts, saves, rosters, and raw
  logs private.

### Advanced II implementation review — 2026-11-01

- Re-read local `docs/reference/bbrules2007.pdf`, printed pp. 16–18 (PDF pp. 19–21),
  for Wild Card, Run/Pass, Nickel Zone, and Red Zone. Paydirt has no matching Bowl
  Bound defensive calls; no NFL behavior was reused.
- The owner selected the W-coded default. W privileges make Wild Card and Run/Pass
  free; other teams may use those calls conditionally. Nickel Zone is unconditional.
  Conditional mistakes double eligible yardage under the printed Rule IX exclusions.
  Play 6 Screen counts as a pass for conditional guesses; QR/QT count as pass plays.
- Implement exact Play 5 Wild Card guesses: run without SOP/BLP, SOP, or BLP. Keep
  dice order and trace only observed rolls. Red Zone is offered only when the line
  of scrimmage is inside the defense's 20.
- Team privileges now pass through catalog loading, game creation, and private saves.
  Legacy M21 saves keep their six-formation profile. Synthetic tests cover the
  decisions, dice use, traces, conditional doubling, API creation, and save replay.
- At the time of this review, coaching still selected among the six chart formations;
  the follow-up is recorded in [AI-021](issues/AI/AI-021.md).

### Advanced II coaching review — 2026-11-01

- Paydirt has no comparable Bowl Bound Advanced II defense calls or W-coded
  eligibility. No Paydirt strategy or NFL rule was reused; the game engine remains
  authoritative for legality and outcomes.
- Policy v9 gives baseline, Easy, Medium, Hard, and chart coaches the complete
  engine-offered defense set. Baseline/Easy/Medium use their existing legal-call
  mixtures. Hard/chart compare calls with isolated Bowl Bound engine runs; the
  evaluator carries the defending team's W-coded free eligibility. Policies v1–v8
  keep their six-formation input and saved selection streams.
- Advanced calls are now recorded in Hard's public call history. The coaching
  audit with public synthetic sample teams covered 32 complete games across two
  seeds, both team arrangements, both CPU sides, and baseline/Easy/Medium/Hard v9.
  Every game finished and verified save continuation; there were no illegal
  selections. All four policy types used Advanced II calls. Two Medium fallback
  selections occurred on engine-adjusted two-point tries, covered by AI-020.
- Synthetic tests cover v8 preservation, all v9 coach types, W-coded/conditional
  eligibility from offense and defense, complete Hard estimates, and versioned
  committed-call history.
- Implemented in `53ca033`; 253 focused Python tests and Ruff lint/format checks
  passed. The ticket is resolved and awaits owner play-test confirmation.

### Power-rating scope decision — 2026-11-01

- The owner stated that power rating is not important to gameplay. Advanced Rule
  VIII's point spread and player-rating system is therefore not part of engine
  eligibility, outcomes, or scoring; imported rating values remain informational.
- Updated the canonical rules profile and plan; closed [RULE-024](issues/RULE/RULE-024.md)
  as wont-fix for gameplay behavior. This documentation-only decision needs no
  behavioral tests.

### Yardage-factor scope decision — 2026-11-01

- Advanced IX (printed pp. 29–31) ties both yardage-factor methods to point spreads,
  rating-derived team factors, and score margin. The owner deferred both methods
  because ratings must not change gameplay. [RULE-023](issues/RULE/RULE-023.md) is
  closed for this milestone; chart yardage, traces, and save semantics stay unchanged.
- This is a scope/documentation decision, so verification uses the issue-tracker
  metadata and generated-index checks rather than artificial behavior tests.

### Fake and block scope decision — 2026-11-01

- The owner deferred Advanced V's fake-kick option, all-out kick rush, and free
  block option as a group. They remain unavailable; the separate Basic VI-8
  onside-kick implementation is unaffected. [RULE-026](issues/RULE/RULE-026.md)
  is closed for this milestone. This documentation-only decision is verified by
  the issue-tracker checks.

### Timing scope decision — 2026-11-01

- The owner chose to retain standard chart timing and defer both Advanced VII
  alternate and hybrid profiles. Period transitions continue to follow play
  timing; no manual runoff choice is restored. [RULE-027](issues/RULE/RULE-027.md)
  is closed for this milestone. No gameplay change was made.

### QB Sneak implementation — 2026-11-01

- Completed [RULE-021](issues/RULE/RULE-021.md) in tested commit `d0fa13b`.
- Followed Advanced Rule I-2 with synthetic test-first coverage. QB Sneak uses
  Play 1 only, handles chart-color outcomes and WCSNEAK/conditional Wild Card
  behavior, and preserves engine state, statistics, and structured traces.
- Verification: 416 targeted Python tests passed; 120 frontend tests and the
  production build passed on Node 24.22.2; Ruff lint/format checks passed.
  Ticket is resolved and awaits owner play-test confirmation.

### Onside kickoff implementation review — 2026-11-01

- Basic VI-8 (printed p. 10) specifies a 12-yard kickoff. The kicking team
  recovers on offensive totals 13–20 inclusive; otherwise the receiving team
  recovers. The ball is dead at recovery with no return roll.
- [RULE-025](issues/RULE/RULE-025.md) exposes this kick type to the engine-assigned
  kicker, including the fixed reciprocal halftime kicker. It does not introduce a
  kick/receive choice. A safety free kick remains ineligible.
- Paydirt's menu separation was reviewed at milestone start, but its rules, dice
  threshold, field position, and timing are not reused. Bowl Bound's Basic VI-8
  governs the implementation.
- Synthetic tests cover both sides of the recovery threshold, field position,
  trace, no-return timing, default AI preference for a normal kick, safety-kick
  exclusion, second-half team assignment, all 216 offensive dice combinations,
  API/CLI/browser controls, and save replay. The first tests failed before the
  action/API support and safety-kick guard were implemented.
- Tested in `9fb974a`: 162 focused Python tests passed, including issue-index
  validation; Ruff checks and formatting passed; 121 frontend tests passed;
  production build passed; all 33 real-engine browser tests passed on synthetic
  teams. Browser emitted the existing `NO_COLOR`/`FORCE_COLOR` warning; no tests
  were skipped. Owner play-test remains needed before closure.

### Situational-play scope decision — 2026-11-01

- The owner approved Razzle-Dazzle (Advanced I-1), elected safety (I-5), and
  intentional delay (I-6(B)). [RULE-022](issues/RULE/RULE-022.md) records this
  scope decision; [RULE-028](issues/RULE/RULE-028.md),
  [RULE-029](issues/RULE/RULE-029.md), and
  [RULE-031](issues/RULE/RULE-031.md) remain separate implementation tickets.
- None is enabled by the scope decision. Each stays unavailable until its own
  rulebook review, synthetic test-first implementation, and verification.

## Ticket coverage

| Milestone 22 change or decision | Ticket |
| --- | --- |
| Advanced II Wild Card, run/pass, nickel-zone, and red-zone defenses | [RULE-019](issues/RULE/RULE-019.md) |
| Defensive guesses specific to SOP/BLP option plays | [RULE-020](issues/RULE/RULE-020.md) |
| QB Sneak, Advanced I-2 | [RULE-021](issues/RULE/RULE-021.md) |
| Situational-play scope decision (closed; three options adopted) | [RULE-022](issues/RULE/RULE-022.md) |
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
| Teach coaching policies to use Advanced II defenses | [AI-021](issues/AI/AI-021.md) |
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

Checked the generated tracker against the Milestone 22 plan: all 39 tickets
assigned to the milestone have individual mappings above. They cover the 14
advanced-rule items, RULE-010 bounds declarations, ten AI findings, two API
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

For AI follow-ups, owner play-test acceptance uses the
[human coaching play-test checklist](ai-playtesting.md): inspect offered actions
and the decision before the dice, then record the outcome separately. Automated
audits and final scores alone do not close coaching tickets.
