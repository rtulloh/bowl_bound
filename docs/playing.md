# How to play

[Player guide](README.md) · [Installation](installation.md)

## What kind of game is this?

Bowl Bound is a chart-and-dice college-football strategy game, not an animated
arcade simulation. Choose a team and offensive/defensive calls; the engine
resolves chart results, supplemental procedures, penalties, clock, scores and
team statistics. The web interface shows legal choices and their explanations.
Dice and chart audits let you inspect how a result was reached.

The initial distribution includes **Cedar Valley** and **Harbor Tech**, original
fictional teams for the 2007 season. They are not historical-team recreations.
You can optionally [import your own authorized charts](importing-teams.md) separately.

## Start a web game

1. [Launch the local game](startup.md); leave its terminal window open.
2. Select home/away teams and Regular season or Postseason. The home season
   selects the supported regulation/overtime profile.
3. Choose Human home / computer away (default), Human away / computer home,
   or Two-sided manual play. Manual mode is local control of both sides,
   not network multiplayer or a concealed-call competitive service.
4. Select Easy, Medium (default), or Hard when playing the computer.
5. Start the game and resolve your offered opening kick/receive decision.
   Computer-owned decisions advance automatically.

Difficulty affects coaching decisions, **never dice odds**. Easy/Medium/Hard
use 0.3/0.5/0.7 situational weighting. Hard uses bounded chart-aware estimates,
not perfect foresight or exact win probabilities.

## Calls and decisions

When attacking, choose one of the offered running/option/passing plays (1–9),
QB Sneak, Razzle-Dazzle, or an available punt, field goal, kneel or other special
action. On Razzle-Dazzle, the defense rolls first, then the offense. The lower
roll chooses who selects an offensive chart result: offense when its roll is
lower or tied, defense when its roll is lower. The offense chooses from its
lower total; the defense may choose from either total. Penalty cells are excluded
unless every available cell is a penalty. The selected result then follows the
normal defensive priority and follow-up rules. A B, QR, QT or Option selection
commits to a gamble: its fresh follow-up roll happens after the choice. The
computer can compare possibilities from the available charts but cannot know
that future result. When defending,
choose an offered formation (A–F). Against the computer, your single selection
submits the call; its simultaneous call is concealed until the result. In
two-sided manual mode, the second of the offensive/defensive selections submits
the play. Selections clear after submission; there is no separate Snap button.

Follow required choices for returns, penalties, interceptions, conversions,
halftime and overtime. Disabled choices include an explanation and cannot be
selected. A touchdown awards six, then a one-point kick or two-point try is
offered as appropriate. Kicks/returns and extra decisions resolve only when
the engine offers them; do not infer a result from an animation or die face.
At a kickoff, the assigned kicker may choose a normal or onside kick; the
onside kick travels 12 yards, and the offensive-dice total determines which
team recovers it.

When offered between scrimmage plays, **ES / Elect a safety** awards two points
to the opponents and gives the conceding team a free kick from its own 20. It
uses no dice and is unavailable during a pending play decision.

The clock advances through engine decisions, not real elapsed time. Standard
play timing applies automatically with your next call; there is no separate
runoff action. Kneel to run down the clock. Timeouts, spikes, and the intentional
delay penalty are one-shot choices; delay is offered only after an eligible
30-second play and adds five yards. Hurry-up mode stays selected until turned off
but applies only where legal. New/loaded games reset Hurry-up mode. When offered, OOB and IB declare
the next scrimmage play's bounds and clear after that play; OOB guarantees a
10-second play. Each costs five yards only when it changes a result, subject to
the rulebook exceptions. The terminal accepts O and I while offered, or
`action bounds:oob` / `action bounds:ib`. Choosing a kick clears the declaration;
it never applies to a punt. Modifier controls wrap on smaller screens.

Expand Team statistics, the scoring summary, Play log and Dice and chart audit
to inspect recorded events. CLI and web share natural engine-generated
play-by-play, with technical calls and traces kept separate. Commentary player
names are illustrative labels rather than individual-player statistics.
The included Cedar Valley and Harbor Tech samples have fictional player
rosters; other teams use generic roles unless optional rosters are installed.
Names never affect dice, results or player ratings. Pending decisions,
penalties and ambiguous recoveries retain complete factual wording.

