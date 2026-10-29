# Computer opponent and difficulty

Choose **Human home / computer away** or **Human away / computer home** under
**Control mode** on team setup, before starting or loading. Human home and human
away appear first, with **Two-sided manual play** last. **Human home / computer
away** is the default.
The mode selector is not shown during play; use **Game → New
game** to return to setup and select another mode.

The opening toss has its own screen before the playing screen, following Paydirt’s
setup → toss → play flow. It shows only the matchup, engine status, winner and
legal kick/receive choices, with recorded dice in a collapsed audit. A one-second
coin flip animates first, then reveals the engine’s recorded winner and choices.
Computer-owned decisions wait for that reveal before advancing; reduced-motion
preferences skip both animation and delay. No additional roll or heads/tails
choice is generated in the browser. The field,
scoreboard and play modifiers appear after the engine settles the opening choice.
Computer-owned toss decisions still advance automatically; their controls are not
exposed. Failed choices stay on the toss screen, and unresolved opening saves
return there. The Game menu remains available. Kickoff controls appear above
the field on the playing screen, rather than below the audit and modifiers.

Only your offensive or defensive selection controls appear. The computer selects
its simultaneous call on the server without receiving your selected call; no
preview response includes that computer call. Choosing your play immediately resolves
both calls and may reveal them in the result/history. Pending football decisions
are explicitly assigned to a home/away side, not inferred from team names.

Computer-only decisions and kicks advance automatically, one engine command per
request. Human calls, kick actions and required decisions always wait for you.
There is no Pause/Resume or Snap button. In manual play, the second fresh selection
submits both calls; both clear after submission, including failed requests. Required
football decisions still block play. Errors stop automatic advancement and show
**Retry computer** only when needed. A successful save does not silently retry a
failed computer turn. Save/load never overlap gameplay requests. Loads keep the
browser mode selected on setup (human home/computer away by default), not a mode stored in
the save; computer-only actions then advance normally. Final games stop. A
12-consecutive-action safety guard stops unexpected automatic loops and offers
retry; it does not cap game length or overtime rounds.

Open the compact header **Game** menu for **New game**, **Save game** and **Load
saved game**. It overlays rather than pushing the play area down; Escape closes
it and returns focus to the menu summary. Offered special/game actions share your
play panel: P/Punt, F/FG, K/Kneel, KO/Kickoff and HM/Hail Mary. The
prominent number/letter sits above its name; full engine labels remain available
to assistive technology and in tooltips. Unsupported Q/Sneak is not added.

Defense buttons keep A–F above their engine-supplied names: **Standard**,
**Short yardage (gaps)**, **Short yardage (wide)**, **Pass prevent (short)**,
**Pass prevent (long)** and **Blitz**. These are the supported Bowl Bound/Mays
formation names, not an inferred Paydirt mapping. Results and chart traces retain
the stable Formation A–F identifiers; naming does not alter chart lookups or dice.
Legacy save digests canonicalize only defensive selector wording back to those
identifiers, preserving their original gameplay/trace checks.

**Timeout** and **Spike** sit beside **Hurry-up mode** in the visible play-modifier
row; they are one-shot engine decisions, not modes. The row wraps on narrow
screens. Unavailable actions stay disabled. Hurry-up/no-huddle is the only
persistent mode. **OOB** and **IB** also appear, but remain disabled pending
[engine implementation](dev-notes/issues/RULE/RULE-010.md): they must be mutually
exclusive declarations for one play, reset afterward, and apply the documented
five-yard cost and exceptions. They are not clock-only overrides. Chart-generated
OOB outcomes already follow the engine timing profile.

## Policy and fairness

The engine owns legality, dice, results and rules. Choose **Easy (0.3)**,
**Medium (0.5, default)** or **Hard (0.7)** at browser setup or with CLI `-d`.
The numbers are coaching aggression settings, not dice multipliers.

- Easy uses conservative situational mixtures, independent of chart strength.
- Medium uses balanced mixtures with a coarse run/pass strength tilt on first
  and second down; it does not rank individual chart plays.
- Hard evaluates individual legal plays through 32 isolated real-engine samples,
  blends smoothed committed opponent-call frequencies with recent-call variety,
  and retains exploration. Hypothetical dice never consume live gameplay dice.
  At most 128 analysis situations are cached. Failed candidate analysis falls
  back for the entire comparison and is recorded in the committed diagnostic.

Evaluator diagnostics retain the legacy name `turnover_rate`, but it is a
possession-loss proxy, **not** football turnover statistics: punts, kickoffs and
turnovers on downs can count. Declared chart/evaluation/decision failures
invalidate the whole comparison; unexpected programming errors propagate rather
than silently triggering fallback. Hail Mary analysis uses the same 8/A engine
call and hurry flag as regulation, without drawing an unused opposing call.
Hard values an action as points scored plus the change in a field-position
preference. For the possessing team that preference is
`-1 + 5 * (yards_from_own_goal / 100)^2 - 0.2 * (down - 1) - 0.03 * distance`;
for the other team it is negated. A settled scoring action has no remaining
field preference. This keeps a touchdown worth more than an unscored goal-line
opportunity and values a punt at the actual receiving spot rather than charging
a fixed possession-loss premium. The existing late lead/tie bonus still applies.
These are explicit heuristic units, **not calibrated expected points**. The
legacy `chart-v1` policy keeps its original utility and selection streams.

