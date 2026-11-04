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
play panel: P/Punt, F/FG, K/Kneel, KO/Kickoff, O/Onside kickoff when offered,
and HM/Hail Mary. The
prominent number/letter sits above its name; full engine labels remain available
to assistive technology and in tooltips. Elect a safety appears as ES when the
engine offers it. QB Sneak appears as Q when the engine
offers it. The computer considers QB Sneak only with two or fewer yards to gain;
it does not use it as a long-yardage passing-down call.

Defense buttons keep A–F above their engine-supplied names: **Standard**,
**Short yardage (gaps)**, **Short yardage (wide)**, **Pass prevent (short)**,
**Pass prevent (long)** and **Blitz**. These are the supported Bowl Bound/Mays
formation names, not an inferred Paydirt mapping. Results and chart traces retain
the stable Formation A–F identifiers; naming does not alter chart lookups or dice.
Legacy save digests canonicalize only defensive selector wording back to those
identifiers, preserving their original gameplay/trace checks.

**Timeout**, **Spike**, and **Intentional delay** are one-shot engine decisions.
Existing post-play clock choices apply to the completed play. Separately, each
eligible side may arm its own timeout before the next play, including immediately
after kickoff. Arming/canceling changes no clock, dice or budget. The next
completed legal play consumes it, takes 10 seconds, and clears it. One side-owned
modifier may be armed at a time; the other side cannot overwrite it. Mandatory
play continuations retain it until completion. No persistent Spike button exists. **OOB** and **IB** appear when offered as
mutually exclusive declarations for the next scrimmage play. They clear after
that play, and the engine applies the five-yard cost and rulebook exceptions.
They are not clock-only overrides. Chart-generated OOB outcomes already follow
the engine timing profile. Hurry-up/no-huddle is the only persistent mode.

## Policy and fairness

The engine owns legality, dice, results and rules. Choose **Easy (0.3)**,
**Medium (0.5, default)** or **Hard (0.7)** at browser setup or with CLI `-d`.
The numbers are coaching aggression settings, not dice multipliers.

- Easy uses conservative ordinary play-call mixtures, independent of chart strength.
- Medium uses balanced mixtures with a coarse run/pass strength tilt on first
  and second down; its ordinary play-call mixture does not rank individual chart plays.
- In v4, Easy/Medium continuously adjust pass/run weights from late-half
  score margin and time; runs retain positive weight, and protecting a lead
  tilts the mix toward runs. Long-down mixtures also vary by tier aggression.
- Hard evaluates individual legal plays through 32 isolated real-engine samples,
  blends smoothed committed opponent-call frequencies with recent-call variety,
  and retains exploration. Hypothetical dice never consume live gameplay dice.
  At most 128 ordinary play-call analysis situations are cached; pending RZDZ
  comparisons have a separate bounded cache. Failed candidate analysis falls
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
A penalty that requires a new two-point attempt can leave an ordinary one-action
play-call estimate incomplete. That comparison uses its flagged legal fallback;
it does not invent a completed zero/two-point result or append another snap.
These are explicit heuristic units, **not calibrated expected points**. The
legacy `chart-v1` policy keeps its original utility and selection streams.

Try-phase observations are explicit: Hard evaluates conversion and overtime
try-only snaps through the engine’s two-point phase. Success is worth two points,
failure ends the try, and neither retains a scrimmage field-position value.
Ordinary overtime series remain scrimmage, without hypothetical kickoffs.
Policies receive an immutable public-observation allowlist: side, possession,
down/distance, spot, phase, quarter/time, score difference, completed-play count,
overtime, hurry status, the engine's safe-kneel query and offered action/decision
IDs. Coaches may read both supplied immutable board charts, including possible
supplemental rows. They receive no live engine, future dice, gameplay seed/RNG or
concealed current opponent selection. Easy/Medium retain the ordinary play-call
mixtures described above; the forced Razzle-Dazzle choice below has its own
comparison policy. Hard learns only committed calls, not previews.
Every suggestion is constrained to enabled engine IDs; an empty legal set fails
clearly. The web API returns HTTP 409 with a stable message when it cannot prepare
a legal coached turn. Conversions, tosses, kick receptions, turnovers, penalties
and clock choices remain engine-constrained. These are bounded heuristics, not an optimal
coach, exact win probabilities, or a guarantee of increasing win rate.

