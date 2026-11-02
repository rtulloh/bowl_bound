# Milestone 23 — Regression-gate follow-ups

## Scope

Resolve the public-safe findings in the 2026-11-01 review of milestones 22 and
32. Each ticket remains independently test-first, committed after focused checks,
and resolved only after tested implementation. Owner play-testing is required
before gameplay or UI tickets are closed.

## Paydirt consultation — 2026-11-01

Reviewed the local Paydirt repository before beginning the follow-up work:

- `tests/run_full_season.py:33-117` validates final state, period scores, score
  ledgers, and conversion periods independently. Bowl Bound will adapt this audit
  discipline for DEV-054 through DEV-056, while retaining its college rules and
  local-only data policy.
- `tests/test_onside_kick.py:44-128` exercises both recovery boundaries and ball
  coordinates. Its boundary-test organization is useful for Bowl Bound special
  teams, but its NFL engine behavior and chart data are not reused.
- `tests/test_save_game.py:1-130` compares restored state and continuation. Bowl
  Bound instead verifies command-and-dice replay with its own synthetic charts;
  Paydirt save format and team data are not reused.

No Paydirt runtime dependency, rules implementation, private data, or schedule
logic is added.

## Paydirt consultation — AI-025 and CLI-050 follow-up, 2026-11-01

Reviewed `/Users/rtulloh/work/paydirt/paydirt/computer_ai.py:311-365`, which documents
historical NFL fourth-down patterns, including mixed kick/go choices in opponent
territory. Bowl Bound does not adopt its NFL rates, field-goal distance, teams, or
selection logic: the owner-directed Bowl Bound policy is an explicit conservative
early fourth-and-long guard. Paydirt's generic pending-choice wording was also
reviewed but not reused; Bowl Bound's engine already owns the pending decision and
therefore supplies its exact terminal status.

## Ticket work

### RULE-033 — 2026-11-01

- Synthetic tests first reproduced wrong numbered Wild Cards stopping Option runs.
- The resolver now requires both Play 5 and the exact Option branch before the
  Wild Card stop applies. The focused Advanced II, resolution, and coaching
  evaluation regression set passed before commit.

### RULE-034 — 2026-11-01

- Synthetic tests first showed that an exact WCRZDZ call recorded an incomplete
  pass without applying the normal state transition.
- The no-dice result now uses the ordinary prepared-play path. This preserves the
  required incomplete timing, statistics, turnover-on-downs behavior, regulation
  integration, and save replay without duplicating transition logic.

### RULE-035 — 2026-11-01

- Synthetic penalty-reroll tests first reproduced stale conditional-defense
  doubling for QR, QT, Sprint Out, and Boot-leg outcomes. They also cover a
  PASS guess changing from incorrect before the reroll to correct afterward,
  plus W-marked free defenders.
- The shared conditional-defense predicate now evaluates the rerolled resolved
  play and cell. Penalty preparation and the Razzle-Dazzle decision path retain
  the Advanced II call metadata so that they can make that assessment without
  guessing from a stale resolution.

### RULE-036 — 2026-11-01

- A synthetic yellow Play 1 box containing a PEN token first demonstrated that
  the QB Sneak correctly produced a zero-yard play but incorrectly charged
  penalty timing because its color-evidence trace was mistaken for execution.
- Timing now excludes chart-token penalties for QB Sneak. The original lookup
  remains in the structured trace as provenance; ordinary penalties and return
  penalties keep their existing timing behavior.

### RULE-037 — 2026-11-01

- The previous QB Sneak test incorrectly expected a conditional, mismatched
  Wild Card to double a green Sneak. The local rulebook's Advanced IX exemption
  applies to the Advanced II conditional-defense reference.
- Conditional doubling now explicitly excludes QB Sneak. Synthetic fourth-and-
  two tests cover both conditional and W-marked defenders, ensuring a green
  Sneak does not become a first down through an inapplicable double.

### RULE-038 — 2026-11-01

- Synthetic kickoff and punt returns first reproduced a touchback when a return
  crossed the receiving team's end line. Recovered-ball returns use the same
  tested endpoint path.
- Return handling now distinguishes remaining in the end zone (touchback) from
  reaching or crossing the end line (safety), using the shared END_LINE fact.

### API-005 — 2026-11-01

- Coached API contract tests first reproduced FastAPI rejecting the Razzle-Dazzle
  and its exact Wild Card defense even though the engine offered each action.
- The request contract now permits both offered identifiers, and tests submit
  them through real coached games for either human side.

### AI-022 — 2026-11-01

- Synthetic pending-decision tests first showed the decline preview using twelve
  yards while execution applied the out-of-bounds declaration's five-yard cost.
  Conditional defense doubling was likewise absent from the preview.
- A shared pure live-resolution adjustment now feeds both execution and decline
  projections. Penalty acceptance retains the unmodified prepared result, since
  the declaration applies only when the ordinary play is declined.

