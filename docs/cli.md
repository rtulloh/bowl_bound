# Playing in the terminal

Bowl Bound is solitaire against a computer opponent. The terminal runs directly
over the engine without a browser, API or web dependencies. The opposing call
stays concealed until resolution; there is no two-sided terminal mode.
From the repository root, install the core package (`pip install -e .`) in your
Python 3.10+ environment. The fictional Cedar Valley and Harbor Tech bundles are
included in the checkout; see [sample teams](sample-teams.md) to regenerate them.

## Start a game

```sh
.venv/bin/python -m bowl_bound --play -d medium --away 2007/harbor-tech --home 2007/cedar-valley --compact
```

After installation, `.venv/bin/bowl-bound` accepts the same arguments. Defaults are
human home / computer away, these two sample teams, and a regular game. Use:

| Option | Purpose |
| --- | --- |
| `--play` | Start interactive play (also the default) |
| `--list-teams` | List readable local season/team IDs, then exit |
| `--seasons PATH` | Team catalog root (default: `seasons` in the working directory) |
| `--home YEAR/slug`, `--away YEAR/slug` | Select installed teams by exact listed ID |
| `--human SIDE` | Control home or away; the computer controls the opponent |
| `-d easy`, `-d medium`, `-d hard` | Conservative (0.3), balanced (0.5, default), aggressive/chart-aware (0.7) coaching; never changes dice odds |
| `--game-type TYPE` | regular or postseason; engine's season-appropriate profile |
| `--compact` | Show legal shortcut keys and default; expand play labels with `?` |
| `--trace` | Show detailed recorded dice and chart consultations after reports |
| `--seed N`, `--coach-seed N` | Separate gameplay and coaching seeds (0 through 2^63−1) |
| `--load PATH` | Resume a private save instead of creating a game |
| `--help` | Show all startup options |