## Save and resume

Open **Game → Save game** to download JSON, including during a pending choice.
Keep that file somewhere safe. To resume, use **Load saved game** on setup or
**Game → Load saved game** during play. Select your desired control mode on
setup before loading. Matching team charts must remain installed and unchanged.
An invalid load does not replace your current game. Ordinary saves keep your
chosen difficulty and use its current coaching improvements when loaded. The
current CPU can preserve its intended fourth-down field goal before an expiring
half with an offered useful timeout or hurry; it does not change Bowl Bound
clock rules.

There is **no automatic save**. Browser refresh, server shutdown or starting a
new game can lose unsaved progress. Closing the browser does not stop the server.
Save first, then press Ctrl+C in its terminal to stop. Keep backups of saves
before upgrading or changing team files. See [version information](versioning.md).

## Source-installed terminal game

Run `python -m bowl_bound --play -d medium --compact` with your installed source
environment. It is solitaire against the computer. Type the displayed shortcut:
1–9 for offense, A–F for defense; follow labeled choices in other phases.
`?` expands the current legal menu, `/` shows statistics, `log` shows game logs,
and `trace` shows recorded dice/chart evidence without advancing play.

`W` saves to a new local file and prints its path/resume command. `W PATH` uses
a new filename you choose; existing files are not overwritten. Resume using
`--load PATH` without new-game difficulty/seed/team overrides. `T` uses your
team’s offered timeout. Append it to an offensive or defensive call, such as `7T`
or `AT`, to request the timeout after that play. The play is submitted first; the
timeout is used only if the engine offers it afterward. If not, the play still
applies and the terminal says no timeout was used. On Easy only, `Z` toggles the
default-on coaching helper;
there is no browser helper panel. `quit` exits without automatically saving.

## Alpha limitations

This is an early test release, not a complete implementation of every optional
rule. Supported season profiles cover 1940–2023; older rules may permit a final
tie. Advanced kick options, alternate/hybrid timing and certain end-zone
recovery/return-foul branches are unavailable.
Unsupported choices stay disabled rather than guessing a result. The extractor
supports only its documented PDF layout, not arbitrary scans.

Please [report problems](reporting-bugs.md), preferably reproduced with the
fictional samples. Keep your personal charts and detailed chart traces private.


On eligible fourth downs, the browser and CLI display the engine's public
recommendation and field-goal distance. All normal difficulties use the same
policy as their CPU. Guidance does not select a play or change the controls;
choose any enabled legal action. It uses public game facts, with actual kick
results resolved from the team chart after the call.


The Clock controls offer **Use [team] timeout on next play**.
Select your team's request, then choose the play or defensive formation. This
matches the normal CLI `AT` timing intent: spend one timeout and use 10 seconds
only if the resolved play would offer a post-play timeout. An incomplete pass,
interception, other possession change, or any play already taking 10 seconds
or less spends none. **Cancel [team] timeout** removes the request. Remaining
timeouts appear on the scoreboard. Only one side's request can be selected at a time.

The web request stays with that selected play through required decisions and
private save/load, then clears once the play is complete. The CLI suffix
currently cannot retain a request across a required human decision; it reports
that no timeout was offered. Existing post-play Clock choices apply to the
completed play. Old saved next-play reservations retain their original behavior.
Cancel a selected request before choosing the separate combined next-spike
option; the engine withholds that choice while a request is selected.

When a completed play's timing is still pending, the Clock controls explain its
normal time charge. Selecting another play applies that previous charge first;
it does not belong to the newly selected play. If the new play requires a
decision, its selected timeout stays attached to that play until the decision
completes. The result and history show the engine's timeout usage once charged.


Computer coaches use Razzle-Dazzle as an occasional surprise, normally around
one to three times per team in a full game. Recent use reduces its preference;
it is never called merely to reach a minimum. You can still select any legal
Razzle-Dazzle call yourself. Actual results and further required rolls remain
uncertain until the engine resolves them.