### DEV-053 — 2026-11-01

- Synthetic M21/post-M27 digests first reproduced rejected fresh-drive and
  ordinary clock-choice saves. The old profile had no M22 actions but had
  already removed the manual runoff control.
- Save validation now includes that precise M21 projection in addition to the
  pre-M27 projection. It accepts only the historical semantic menu and never
  restores a runoff action into the loaded game.

### AI-023 — 2026-11-01

- A synthetic legacy-v8 regression first showed new Razzle-Dazzle actions
  changing a frozen selection stream, despite the older policy being restricted
  to standard defenses.
- Legacy policy observations now remove all M22-only action families before
  selection and hashing: QB Sneak/Razzle-Dazzle, onside kickoff, bounds/elected
  safety, intentional delay, and Advanced II metadata. V9 receives the complete
  engine menu unchanged.

### AI-024 — 2026-11-01

- Synthetic last-snap tests first reproduced Easy, Medium, and Hard selecting
  Hail Mary over a guaranteed winning field goal for either possession side.
- The late-play shortcut now checks a one- or two-point deficit against the
  real field-goal evaluator first. It selects the kick only when every sampled
  chart result scores three points; Hail Mary remains available when a kick is
  not guaranteed or cannot produce a lead.

### API-006 — 2026-11-01

- A manual request for Red Zone at own 35 first reproduced an unhandled
  unavailable-formation ValueError and HTTP 500.
- Formation parsing now uses the engine's decision-validation exception. The
  existing API mapping returns HTTP 422 without consuming dice or changing the
  game view.

### DEV-054 — 2026-11-01

- A synthetic boundary regression first demonstrated that the runner had no
  post-action period attribution and therefore used the stale pre-action
  quarter for a score delta.
- Score deltas now use the post-action engine view, which correctly attributes
  plays that implicitly advance from Q1/Q3 into Q2/Q4 before scoring.

### DEV-055 — 2026-11-01

- A synthetic W-marked constructor regression first showed the runner had no
  metadata path and therefore created only conditional defenses.
- Audit-game construction now passes validated defense-chart markers exactly as
  CLI/API construction does. Private records state both baseline coaching
  policies, Advanced II status, and each side's marker set, so their scope is
  inspectable without exposing team charts.

### DEV-056 — 2026-11-01

- Adversarial audit fixtures first showed both a repeated clock interval and a
  disconnected report field state being accepted.
- The local validator now reconciles chronological regulation clock continuity,
  report-associated timing entries, and contiguous public field facts while
  allowing explicit zero-time boundary entries and post-regulation timing.

### DEV-057 — 2026-11-01

- The maintained coaching reference was still pre-revision and described a
  mutable human-side assumption, while the Priority Chart still deferred
  Advanced II behavior that is now implemented.
- Documentation now gives the concise current API contract and directs detailed
  Advanced II exceptions to the canonical rules profile. The current web-demo
  contract was checked for consistency.

### AI-025 and CLI-050 — 2026-11-01

- `66de34b` introduces versioned v10 Easy/Medium/Hard policies. In non-overtime
  Q1–Q3, a tied-or-leading offense punts on fourth-and-long outside the engine-offered
  field-goal range; late and deficit situations retain normal selection. Synthetic
  regressions preserve v9's previous stream and cover the reported fourth-and-13 and
  penalty-replayed fourth-and-18 situations.
- A pending ordinary penalty now names its required penalty decision rather than
  displaying the stale scrimmage-call status. Other pending results retain a generic
  pending-result status; the valid accepted-offense-penalty fourth-down replay is
  unchanged.
- Both tickets are resolved, not closed, pending owner play-test confirmation.

## Acceptance — 2026-11-01

All sixteen findings from the milestone 23 review inventory are resolved with
public-safe synthetic regression evidence. They remain resolved rather than
closed until owner play-testing confirms the observed gameplay/UI behavior.

- Full Python gate: `/tmp/bowl-bound-py313/bin/python -m pytest --cov
  --cov-report=term-missing -q` — 3,078 passed in 641.13 seconds; 92.80% branch
  coverage (75% required).
- Repository checks: `/tmp/bowl-bound-py313/bin/python -m ruff check .`, Ruff
  format check (487 files), `/tmp/bowl-bound-py313/bin/python -m pip check`, and
  `git diff --check` passed.
- Frontend on Node 24.22.1: `npm test` — 122 passed across 16 files; `npm run
  build` passed; `npm audit --omit=dev` reported zero vulnerabilities.
- Real-engine browser gate: an isolated `/private/tmp/bowl-bound-m23-e2e.*`
  synthetic-team directory with `npm run test:e2e` completed all 33 Playwright
  cases; its recorded status is passed with no failed tests.

No private charts, PDFs, historical rosters, saves, or local audit logs were
added to the repository.
