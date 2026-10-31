# Initial Bowl Bound Rules Profile

Status: **Milestone 2 rules specification, version 1**.
This profile defines planned behavior, not implemented gameplay. User-selected policies
are recorded below; additional conflict resolutions are explicit project defaults adopted
to complete the initial specification, rather than attributed to user answers.

## Sources and precedence

The local reference is `docs/reference/bbrules2007.pdf` (42 PDF pages).
SHA-256: `599b1366b77fb5c17e01e510f0e0e78b92aba505aa57880bb95de7f024a7e690`.
The PDF remains ignored; redistribution rights have not been established. Page references
below use printed page numbers (printed page 1 is PDF page 4).

Explicit project decisions take precedence over conflicting rulebook guidance. Historical
college rules require dated sources, not Paydirt NFL behavior or a moving reference to
“current” college rules. Preserve source evidence when interpreting chart tokens.

## Selected policies

| Topic | Initial policy | Source / implementation target |
| --- | --- | --- |
| Variable yardage | Full-feature DS, X, T1, T2, T3 method; actual supplemental rolls appear in traces | Basic VI-3, p. 6; resolution milestones |
| Penalty yardage | Chart mode: preserve printed penalties; resolve S/R with the full-feature method, not Advanced conversion of every penalty | Basic VI-4(B), pp. 7–8; Milestone 11; Chart mode is the project default |
| Timing | Standard chart timing; shortest applicable duration; late-half out-of-bounds windows | Timing Chart, p. 34; Milestone 15 |
| Historical overtime | Home season selects the major-college profile in the historical table below | Project decision; Milestone 16 |
| Kickoff spot | Select the kickoff spot using the designated home team season, including mixed-season games | Project decision; Basic V-4, p. 5 documents the 2007 spot at the 30; Milestone 13 |
| Hail Mary | Include using Bowl Bound eligibility and outcomes, not NFL outcomes | Advanced I-3, p. 14; Milestone 15 |
| Hurry-up, spike, kneel | Include using Bowl Bound procedures; Paydirt is a design reference only | Advanced I-4(A–B), pp. 14–15; I-6(A), p. 15; Milestone 15 |
| Deferred options | Wild Card/advanced defenses (Advanced II), QB Sneak (I-2), yardage factors (IX), advanced kicking (III–V), Razzle-Dazzle (I-1), elected safeties (I-5), weather (VI), power ratings (VIII), guaranteed in/out-of-bounds (I-4(C), I-6(C)), intentional delay (I-6(B)) | Separate Milestone 22 scope approvals |
| Later timing consideration | Alternate and hybrid timing; neither is promised for implementation | Milestone 22 evaluation only |

## Standard timing matrix

| Category | Seconds |
| --- | ---: |
| Run or completed pass | 30 |
| First down | 20 |
| Change of possession, including turnover on downs | 10 |
| Penalty, even if declined | 10 |
| Incomplete pass | 10 |
| Play followed by timeout | 10 |
| Scoring play or touchback | 10 |
| Unreturned kickoff | 0 |
| Conversion attempt | 0 |

Non-kicking out-of-bounds plays take 10 seconds only in the last two minutes of Q2
and last five minutes of Q4; otherwise ignore the marker for timing. Apply the shortest
applicable duration. Return-chain timing must avoid charging both a kick/turnover and
its return twice (Basic V-6, p. 5). Alternate and hybrid timing remain unavailable pending
Milestone 22 consideration.

## Rules matrix for remaining core behavior