The familiar Paydirt invocation shape is retained, but these are Bowl Bound team
IDs and difficulty levels. No Paydirt installation or historical charts are needed.
The coach selects from engine-legal controls; see [difficulty and fairness](coaching.md#policy-and-fairness).

### Easy-only coaching helper

Easy displays assistance at offensive/defensive play selection by default. **Z**
toggles it without advancing play. The preference is terminal-local, not saved;
starting or loading a game restores it to on. Medium/Hard have no helper.
Advice is computed once per enabled display, never while switched off. The Z
control remains available during optional runoff/play selection, but not before
the opening kick, during a required decision, or after the game finishes.

On offense it ranks up to three offered plays from plain numeric offensive cells
using exact dice weights. Targets are half the distance rounded up on first down,
70% rounded up on second, full distance on later downs (minimum one yard).
Target rate, positive-gain rate and average yards are conditional on the numeric
cells evaluated. Coverage is their share of all dice outcomes; below 50% is
**limited** and ranks behind supported estimates. Missing/symbolic/annotated cells
are excluded, not zeroed. No defense, priority or secondary procedure is resolved;
these are **not full-engine conversion odds** or confidence intervals.

Separate Situation/Clock tips are heuristics, not new rules. Defensive advice is
situational, not learned CPU tendencies. The existing Enter default is separate
from these chart rankings. No browser helper panel is added.

## Bracketed shortcuts

Type the key shown in brackets; letter keys are case-insensitive. `?` or `help`
expands the **current legal menu**, even in compact mode. For example, an opening
choice offers `[R] Receive` and `[K] Kick off`; enter `r` instead of
`choose toss:receive`. Required choices also display numbered shortcuts.

In compact mode, ordinary scrimmage turns show only a shortcut summary:

```text
  OFF: 1-9 | P,F,K | W=save | /=stats | ?=help (Default=1/Line Plunge)
```

The keys are filtered to current legal controls; this example is not a universal
menu. Defensive turns show `DEF: A-F` instead. Only your team's controls appear.
Required choices remain labeled so they are actionable without another help command.

`?` expands a titled, aligned menu: **Running / Option Plays**, **Passing Plays**,
**Special Plays**, **Special Teams**, and **Options**, omitting groups that have no
legal choices. Defensive help shows **Defensive Formation** and relevant options.
Labels come from Bowl Bound; short glossary descriptions do not promise yardage
or change the rules. Full command suffixes are omitted from play labels. Type
`commands` for explicit command syntax, private save/load instructions and traces.
Without `--compact`, the expanded menu is shown at each turn.

| Key | Bowl Bound play/control, only when offered |
| --- | --- |
| `1` | Line Plunge |
| `2` | Counter |
| `3` | End Reverse |
| `4` | Draw |
| `5` | Option |
| `6` | Screen |
| `7` | Sprint Out |
| `8` | Boot-leg |
| `9` | Drop Back |
| `A`–`F` | Engine-labeled defense (including `F` Blitz when defending) |
| `P`, `F` | Punt or field goal when choosing an offensive special play |
| `K` | Kick off, elect to kick, or kneel—whichever the current menu offers |
| `H` | Hail Mary when the engine offers it |
| `R` | Receive or return, as labeled in the current decision |
| `TB`, `FC` | Touchback or fair catch when offered |
| `N`, `S` | Apply an offered hurry or spike clock choice |
| `T` | Your offered timeout, on offense or defense; append to a call as `7T` or `AT` |
| `W` | Save immediately to a new private file; `W PATH` selects an explicit new filename |
| `Z` | Toggle Easy-only coaching at play selection (on by default) |

During required decisions, numbers select the displayed choices, not scrimmage
plays. During optional clock modifiers, `1`–`9` remain offensive calls. Disabled
choices have no shortcut. Enter submits a **displayed default** in human/computer
mode (see below); otherwise it does nothing.
Append `T` to an offensive or defensive call (for example, `7T` or `AT`) to use
your timeout after that play when the engine offers it. The call still applies if
the timeout is unavailable; the terminal reports that no timeout was used. An `O`
shown for an overtime offense-first choice is not an onside-kick command. Follow
the current menu, not another phase.

Enter one offensive number or defensive letter from your current menu. Paired
calls such as `1 A` and `snap 1 A` are rejected without advancing the game.

## Scoreboard, commentary and Enter defaults

The summary is one line: quarter/clock, away and home scores with remaining
**timeouts in parentheses**, engine situation/spot, and possession. For example:

```text
Q1 14:50 | Harbor Tech 0 (3) - Cedar Valley 0 (3) | 1st and 10 @ own 32 | Harbor Tech ball
```

Blank lines separate play results and the next summary. The `►` line emphasizes
the engine's own commentary; committed offense/defense labels appear only after
resolution. Unchanged reports returned again by clock modifiers are not repeated;
updated reports still appear, and explicit `log`/`trace` remains available.

Turnover commentary comes from the engine's structured recovery traces and
committed statistics: fumbles identify the fumbler; a single recovery with no
return names the recovering team and recovery spot. Returns show the **final ball
position**, not an invented recovery spot. Committed interceptions are emphasized
with `INTERCEPTED!`; a completed possession change is marked `★ TURNOVER!`.
An offensive fumble recovery is not falsely labeled a possession-changing turnover.

Compact results include `(section:total→cell | ...)` using only actual recorded
trace entries, including recovery and return rolls. For full die faces, labels,
team/chart context and cells, use `trace` or start with `--trace` (which replaces
the short summary with the detailed trace). Inspection does not roll dice.
These diagnostics may contain private chart values; do not publish historical
team captures. No player names, unrecorded rolls or return distances are invented.

`log` uses the same engine-derived commentary. Stored legacy descriptions and
save digests are unchanged, so existing saves remain loadable. The CLI uses an
engine commentary property; it does not interpret chart text or decide turnovers.

During human/computer scrimmage selection, the menu shows
`Default=A/Standard` (or another legal call). **Press Enter to submit it**;
you can always type a different call. Recommendations come from a deterministic
public coaching helper, using down/distance only—no charts, hidden opponent
calls, seeds, or dice. The human convenience policy is separate from the CPU:

- Offense: Line Plunge on first down or 3-or-fewer yards; otherwise Screen up to
  7 yards, Drop Back beyond 7.
- Defense: gaps short yardage at 3-or-fewer; otherwise Standard on first down,
  short prevent on second down or later, long prevent on third/fourth and >7.
- A missing suggested call falls back to the first offered call.

Defaults are scrimmage calls only, not fourth-down special-teams advice. There
is **no Enter default** for required decisions, kickoffs,
computer-owned turns, finished games or paused error recovery. Optional clock
controls do not override the displayed scrimmage default. Inspection never
submits it or advances dice; EOF/Ctrl-C/quit remain exits, not defaults.

Selecting **Kick** at the opening or halftime election also submits the offered
normal kickoff immediately—no second `K`. This applies to the numbered choice
and `choose toss:kick` / `choose half:kick` too. Required return/penalty
choices still stop for their owner; the computer resolves only its own choices.
Choosing Receive does not submit a human-owned kick. Loading/inspecting an
already-pending human kickoff does not submit it either. If the follow-up kick
fails, the election remains applied, the error is shown, and inspection cannot
retry it: use `kick kickoff` explicitly when ready.

## Commands during play

Follow the **currently offered** engine IDs and labels. Choices are not interchangeable
between phases; disabled choices include the engine's reason.

- `call 1` or bare `1`: select a displayed offensive play against the computer.
- `call A` or bare `a`: select a displayed defense against the computer.
- `choose ID`: resolve a required choice, e.g. `choose toss:receive` when offered.
- `kick KEY`: select a listed kickoff, punt or field-goal action.
- `action KEY`: select a listed engine game action.
- `commands`: read-only full command reference, including saves and traces.
- `status`, `stats` (or `/`), `log`, `trace`, `help` (or `?`): inspect without
  advancing play or consuming dice. `?`/`help` redisplays full current legal controls;
  `trace` shows toss evidence and the latest report.
- `retry`: explicitly resume after a computer error or automatic-turn safety stop.
- `quit` or `exit`: leave without saving automatically. EOF also exits cleanly;
  Ctrl-C exits with status 130. Neither chooses a pending football decision.

Computer-only turns advance at startup and after successful gameplay or loading.
They stop at human decisions. Standard timing is applied with the next action;
there is no separate runoff or Continue action. At a Q1/Q3 boundary, that next
play runs in the new quarter. At halftime or game end, the engine transitions
without running another play.
Use `T` for your team whether attacking or defending; the computer can call its
own legal timeout too. `TO`, `TD`, `TH` and `TA` are not commands.
Hurry/spike belong to the offense only.
The opposing scrimmage call remains concealed until resolution. Inspection and invalid
commands never restart a stopped computer turn; inspect/save, then use `retry`.

## Save and resume privately

Type **`W`** (or `w`) to save immediately. It creates `private-data/saves/` if
needed and writes a new `bowl-bound-TIMESTAMP-RANDOM.json` file with owner-only
permissions. Repeating W creates another file, not an overwrite. The CLI prints
the saved path and a quoted resume command using your current Python interpreter,
human control mode, compact mode and trace flag. Run it from the same project
directory; retain your custom `--seasons PATH` if you use one. There is no AI
sidecar: the existing save already contains the coaching seed and exact future
dice state. Save does not select a play or resume a paused computer turn.

Default save folders must not be symlinks. Explicit `save PATH` (or `W PATH`)
remains available. For an explicit filename, create an ignored directory once
and choose a **new filename** for each save:

```sh
mkdir -p private-data/saves
```

```text
bb> save "private-data/saves/first game.json"
bb> quit
```

```sh
.venv/bin/python -m bowl_bound --load "private-data/saves/first game.json" --human home --compact
```

Or use `load "private-data/saves/first game.json"` during play. Load keeps the chosen
terminal control mode, validates before replacing the live game, and uses the same
[save codec](saves.md) as the web game, including pending procedures and exact future
dice/coaching. The same unchanged team charts must be installed. Loads reject
symlinks, nonregular files, oversized saves (over 2 MiB), and invalid/tampered data.
Do not combine `--load` with new-game team/seed/game-type/difficulty overrides.
Legacy baseline/chart saves retain their original policies; they are not relabeled Hard.

Saves are create-only with owner-only file permissions (0600); existing files and
symlinks are never overwritten. A failed write removes its partial new file. There
is no auto-save. Terminal traces can contain chart values, so do not publish saves,
terminal captures or historical team data. Use only fictional samples in shared reports.

## Play-test checklist

1. Run `--list-teams`, launch the sample command, and make the offered opening choice.
2. Select offensive and defensive calls; confirm only your controls appear before
   the snap and both committed calls appear in the result. Try `--human away` too.
3. Inspect `status`, `/`, `log` and `trace`; confirm clocks, scores and pending
   choices do not change. Try an invalid/disabled choice with the same expectation.
4. Try optional timeout/hurry controls and follow kick, conversion, penalty,
   interception/recovery, halftime and overtime choices when offered.
5. Save during a pending choice; resume with the same local charts and compare the
   next result/dice to the original continuation. Try an existing save filename.
6. Confirm `--human manual` and paired-call commands are rejected. Complete a game
   against the computer and reconcile scoring,
   quarter clocks and statistics; exit from a pending choice without auto-saving.

Report problems with synthetic examples via the [issue workflow](dev-notes/issues/README.md).

Routine instructions stay out of the terminal play display. Use `?` or `help` to
review legal controls and timeout suffix guidance; required choices and game status
remain visible.

Live reports and play logs display engine-generated
[optional player labels](terminal-play.md) from local rosters. See
[roster lifecycle and privacy](rosters.md) before installing player names.
