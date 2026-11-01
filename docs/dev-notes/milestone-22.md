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

Other work already assigned to Milestone 22 has tickets in the
[issue tracker](issue-tracker.md): AI-011–AI-017 and AI-019; API-002/003;
CLI-044/045; DEV-022/024/028; FLOW-002; RULE-012–015; and UI-036/037.
These are existing coaching, API, CLI, development, flow, rules-correction, and
presentation findings, rather than additional untracked advanced-option features.

### Ticket coverage reconciliation — 2026-11-01

Checked the generated tracker against the Milestone 22 plan and this feature map:
all 37 tickets assigned to Milestone 22 are represented here. They cover the 14
advanced-rule items above, RULE-010 bounds declarations, eight AI findings, two
API findings, two CLI findings, three development findings, one flow finding,
four return-rule findings, and two UI findings. The active kneel-safety work is
tracked by AI-011. AI-018 is assigned to Milestone 23 for full-game coordinator
coverage, so its absence from this milestone is intentional. No untracked M22
change was identified in this reconciliation.

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