| Behavior | Reference | Planned policy / milestone |
| --- | --- | --- |
| Dice | Basic IV-1, p. 2 | Enumerate 216 offensive and 36 defensive face combinations; Milestone 3 |
| Cell semantics | Legend, pp. 32–33 | Normalize text/color into facts with provenance; Milestone 4 |
| Priority | Basic IV-2(D), pp. 3–4; Priority Chart, p. 34 | Structured, table-driven resolution; Milestone 7 |
| B / QR / QT | Basic VI-2, p. 6 | Supplemental columns are outcomes, not callable plays; Milestone 8 |
| Option SOP / BLP | Basic VI-12, p. 11 | Cancel ordinary defense, reroll under Play 7 / 8; preserve called and resolved classifications; Milestone 8 |
| Penalty rerolls and choices | Basic VI-4(A), pp. 6–7 | Retain original defense; model accept/decline and offsetting choices; Milestone 11 |
| DEF5X | Basic VI-4 commentary, p. 8 | Interpret as DEF5Y without automatic first down; retain original token; Milestone 11 |
| Enforcement and PI | Basic VI-4(C), pp. 8–9 | College-specific enforcement, half-distance, and spotting; conflict resolutions below; Milestone 11 |
| Fumbles and interceptions | Basic VI-9–10, p. 10 | Team recovery ranges and explicit return chains; Milestone 12 |
| End zones | Basic VI-13, pp. 11–13 | Distinguish goal line, end line, live-ball recovery, touchback, and safety; Milestones 9, 12–14 |
| Kicks and field goals | Basic VI-5–6, p. 9 | Field-goal chart yardage measures LOS-to-goal, not statistical kick distance; Milestone 13 |
| Conversions | Basic VI-7, pp. 9–10 | Dedicated PAT data, two-point try from the 2, and conversion returns as Bowl Bound rules; not a full historical conversion simulation; Milestone 14 |

### Scoring implementation (Milestone 14)

Touchdowns award six, field goals three, and ordinary safeties two to the opponent.
An immutable ledger links each award to a committed play report; totals reconcile
from the ledger. A touchdown enters a scoring-team conversion decision rather than
ending the session immediately.

One-point kicks use dedicated normalized PAT outcomes and exactly one offensive
roll (Basic VI-7(A)); the field-goal column is never substituted at runtime. Two-point
tries start at the opponent 2 and use the normal play/priority/turnover engine. A
try reaching the attacking goal scores two; a defensive turnover return reaching
the other goal also scores two, not six. Other completed live plays fail the try.
Pre-snap, offsetting, and accepted previous-spot fouls replay from the enforced spot.
Successful tries offer carry-forward of defensive 5Y/15 fouls to the following
kickoff (VI-4(C)(iv–v)); retain fifteen, not the source typo’s five. Milestone 15
enforces carried fouls on the scheduled kickoff, including half-distance. Dedicated
PAT data has no separate penalty/blocked-kick branch; advanced kicks remain unavailable.

This is the approved board-game conversion profile, not a claim of full historical
NCAA try rules. Milestone 15 completes required conversions before expiration and
schedules post-score kicks during regulation. Milestone 16 adds the historical overtime restrictions.
The compatibility drive mode still stops after a PAT/try, field goal, or safety.

## Worked examples for review

These examples contain no historical team chart data; rulebook examples are identified.

- **Timing:** A six-yard run without a first down consumes 30 seconds. A 14-yard
  first-down completion consumes 20; if followed by a timeout, it consumes 10.
- **Out of bounds:** A non-first-down completion marked out of bounds consumes 30
  seconds at Q2 8:00, but 10 at Q2 1:30.
- **Variable yardage (Basic VI-3 example, p. 6):** Supplemental faces black 3,
  whites 2 and 5 give normal total `10 × 3 + 2 + 5 = 37`, DS `3 + 2 + 5 = 10`,
  X `40 - 37 = 3`, and T1 equal to the normal total, 37. T2/T3 require more rolls.
- **Option:** Called Play 5 produces SOP. Cancel the ordinary defensive result and
  consult Play 7 on a new offensive roll. Record both Play 5 and Play 7.
- **Penalty (project arithmetic example):** On third-and-five at the opponent 7,
  an accepted DEF5 is limited to half-distance: opponent 3.5, rounded toward midfield
  to opponent 4, leaving third-and-two. The p. 9 worked example instead says opponent
  5 and third-and-three; this profile follows VI-4(C)(ii, vii), not that inconsistent example.
- **PAT:** A synthetic dedicated PAT outcome of failure scores zero regardless of
  the field-goal column. A successful two-point try scores two, not a touchdown.