Try-phase observations are explicit: Hard evaluates conversion and overtime
try-only snaps through the engine’s two-point phase. Success is worth two points,
failure ends the try, and neither retains a scrimmage field-position value.
Ordinary overtime series remain scrimmage, without hypothetical kickoffs.
Policies receive an immutable public-observation allowlist: side, possession,
down/distance, spot, phase, quarter/time, score difference, completed-play count, overtime,
hurry status and offered action/decision IDs. Medium/Hard can analyze supplied
charts, but receive no live engine, future dice, gameplay seed/RNG or concealed
current opponent selection. Hard learns only committed calls, not previews.
Every suggestion is constrained to enabled engine IDs; an empty legal set fails
clearly. Conversions, tosses, kick receptions, turnovers, penalties and clock
choices remain engine-constrained. These are bounded heuristics, not an optimal
coach, exact win probabilities, or a guarantee of increasing win rate.

Easy CLI assistance is [documented separately](cli.md#easy-only-coaching-helper).
There is no Medium/Hard helper or browser helper panel.

Coaching uses a separate private seed and deterministic local streams keyed by
public observations and role. Previews/retries do not consume dice or future calls.
The private save contains the versioned policy and seed. Hard history is rebuilt
from successful committed snap commands during replay, with no sidecar. The
engine command is journaled before derived coaching history is updated. If an
unexpected history-update error propagates after a snap, the snap has already
completed: save/reload reconstructs its history from the journal; do not blindly
resubmit that snap. Compatible baseline and draft chart-v1 saves retain their
original policies, not a new tier; older engine-profile saves are rejected rather
than migrated (see [save compatibility](saves.md#schema-and-compatibility)).
This makes future coaching reproducible as well
as future gameplay dice. The displayed gameplay seed alone reproduces manual dice,
not a newly randomized computer coach. Saves are private local documents, not a
competitive anti-cheat boundary.

Paydirt supplied the mixture/fallback design, not its NFL rules or coupled AI class;
see [attribution](ATTRIBUTION.md). No Paydirt runtime dependency was added.

## API

`POST /api/games` accepts `difficulty: "easy" | "medium" | "hard"`; omitted means
Medium. Alternatively, explicit `coach_policy` accepts `baseline`, `chart-v1`,
`easy-v1`, `medium-v1` or `hard-v1`; it cannot be combined with `difficulty`.
`baseline` and `chart-v1` are compatibility policies, not additional player-facing
difficulty levels. New/load/get responses report `coach_policy`; loading restores
the saved version, irrespective of setup selections.

`POST /api/games?human_side=home` and `GET /api/games/{id}?human_side=home`
(optionally `away`) return the normal engine view plus `turn`: human identity/role,
automatic flag, status, human-only actions, game actions and pending choice. No
private computer plan is serialized.

`POST /api/games/{id}/coach` takes `{human_side, human_call?}`. Omit/null
`human_call` only for an automatic computer action. Otherwise send just your offered
offensive ID or defensive ID; never both calls. Planning happens before the human
call is considered. Planning, validation, the one engine command and its matching
view/next turn all share the game lock. Responses contain `{report, view, turn}`.

For human kicks, decisions and game actions, append `?human_side=home` (or `away`)
to the usual endpoints. These validate against the human-only controls and return
the next turn atomically. Existing manual endpoints stay compatible; this local
unauthenticated API is not multiplayer access control. Invalid input does not
consume dice or record a command.

## Dice presentation

Observed trace rolls include engine-supplied `dice_label` and `dice` entries with
`role`, `label`, `color`, and `face`, alongside the original `faces` and authoritative
`total`. Black, White 1, White 2, Red and Green have visible text and accessible
labels; color is not the only distinction. Offensive total is not the direct sum
of displayed faces. The UI never recalculates it. Opening/overtime `toss_dice` and
`overtime_toss_dice` describe only already-recorded rolls. The compact result and
expandable toss/chart audits never generate, reconstruct or reorder rolls.

### Versioned behavior profiles

`bowl_bound/coaching_profiles.py` groups immutable preference parameters for
`baseline-v1`, `chart-v1`, `easy-v1`, `medium-v1` and `hard-v1`. The persisted
baseline save identifier remains `baseline`. Profiles name sample/cache/history
bounds, mixture temperature/exploration, aggression, late-game thresholds and
utility coefficients. These are coaching preferences, not football rules,
configurable difficulty odds or calibrated expected points. Existing profile
values and RNG inputs are frozen; preference changes require a new policy version.

Audit JSON includes `behavior_profile` and `audit_profile` for each game. The
separate `coaching-audit-v1` profile names replay and advisory concentration
thresholds; it never constrains legal play usage.

### Shared policy interface and exact-analysis foundation

All coaches declare an analysis-fallback flag and a committed-call hook; baseline
and legacy chart policies deliberately learn nothing. Saves journal a successful
engine command before notifying that hook. The chart and difficulty coaches share
candidate enumeration, bounded weighted-model caching and mixture selection,
with explicit hooks retaining their different utility, public-history preferences
and selection RNG namespaces. `observe_game` is the public allowlisted observation
builder; the old private name remains a compatibility alias only.

`coaching_probabilities.analyze_play` is an intentional **library-only exact
chart-analysis foundation**, exercised with synthetic tests. It is not called by
a current policy or presented as complete-game odds. Hard instead uses the bounded
real-engine sampled evaluator so pending penalties/returns can settle. The exact
library keeps failed/unexplored mass explicit rather than pretending those
branches are known football outcomes.
