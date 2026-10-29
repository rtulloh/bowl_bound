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
You can [import your own authorized charts](importing-teams.md) separately.

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
or an available punt, field goal, kneel or other special action. When defending,
choose an offered formation (A–F). Against the computer, your single selection
submits the call; its simultaneous call is concealed until the result. In
two-sided manual mode, the second of the offensive/defensive selections submits
the play. Selections clear after submission; there is no separate Snap button.

Follow required choices for returns, penalties, interceptions, conversions,
halftime and overtime. Disabled choices include an explanation and cannot be
selected. A touchdown awards six, then a one-point kick or two-point try is
offered as appropriate. Kicks/returns and extra decisions resolve only when
the engine offers them; do not infer a result from an animation or die face.

The clock advances through engine decisions, not real elapsed time. Ordinary
runoff normally commits with your next call. Timeouts and spikes are one-shot
choices; Hurry-up mode stays selected until turned off but applies only where
legal. New/loaded games reset Hurry-up mode. IB/OOB declaration controls are
not implemented and remain disabled. The modifier controls wrap onto compact
rows on smaller screens and with wider system fonts; their labels and actions
remain the same.

Expand Team statistics, the scoring summary, Play log and Dice and chart audit
to inspect recorded events. CLI and web share natural engine-generated
play-by-play, with technical calls and traces kept separate. Commentary player
names, when local rosters are installed, are illustrative labels rather than
individual-player statistics. Names never affect dice, results or player ratings.
Without names, the announcer uses generic roles. Pending decisions, penalties
and ambiguous recoveries retain complete factual wording.

## Save and resume

Open **Game → Save game** to download JSON, including during a pending choice.
Keep that file somewhere safe. To resume, use **Load saved game** on setup or
**Game → Load saved game** during play. Select your desired control mode on
setup before loading. Matching team charts must remain installed and unchanged.
An invalid load does not replace your current game.

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
team’s offered timeout. On Easy only, `Z` toggles the default-on coaching helper;
there is no browser helper panel. `quit` exits without automatically saving.

## Alpha limitations

This is an early test release, not a complete implementation of every optional
rule. Supported season profiles cover 1940–2023; older rules may permit a final
tie. Advanced kick options, alternate/hybrid timing, in-bounds/out-of-bounds
declarations and certain end-zone recovery/return-foul branches are unavailable.
Unsupported choices stay disabled rather than guessing a result. The extractor
supports only its documented PDF layout, not arbitrary scans.

Please [report problems](reporting-bugs.md), preferably reproduced with the
fictional samples. Keep your personal charts and detailed chart traces private.