- **Mixed seasons:** Away season 2007 versus home season 1987 selects a kickoff
  from the 35 and permits a regulation tie. Reversing home/away selects a kickoff
  from the 30 and the 1997–2018 overtime format. A neutral-site game still requires
  a designated home team; that team selects the season without a home-field bonus.
- **Overtime:** With a 2007 home season and a tied regulation score, A scores a TD
  and PAT in OT1. B still gets its series; B scoring a TD and PAT forces OT2, while
  B scoring only a field goal loses. At OT3 both must attempt two after a TD.
  In the 1996 profile, PAT kicks remain available in OT3. A defensive touchdown
  during a possession series (not a conversion return) ends the game immediately.
- **Historical tie:** A 1987 home-season game tied 21–21 after regulation ends tied;
  do not invent an overtime possession. A 1995 postseason game uses overtime, but
  a 1995 regular-season game may end tied.
- **Hurry-up:** After a 30-second play, choosing hurry-up reduces it to 20 seconds
  and commits the next snap to the hurry-up hazards. A 20-second first-down play
  is ineligible for this reduction.
- **Spike (separate alternative):** After a 30-second play, choosing a spike without
  hurry-up makes the prior play plus spike consume 20 seconds total and one new down.
  After an unmodified 20-second first-down play, that pair consumes 10 seconds.
- **Kneel:** Lose two yards and ordinarily consume 30 seconds, or 10 if either team
  calls timeout or the play turns possession over on downs.

## Historical season selection and support boundary

At game creation, freeze `rules_season = home_team.season` for both teams. Record
regular-season versus postseason game type as well. Neutral sites require designated
home/away identities; do not choose the newer season automatically. Missing season or
unsupported competition must produce an actionable error, never an NFL fallback.

The initial project scope is **major-college seasons 1940–2023** (using the later
Division I-A/FBS designations only where historically applicable), for overtime and
kickoff placement. This range is an explicit initial support boundary, not a claim
that every intervening rule has been verified. Other competitions, earlier seasons,
and 2024+ profiles require sourced extensions before selection. Thus current-season
play is not initially supported. This does not recreate every historical NCAA rule.

### Kickoff placement

| Home season | Ordinary kickoff from own | Evidence |
| --- | ---: | --- |
| 1940–1985 | 40 | Project historical extrapolation: S2 establishes the spot immediately before 1986, not every earlier season; verify against dated rules before claiming exact historical fidelity |
| 1986–2006 | 35 | S2 and S3 change points; continuity between them is inferred |
| 2007–2011 | 30 | S3 is board-game evidence for 2007; continuity until S4 is inferred |
| 2012–2023 | 35 | S4 change point; continued application is the initial profile policy |

Before 2012, free-kick touchbacks use the 20 (Basic VI-13(G), p. 12, and S4’s
reported change from 20 to 25). From 2012, **free-kick touchbacks** use the 25 (S4);
include this companion policy in Milestone 13. Punt/interception touchbacks stay at 20.
The initial kickoff action does not offer the later advanced kickoff fair-catch
touchback option; fair catches in Milestone 13 refer to punts. Safety free kicks
remain from the 20 under Basic VI-13(G). No adjustment to imported kick distances is
made merely because the kickoff spot differs.

### Overtime

| Home season / game type | Profile |
| --- | --- |
| 1940–1994; 1995 regular season | No overtime; regulation ties are final |
| 1995 postseason; 1996 | Alternating series from the opponent 25; no mandatory two-point round |
| 1997–2018 | Alternating series from the opponent 25; mandatory two-point tries after TDs from OT3 onward (1997 boundary supported by secondary S5; primary-source corroboration still desirable) |
| 2019–2020 | Same through OT4; paired two-point attempts replace series from OT5 |
| 2021–2023 | Series from the opponent 25 in OT1–2; mandatory two after TD in OT2; paired two-point attempts from OT3 |