Easy CLI assistance is [documented separately](cli.md#easy-only-coaching-helper).
The chart-ranking helper remains Easy-only in the CLI. Separately, all normal
difficulties show read-only fourth-down guidance in the browser and CLI, using
the same public policy as that difficulty’s CPU. The engine supplies the
recommendation, public field-goal distance and wording. It reads no kick chart,
selects no play, consumes no dice and changes no history. It appears only for
the offense on an eligible fourth down with an offered kick; mandatory choices,
conversions, overtime and finished games are excluded. Explicit development
policies do not claim this shared normal-play guidance. Team/season range
settings remain future work (AI-031).

Coaching uses a separate private seed and deterministic local streams keyed by
public observations and role. Previews/retries do not consume dice or future calls.
The private save contains the selected difficulty and seed. Hard history is rebuilt
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
Medium. A loaded game uses the current coach for its saved difficulty, so AI fixes
are immediately available to play testing. The API reports `difficulty`; internal
baseline/chart policies are development audit choices, not player-facing levels.

`POST /api/games?human_side=home` and `GET /api/games/{id}?human_side=home`
(optionally `away`) return the normal engine view plus `turn`: human identity/role,
automatic flag, status, human-only actions, game actions and pending choice. No
private computer plan is serialized.

For prepared penalty decisions, the engine may include `decision_outcomes` beside
the offered choices. Each entry identifies one choice and its deterministic
post-choice field position, score, turnover possession, or an `unresolved` result
when applying the choice still needs dice. Coaches use only enabled choices and
these engine projections; they do not parse choice labels or resolve penalties.

`POST /api/games/{id}/coach` takes
`{human_side, expected_revision, human_call?}`. Use the `revision` from the
create/get/previous command response as `expected_revision`; a stale or duplicate
request receives HTTP 409 and changes nothing. The selected human side is bound
when the game is created or loaded and cannot be changed. Omit/null `human_call`
only for an automatic computer action. Otherwise send just one offered offensive
or defensive ID, never both. Planning, validation, the one engine command and its
matching view/next turn share the game lock. Responses contain
`{report, view, turn, revision}`.

For human kicks, decisions and game actions, append the same bound
`?human_side=home` (or `away`) to the usual endpoints. These validate against the
human-only controls and return the next turn atomically. Existing manual endpoints
stay compatible; this local unauthenticated API is not multiplayer access control.
Invalid input does not consume dice or record a command.

## Dice presentation

Observed trace rolls include engine-supplied `dice_label` and `dice` entries with
`role`, `label`, `color`, and `face`, alongside the original `faces` and authoritative
`total`. Black, White 1, White 2, Red and Green have visible text and accessible
labels; color is not the only distinction. Offensive total is not the direct sum
of displayed faces. The UI never recalculates it. Opening/overtime `toss_dice` and
`overtime_toss_dice` describe only already-recorded rolls. The compact result and
expandable toss/chart audits never generate, reconstruct or reorder rolls.

### Versioned behavior profiles

`bowl_bound/coaching_profiles.py` groups immutable preference parameters for the
versioned policies. The persisted legacy baseline identifier remains `baseline`.
Profiles name sample/cache/history bounds, mixture temperature/exploration,
aggression, late-game thresholds and utility coefficients. These are coaching
preferences, not football rules, configurable difficulty odds or calibrated
expected points. Version 2 consults the engine's `can_kneel_out_game` query before
choosing a kneel; v1 keeps its original selection stream and heuristic. New games
use the current implementation, while older difficulty saves are upgraded to their
named tier. Version 3 adds
chart-backed fourth-down and late-half choices, score-aware fourth-quarter
conversion preferences, and an offered last-snap Hail Mary for a trailing team.
Its field-goal options come from the engine and team chart, not a fixed distance
threshold. Version 4 adds bounded score/time pressure to Easy/Medium pass/run
mixtures and applies the same directional bias to chart-scored choices; long-down
mixtures vary by tier aggression. Its seven-point pressure unit is a coaching
scale, not a rules threshold or an expected score. Earlier policies keep their
recorded behavior. Version 5 gives Hard a decaying repetition discount within
the same public situation buckets used by coaching audits. A 0.30 floor keeps a
repeated call available; history from another situation does not reduce its
weight directly. Other policy versions retain their prior selection behavior.
Version 6 adds Easy/Medium/Hard situational defensive preferences for goal-line,
likely fourth-down kicks, and protecting a large late lead. It adjusts weights
without removing any of the six formations from the engine's legal menu. Hard's
chart analysis uses the same preferences, so it cannot override those guards.
Advanced II calls remain excluded from older policy versions; version 9 adds all
engine-offered calls while preserving the older selection streams.
Version 7 returns kicks unless a large late lead favors a fair catch or
touchback, selects the receiving team's guaranteed spot on a kickoff out of
bounds, and clears stale analysis-fallback state before a decision. Version 8
uses deterministic engine-projected penalty outcomes to compare decline and
accepted-enforcement choices, including fourth-down turnovers and scoring
results; when an outcome needs future dice, it retains the earlier safe default.
Version 9 includes every engine-offered Advanced II defense. Baseline, Easy and
Medium mix legal calls using their existing selection preferences. Hard and chart
policies compare calls through isolated engine simulations, including conditional
yardage doubling and free W-coded access. Earlier policy versions keep their
recorded six-formation behavior.
Version 10 replaces current fourth-down kick selection with a shared public policy:
attempt distance is yards to the goal line plus 17. The coach kicks through 35 yards;
at 36–47 it goes for fourth-and-one at Medium/Hard and otherwise kicks; at 48–50 it
kicks; at 51–55 Medium/Hard kick and Easy punts; beyond 55 it punts unless
Medium/Hard face fourth-and-one. Late in the fourth while trailing, it kicks only if
three points can tie or win and the attempt is within 55 yards; otherwise it goes for
it. Difficulty supplies only the public aggression choice (Easy .3, Medium .5, Hard
.7). The same rule can be shown to players: the AI does not inspect a team's kick
chart to decide whether to attempt a field goal. The engine still uses the selected
team's chart to resolve the actual kick. Future public season/team range adjustments
are tracked in AI-031.

`coaching.public_fourth_down_call` is the engine's single public policy entry
point. It takes only the allowlisted observation, declared aggression, and the
approved late-game window. The current CPU delegates to it. Its public-only inputs also support player
guidance with the same decision basis. `field_goal_attempt_distance` supplies the conventional
public distance. These functions do not evaluate kick charts or consume dice.

Audit JSON includes `behavior_profile` and `audit_profile` for each game. The
separate `coaching-audit-v1` profile names replay and advisory concentration
thresholds; it never constrains legal play usage.

### Razzle-Dazzle result choices

Version 11 compares all engine-offered Razzle-Dazzle cells for Easy, Medium,
Hard and development chart coaches. The offense maximizes and the defense
minimizes the existing Hard field/score utility described above; exact ties keep
legal menu order. This replaces the former first-legal-cell fallback. It does not
change ordinary Easy/Medium call mixtures or fourth-down guidance.

Only the already revealed comparison dice and declared defensive formation are
fixed. The evaluator uses isolated engine rollouts with ordinary physical-face
dice distributions. All candidates share independent hypothetical streams derived
from the public observation, never a gameplay or coaching seed. Each gets equal
samples, capped at 32; a comparison uses at most 288 total rollouts (16 each for
18 choices). Normal priority, supplemental B/QR/QT/Option branches, penalties and
turnover/recovery procedures remain engine rules. Follow-up decisions use frozen
v10 legal preferences. Evaluation stops after that action; it does not simulate a
later conversion, kickoff or another snap. A called two-point try retains its
actual 0/2-point phase and has no residual scrimmage field preference. A fumble's
sampled recovery is not a guaranteed possession change; actual receiving spot
can make a fourth-down loss preferable to an interception. No token always wins.

Internal diagnostics report sample count, failed samples, estimated mean and
standard error. These are estimates, not exact distributions or confidence in the
underlying heuristic; standard error measures only sample variation, and is
unknown with one sample. Any failed rollout invalidates the whole comparison,
without dropping failures or renormalizing successes. The legal fallback is
flagged. At most 128 comparisons are cached. The exhaustive rational enumerator
remains an explicit library/test oracle and is not used for normal requests.

QT, B, QR and Option remain gambles. A probability-weighted estimate from the
available charts does **not** reveal which future roll or result will occur.
The computer commits its choice before the fresh gameplay roll. Pending labels
retain the unresolved chart symbol; hypothetical utility values are private
coaching diagnostics, never projected actual results in the game view. Repeated
previews consume no gameplay dice, commands or call history, and changing an
unobserved future dice stream cannot change the same observed choice.

Frozen v1–v10 policies retain their former decisions and streams; normal
difficulty loads use the current revision. Ordinary 32-sample play-call analysis
retains its earlier one-action continuation defaults; this forced-choice
comparison is not a recursive search for optimal future play.

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
a current policy or presented as complete-game odds. Ordinary Hard play-call
comparisons use the bounded real-engine sampled evaluator so pending penalties/
returns can settle; v11 forced RZDZ choices use the separate shared rollout budget. The exact
library keeps failed/unexplored mass explicit rather than pretending those
branches are known football outcomes.


### Version 12 late-half clock selection

Current Easy/Medium/Hard preserve an existing public-policy fourth-down field
goal when a pending completed play's normal timing would expire Q2 or Q4 and
the CPU is tied or trailing. The engine supplies `normal_timing_ends_period`.
The separate clock method chooses the CPU's offered own timeout when its
10-second charge leaves time for the kick, otherwise offered hurry; it then
re-plans the kick from the engine's actual clock. A useless timeout, opponent
option or unavailable action is never manufactured. Q1/Q3, a lead, and public
punt/go choices get no new urgency rule. Running calls and ordinary mixtures
are unchanged in strategy; this is a bounded sequencing correction.

Versions 1–11 keep their explicit decision and seeded-analysis contracts. As
required by AI-026, ordinary saved difficulties load through the current tier;
only `preserve_development_policy=True` retains a development revision for
audits. The clock fact is separate from `CoachObservation`, so it adds no
observation fields or historical analysis-seed inputs.


### Version 13 Razzle-Dazzle surprise preference

Normal Easy/Medium/Hard treat RZDZ as a separate surprise call, rather than
another ordinary pass. Its initial probability is 3% when a scrimmage mixture
is selected. Divide that by one plus the team's committed RZDZ calls, then by
one plus eight times its recent-use score. That score sums `0.5 ** age` over
RZDZ calls in the tier's recent own-call history. Previewing a call changes
neither count nor history. There is no forced minimum or hard maximum; the
owner's normal full-game target is roughly one to three surprise calls per team.

The same small preference applies to ordinary mixtures, late-half/Hard analysis
and analysis fallbacks. Initial ordinary-action rollouts rank the other calls;
RZDZ is not allowed to dominate that mixture through an estimated initial-call
utility. Its subsequent revealed-result choice still uses v11's bounded real
engine comparison and remains a gamble wherever further rolls are required.
Public fourth-down kicks, kneeling and last-snap priorities still take precedence.
Legal human calls and all engine outcomes, dice and rules remain unchanged.

Explicit v1–12 policies retain their previous choices and mixtures. Normal named
difficulties upgrade to v13 on ordinary load under AI-026; an explicit development
preservation load keeps its recorded revision. The new preference uses only
committed own calls and public observations, never the hidden human call or
future gameplay stream. Frequency audits report complete-game counts and repeat
runs; the target is a coaching preference, not an asserted historical frequency.


The complete-game audit retains `razzle_outcomes` and `razzle_statistics` counters
from finalized engine reports for the audited CPU side. The former records engine
outcome IDs; the latter preserves credited statistical kinds, including excluded
penalties. They do not label every defensive recovery as an interception or turn
a penalty-excluded call into a credited play. No commentary parsing is involved.
