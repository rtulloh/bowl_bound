# Compact clock controls — UI-012

## Reference study and scope

Paydirt’s `paydirt-web/frontend/src/components/Game/PlayModifiers.jsx` uses a
compact modifier strip with None selected initially. `GameControls.tsx` exposes
a Continue step for results. These provide a presentation reference, not Bowl
Bound timing semantics or a runtime dependency. No Paydirt source was copied.

At the user’s request this targeted Milestone 19 usability ticket is addressed
now, after Milestone 15, without claiming the full usability milestone complete
or starting overtime/AI.

## Behavior

- Clock choices render as one compact selector plus Continue rather than a stack
  of five large buttons. Normal engine runoff is preselected; it needs one click.
- All options, descriptions and availability still come from the engine. Selection
  alone does not submit anything. Continue sends the exact selected decision ID.
- Each new clock window resets to normal runoff; a timeout cannot silently persist.
- Pending/disabled controls cannot submit; unavailable reasons remain accessible.
- Empty offense/defense/special/game groups render nothing. The unavailable Snap
  button is omitted during clock management; real football decisions keep their UI.
- Desktop uses one row; narrow screens wrap Continue below the selector.

Automatic runoff was not introduced: it could consume the final seconds before
the player has an opportunity to choose timeout/spike. Making next-snap selection
implicitly commit the prior play would require an engine contract for expiration
and legal next actions; this focused presentation change avoids speculative UI rules.

## Test-first evidence

New component tests failed on the missing compact component; the empty-panel
regression reproduced blank groups. App integration and real-engine browser tests
failed because clock-controls did not exist. After implementation, tests exercise
normal Continue, optional adjustment submission, busy/disabled choices, preserved
football decision panels, and timeout reset across consecutive clock windows.

Existing browser assertions are updated only where the intended controls changed:
clock choice buttons become selector plus Continue, and the disabled Snap is now
absent during clock management. Timing, score and full-regulation assertions remain.

## Verification

- Frontend `npm test`: 40 passed.
- Frontend `npm run build`: passed.
- Frontend `BB_E2E_CHANNEL=chrome npx playwright test`: ten passed, including full
  regulation, timeout/hurry/spike behavior and desktop/mobile compact bounds.
- Compact panel is checked below 85 CSS pixels at desktop and 130 at 390px width,
  with no horizontal overflow of its bounds.

The backend/API/rules are unchanged and the running server was not restarted.
Refreshing loads the rebuilt frontend but this pre-save UI does not restore the
active game after refresh. Existing tabs may finish using their loaded UI.


Cumulative checks:

- `.venv/bin/python -m pytest --cov --cov-branch -q`: 1,326 passed; 91.61%
  branch-aware coverage. No skips or warnings.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: passed (113 files).

Review: no engine/API changes, chart data, new dependencies or Paydirt code
reuse. A local selection is only presentation state; the engine still owns the
clock decision. The original football timing/score assertions remain intact.

## Follow-up: truly optional modifiers

The user clarified that smaller mandatory Continue was not the intended Paydirt
pattern. This follow-up supersedes the selector/Continue description above.

- None is the default radio option beside usable play controls. Normal next snap,
  punt, field goal or kneel commits prior normal timing in the engine; the browser
  makes no separate clock request.
- Clicking a team timeout, Hurry-up or Spike applies it immediately. These are
  one-shot engine decisions; no modifier selection persists to the next window.
- The engine provides `clock_optional` and compact `clock_modifiers` labels. It
  exposes next-play actions only when normal runoff leaves time in this period.
- At expiration boundaries Continue remains explicit, preserving clock-saving
  alternatives. A direct next-snap/kick API request cannot accidentally play in
  the next period: it returns the previous report and newly advanced view without
  using dice. The next snap must be requested separately.
- Hail Mary availability uses the engine’s clock after pending normal timing.
  Invalid next-action requests do not commit the pending time.

Test-first: ten engine regressions failed against the old mandatory-clock API;
five frontend tests failed against mandatory Continue. The old regression expecting
all pending clock windows to reject snaps now asserts optional legal play controls.
Timing, modifier exclusivity, scoring and full-regulation assertions are retained.
Explicit clock decisions remain compatible for non-browser clients.

The local Bowl Bound server remains stopped at the user’s request; Paydirt is not
modified or restarted. Browser checks use only the isolated synthetic test server.

Follow-up validation:

- `.venv/bin/python -m pytest --cov --cov-branch -q`: 1,342 passed, 91.60%
  branch-aware coverage; no skips or warnings.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: passed, 114 files.
- Frontend `npm test`: 40 passed.
- Frontend `npm run build`: passed.
- Frontend `BB_E2E_CHANNEL=chrome npx playwright test`: ten passed, including
  direct normal snaps, optional modifiers, period transitions, complete regulation
  with reconciled scoring, immutable completion and desktop/mobile size bounds.

Review: timing quantities and rules are unchanged. The contract adds explicit
engine authorization for optional continuation. Existing non-clock decisions
remain blocking. Synthetic tests compare explicit and implicit clock continuation
for identical complete views/reports. No private data, new dependencies, or
Paydirt changes are included.