Sources S1, S5, and S6 distinguish these boundaries. NCAA summaries can compress
the 1996/1997 distinction; retain it explicitly. In full-series overtime there is no
game clock or kickoff. Teams alternate first possession each round; each gets one
series unless a defensive score ends the game or the second team has already won.
A turnover ends the offensive series, but permit the defensive return to finish.
A defensive touchdown during a possession series ends the game; a defensive conversion
return alone does not erase the opponent’s unplayed series. S1 supports one timeout
per team per period without carryover and continued tied periods without a fixed cap.
Reset series to first-and-ten at the opponent 25 unless a penalty relocates the spot.
Apply these procedural details across the selected eras as explicit project defaults
where the cited summaries do not establish historical continuity. In paired-try rounds,
complete both attempts, including defensive returns, before comparing scores. NCAA
2023 Rule 3-1-3(f) explicitly requires equal series unless Team B scores **other than
on the try** (S7); a first-try defensive return can be answered by another defensive
return, so it does not eliminate the second attempt. Do not substitute NFL sudden death.

## Explicit conflict resolutions and optional-action procedures

- **Precedence:** This profile overrides conflicting prose or chart entries only
  where stated. Do not dynamically consult current NCAA rules at runtime.
- **Two-minute warning:** Follow the Timing Chart, p. 34: none in the initial
  supported season range. Disregard the contradictory Basic IV-3 passage.
- **PI versus QT example:** Follow normative Basic VI-4(A)(iii): a PI roll stops
  further offensive rerolls, cancels defense, and leaves an incomplete pass if
  declined. Do not execute the contradictory p. 9 example’s defensive QT roll.
  As a project interpretation of VI-4(C)(iii), the QR/QT-to-DEF10 clause applies
  only when QR/QT was already resolved before PI appeared in subsequent resolution.
  This is a conflict resolution, not an unambiguous statement in the rulebook.
  Implemented in Milestone 11; see [penalties](penalties.md).
- **DEF15 after a successful PAT:** Treat the reference to five yards in
  VI-4(C)(v) as a typo: carry fifteen yards to the kickoff. DEF5Y carries five.
  Enforce half-distance and keep source wording in provenance.
- **Defensive TD priority:** Apply the published correction on p. 38: defensive
  `(TD)` has `[TD]` priority. Preserve the imported token separately. The printed
  Priority Chart's INT/TD = incomplete, F/TD = fumble one yard into the defensive
  end zone, and SOP/BLP exceptions still apply; the correction's broad "always"
  wording does not override those specific chart cells and worked examples.
- **Defensive parenthesized Breakaway:** The published Priority Chart has no defensive
  Breakaway column. By the owner's 2026-10-30 ruling for this unusual imported result,
  treat a parenthesized defensive Breakaway as an override except against offensive
  parenthesized yardage or penalties. If it wins, roll the offense's B column. Keep this
  interpretation limited to defensive chart cells; do not generalize to other decorated
  named results. The Mays rules define Breakaway rerolls and defensive parentheses
  separately but do not state this combination.
- **Parentheses conflict:** Follow the printed Priority Chart p.34: offensive
  `(4)` versus defensive `(-1)` retains the offensive 4. Disregard the p.3 prose
  example saying parentheses offset and produce 3.
- **Minimum turnover locations:** Interpret the chart's `< #` as the lesser signed
  yardage, not the lesser absolute distance. This is an explicit project policy;
  Basic VI-9/10 describes signed spotting but does not independently define `< #`.
- **INT versus QR:** Follow the chart's literal QT outcome. Do not select defensive
  QR or invent a new interception location. See the [ASCII Priority Chart](priority-chart.md).
- **Returns:** Do not copy the Excel-only simplification that suppresses return
  fumbles after penalty rolls (p. 11). Model the complete legal recovery chain.
- **Conversions:** Historical selection initially governs overtime/kickoff policies,
  not all historical scoring rules. Retain Bowl Bound two-point availability and
  conversion returns even for pre-1958 charts. This is a deliberate board-game
  convention, not historical accuracy; historical conversion eligibility is deferred.
- **Hail Mary:** Advanced I-3 says “Within the last 20 seconds of either half.”
  Interpret this as regulation Q2/Q4 with `0 < seconds_remaining <= 20`, against a
  blank defense; zero is excluded except for separately awarded untimed downs, where
  Hail Mary is not initially offered. Use the I-3 outcome table and supplemental rolls.
  Unavailable in overtime, conversions, or while another decision is pending.
  It may be the hurried next snap, retaining the blank defense. By the owner’s
  Milestone 15 decision, printed PI keeps its chart-mode semantics even when hurried.
  Spike and Hail Mary are mutually exclusive actions.
- **Hurry-up:** Apply Advanced I-4(A): reduce the preceding 30-second play to 20,
  committing the hurry-up hazards and its special penalty table to the next snap.
  It is a pending engine choice, not a free clock refund. Hurry-up, timeout, and
  spike are mutually exclusive ways of adjusting the same preceding play. A spike
  cannot be the committed hurry-up snap. The qualifying 30 seconds must be the
  unmodified duration, not a value produced by another reduction. Do not permit a
  next-snap declaration to resurrect a final game.
- **Spike:** Apply Advanced I-4(B): previous 30-second play plus spike takes 20
  seconds total; previous 20-second play plus spike takes 10. Previous 10-second
  plays gain no saving. Consume a down without dice; possession must still belong
  to the offense and another down must be available.
- **Kneel:** Apply Advanced I-6(A): automatic two-yard loss, no dice; 30 seconds
  unless a shorter timing category applies. If the two-yard loss reaches or crosses
  the offense’s own goal line, score a safety, including a kneel from its own 1 or 2.
- **Expiration:** Before committing the prior play’s runoff, offer only legal clock
  management choices. After choosing runoff, resolve quarter/half expiration once;
  never allow a finalized game to be reopened. At 0:00 complete the current play,
  required conversion, and any defensive-penalty untimed down before finalizing.
- **Timeouts:** Three per team per half, no carryover. Record the recipient choice
  from the opening toss and give the other team the second-half choice, as Basic V-3
  specifies; do not blindly import NFL defer/receiver behavior.
- **Deferred actions:** Guaranteed in/out-of-bounds declarations, intentional delay,
  Razzle-Dazzle, QB Sneak, Wild Card and other advanced defenses, weather, elected
  safeties, rating/YF adjustments, and advanced kicking remain unavailable until
  their individual Milestone 22 approvals.

## Historical sources

Reviewed 2026-10-25; links support specific policy boundaries, not wholesale adoption
of modern rules. No rulebook PDF or copied chart is committed.

- **S1:** NCAA.com, [How college football overtime works](https://www.ncaa.com/news/football/2025-01-01/how-college-football-overtime-works),
  January 1, 2025: 1995 postseason / 1996 regular-season introduction, series procedure,
  and 2021 changes.
- **S2:** Associated Press, Los Angeles Times, [College Teams Will Kick Off From the 35](https://www.latimes.com/archives/la-xpm-1986-01-23-sp-28122-story.html),
  January 23, 1986: change from 40 to 35.
- **S3:** Bowl Bound 2007 Basic V-4, printed p. 5: 2007 change to the 30.
- **S4:** Associated Press, ESPN, [NCAA shifts kickoffs to 35-yard line](https://www.espn.com/college-football/story/_/id/7611324/ncaa-moves-kickoffs-30-yard-line-35),
  February 24, 2012: kickoff at 35 and free-kick touchback at 25.
- **S5:** [College Football Overtime Outcomes: Implications for In-Game Decision-Making](https://pmc.ncbi.nlm.nih.gov/articles/PMC7861217/),
  Rick L. Wilson, August 26, 2020 (PMC indexing 2021; PMCID PMC7861217):
  identifies the 1997 third-overtime two-point amendment and 2019 fifth-overtime
  paired-try change. Secondary evidence, not an NCAA rulebook; its unrelated
  three-yard conversion statement is not adopted over Bowl Bound’s two-yard rule.
- **S6:** NCAA.com, [New football overtime rules displayed this season](https://www.ncaa.com/news/football/article/2021-10-27/new-football-overtime-rules-displayed-season),
  October 27, 2021: distinguishes 2019–2020 fifth-round tries from 2021 third-round tries.
- **S7:** [2023 NCAA Football Rules and Interpretations](https://taso.org/wp-content/uploads/2023/05/2023-NCAA-Football-Rule-Book.pdf),
  Rules 3-1-3(d–h), printed FR-48–49, and 8-3-2, FR-87: paired series, defensive-score
  exception excluding tries, conversion requirements, and one timeout per extra period.
  Reviewed 2026-10-26; public source examined in memory, not copied into the repository.

## Acceptance and downstream verification

Milestone 2 delivers the rules matrix, explicit initial policies, conflict resolutions,
historical tables, supported/deferred inventory, and worked acceptance examples.
This is documentation only: existing package tests/lint/format checks apply, not
artificial engine tests. Gameplay milestones must turn these examples into test-first
synthetic regressions before implementing behavior. Historical source limitations
(particularly secondary evidence for 1997) must be retained in implementation docs;
any contrary dated rulebook evidence requires a documented profile revision.

No Paydirt engine code has been copied. No gameplay or importer behavior has changed.

## Later timing evaluation

Milestone 22 will consider alternate timing (action + return + dead time) and hybrid
timing (standard normally, alternate in the last two minutes of each half). Approval
requires explicit conflict resolution, season interactions, synthetic boundary tests,
and full-game play-count audits. Deferral does not imply eventual implementation.

## Basic special-team resolution (Milestone 13)

`bowl_bound.special_teams.SpecialTeamsPlay` owns the kick and all subsequent choices.
The kick is rolled once before reception decisions. Punt asterisk/dagger markers prevent
returns, including on redirected FG/KO distance lookups; those lookups do not become
field-goal attempts or new kickoffs. Unmarked punts permit fair catch or return. End-line
kicks are dead; live end-zone kicks permit touchback or a depth-inclusive return.

Field goals succeed when chart yardage is at least LOS-to-goal; `NG` always misses.
Misses give the opponent first-and-ten at its own 20 or the hold seven yards behind LOS,
whichever is more advantageous (Basic VI-6). For example, a miss from the opponent 30
gives the receiver its opponent 37 (`yards_to_goal=63`), not its own 20.

Kick penalties are enforced from the previous spot; return penalties from the end of
the return, except offensive fouls past the halfway point use that midpoint. Multiple
fouls on one side offer separate acceptances, never added yardage. Offsetting fouls
cancel the play before supplemental yardage rolls. An accepted kickoff foul re-kicks
from the enforced spot; OFF S totals 10–32 instead let the receiver choose own 35 or
a five-yard re-kick. Pending choices do not commit possession, points, or log entries.

Fumbles and blocked kicks use the erring team's recovery range and the Basic VI-10
return gates, with real rolls recorded. Retained scrimmage-kick chains still obey the
original down and line to gain; free-kick recoveries start a new series. Basic VI-13
determines live recovery, white-dice depth beyond the defending end line, touchbacks,
and safeties. A recovery-return touchback uses the own 20, not the free-kick own 25.

The web demo exposes only an optional opening kickoff and scrimmage kicks. Post-score
and safety free-kick scheduling remains part of Milestones 14–15; no clock or conversion
behavior is inferred here. The advanced kickoff fair-catch option remains unavailable.


## Regulation implementation decisions (Milestone 15)

The owner approved preserving printed fixed-yardage and PI fouls on hurried snaps:
the Advanced I-4(A) special table applies only to S/R entries. Its DEF S 10–14
becomes OFF 5, cancels defense, replays the down without rerolls and takes zero
seconds. OFF S 10–11 instead becomes a bad snap (F-2, F-13 on punts, F-7 on field
goals), with recovery handled normally. Other hurried S/R distances follow the
special table. The owner also approved interpreting its unexplained DEF R total
10 dash as **no foul**: record the assessment roll, apply no penalty yardage, then
look up the return on the next roll. That can still yield yards, TD, fumble, or
another foul; it is not an invented zero-yard return or a rerolled assessment.

Normalized NO_CHANGE return cells explicitly mean no advance, unlike missing or
ambiguous importer cells, which remain errors. Consecutive same-side return fouls
are separate alternatives, not summed distances. A penalty followed by a fumble
retains the fumble location but delays recovery dice until the foul is declined.


## Overtime implementation decisions (Milestone 16)

- Game creation freezes the home season and `regular`/`postseason` game type. An
  overtime toss records fresh offensive rolls and offers offense/defense first;
  field orientation is presentation-only, with no wind/end selection mechanic.
- Reuse the approved Bowl Bound play, penalty, interception-decline and conversion
  procedures; this is not a complete historical NCAA rulebook simulator. Ordinary
  series start at the opponent 25; all tries retain the Bowl Bound opponent-2 spot.
- The existing successful-try defensive 5Y/15-yard carry option applies to the
  **next overtime series**, not a nonexistent kickoff. Relocate that series against
  the offending team, including half-distance. Engine labels/descriptions identify
  the next series; the legacy `accept:<index>:kickoff` decision ID and
  `kickoff_penalties` transport field remain compatible. This is an explicit
  board-game carryover policy, not wholesale NCAA post-possession foul enforcement.
- A live return and any penalty/end-zone choice must finish before the series
  advances. A defensive series score ends the game; try returns do not remove the
  other attempt. Compare tied pairs with no round cap, alternating the first team.
- Each round resets to one timeout per team; the count survives the other team's
  series but never carries into another round. Overtime does not charge regulation
  time or offer hurry-up, spike, Hail Mary or free kicks. Final games are immutable.


## College statistics implementation (Milestone 17)

[College offensive statistics](statistics.md) documents the team-accounting policy,
NCAA manual references, supported totals and additive API fields. The user approved
explicit QR/QT marker accounting: QT losses are rushing sacks, QR is a rush, and
ordinary numeric passing results remain completions even for negative yardage.
Statistics use resolved Option classification and never infer sacks from yardage
alone. Conversions, including paired overtime tries, are excluded; full-series
overtime counts. The engine retains/excludes underlying play credit according to
actual penalty enforcement and keeps penalty/defensive-return yards out of offense.

## Engine hardening decisions (Milestone 18a)

- Basic VI-3 full-feature DS/X/T1–T3 distances now resolve on ordinary and
  supplemental scrimmage plays as well as turnovers, penalties and kicks, through
  one shared physical-dice helper. Priority selects which distances need rolls;
  independent offensive/defensive rolls are traced without discarding source facts.
- Basic VI-13 distinguishes the goal line from the end line. Defensive catches/
  recoveries in the original offense's end zone score touchdowns; own recoveries
  are safeties. On/beyond the original offense's end line no recovery is needed.
  Defensive recovery/catch in the other end zone offers touchback or return.
  Beyond that end line, interceptions are nine deep; fumbles roll the white-face
  sum for depth before recovery. Returns count depth; failing to leave the end zone
  is a touchback. A return begun in the field taken into its own end zone is a safety.
  [Turnover details](turnovers.md) include return fouls and recovery chains.
- Declining a prepared turnover penalty resumes its actual engine procedure,
  without repeated chart rolls or a duplicate committed play. Own-recovery return
  fouls retain the original down and line to gain unless enforcement earns a first down.
- Field goals are not offered from own 7 or closer (the hold would be outside
  the field); an invalid direct request is refused before rolling. A fourth-down
  clock choice does not offer a spike, but hurry-up remains independently eligible.
- A requested next snap/kick/kneel first commits the prior play's standard timing.
  If that crosses Q1/Q3, the engine advances and then runs the selected play in the
  next quarter. If it ends a half/game, the request returns `period_boundary`
  without new dice, trace, play/statistical credit or log entry; the updated view
  supplies halftime/final/overtime choices.
- Save profile is `bowl-bound-m18a-v1`; old-profile replay is rejected, not silently
  migrated under corrected rules. The running old backend is not altered.

## Presentation/replay profile (Milestone 19)

Kick origin, flight distance, receiver-relative landing/end-zone depth, return
distance and resulting position are now described by the engine. Field-goal chart
yardage remains a range measured from the line of scrimmage, not a displayed
statistical kick length. This changes replay-description digests, not football
rules; the save engine profile is now `bowl-bound-m19-v1` (see [saves](saves.md)).
Persistent browser hurry mode selects only an offered legal engine decision; it
does not add timing reductions or bypass required decisions.
