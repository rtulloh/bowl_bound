# Team roster files (Milestone 9b)

A roster is an **optional** file beside a team's other files. It supplies player names for
engine-generated commentary and nothing else.

```text
seasons/<season>/<team-slug>/roster.json
seasons/<season>/<team-slug>/roster-sources.md     # where the names came from
```

Historical rosters gathered by hand are **private**: roster files under `seasons/`
are git-ignored and never packaged. Public tests use invented names only.

## Format

The format is Paydirt's: one JSON object mapping a position key to a list of names.

```json
{
  "qb": ["Alex Quill", "Sam Rook"],
  "rb": ["Ray Bolt"],
  "k": ["Kip Boot"]
}
```

Position keys are `qb`, `rb`, `wr`, `te`, `ol`, `dl`, `lb`, `db`, `k`, `p`, and `kr`.
Any may be omitted, which means "no names". The reader is a strict whitelist:

- unknown, uppercase, or duplicate keys are rejected;
- every value must be a list of strings;
- a name must be non-blank, have no leading or trailing space, no control characters,
  and at most 100 characters, and must not repeat within its position;
- at most 60 names per position, and at most 100,000 bytes per file;
- UTF-8 only, no byte order mark, no `NaN` or infinity;
- the file, its folder, and the season folder must not be symlinks, and the team folder
  must be the canonical slug.

Error messages describe the problem. They never include any value from the file.

## Using names

`bowl_bound.roster` provides `parse_roster`, `roster_to_json`, `load_roster(season_dir,
slug)`, and `player_name(roster, position, index=0)`.

- A **missing file is not an error**: `load_roster` returns `None`. A file that exists but is
  malformed **is** an error, so a typo is never silently ignored.
- With no roster, or no names for a position, `player_name` returns generic wording such as
  `the quarterback` or `the kick returner`.
- The `index` wraps around the list. **No randomness is used.** A name is chosen from an
  explicit index, so it cannot consume or reorder the gameplay random stream. A name never
  changes results, state, statistics, or trace rolls. A test plays the same seed with and
  without a roster and requires identical rolls, yards, and state; only the wording differs.

## Workflow for creating a roster

1. Pick the sources for the team. Confirm that using their data fits each site's terms. Take
   **names only**; do not copy a site's page text or layout.
2. Write `seasons/<season>/<team-slug>/roster.json` with the key lists above.
3. In `roster-sources.md` beside it, record each source: the page, its address, and the date
   you retrieved it, so a name can be traced and re-checked.
4. Check the file loads:

   ```bash
   .venv/bin/python -c "from pathlib import Path; from bowl_bound.roster import load_roster; \
   r = load_roster(Path('seasons/2002'), 'ohio-state'); print('ok' if r else 'no roster')"
   ```

   This prints only `ok` or `no roster`, never a name.
5. Do the Ohio State and Miami (Florida) 2002 teams first. Rosters are never committed.

## Scope

The importer does not produce rosters. Milestone 9b delivered the loader and
format; [Milestone 21a](dev-notes/project-plan.md#21a-add-roster-backed-player-commentary)
adds engine-generated illustrative labels in CLI/API/browser live reports and logs.
Local fictional sample rosters remain ignored and unpackaged. Owner play-test
and milestone acceptance remain separate from implementation verification.

## Engine narration foundation (21a)

`bowl_bound.commentary.narrate_report` uses committed structured offensive
credit and explicit kick/return stages to produce natural play-by-play.
CLI-046 replaces mechanical actor-label prefixes with varied announcer-style
calls, shared by CLI/API/browser live reports and logs. Missing rosters or
positions use generic roles in the same phrase families.

Names remain **illustrative**, not simulated player identities or individual
statistics. That disclosure is documented here and in player guidance, not
repeated before every call. Name selection uses report number minus one
(clamped to zero); phrase selection cycles within each outcome family using
the same index. No randomness, display order or mutable narration stream is
used. Original reports and saved semantic descriptions remain unchanged.

Runs, completions, incompletions, sacks, touchdowns and interceptions use
only established credit/outcome facts, with goal-line-clipped credited yards.
First-down and turnover-on-downs calls require the corresponding outcome;
yardage alone never implies a first down. No tackler, route, broken tackle,
dropped pass or player statistic is invented.

Committed kick/PAT calls can name the original kicker or punter. An explicit
completed kickoff/punt/interception return can name the opposite-side
returner, including a return touchdown; fair catches/touchbacks do not imply
a return. Kicks retain the engine's complete factual detail after the natural
call, including recorded distances and final team/spot. These details have no
separate structured report fields, so narration preserves the text without
parsing chart tokens or inferring return distances.

Automatic kneels/spikes, pending/unsupported reports, penalties, blocked
recoveries, fumble chains and unknown outcome classifications retain the
complete factual commentary
rather than losing enforcement details or inventing actors. CLI/API new/load
paths attach private snapshots; browser/terminal display engine text.

### Optional roster lifecycle

CLI startup and backend create/load snapshot each canonical team ID's optional
`<seasons>/<season>/<slug>/roster.json` after successful engine construction/replay.
Missing files/positions remain generic. Malformed present rosters reject startup
or load without replacing a live game; errors do not echo roster contents.
Snapshots are private per game, stable until explicitly reloaded, and excluded
from saves, chart fingerprints and semantic digests. Loading uses currently
installed rosters: historical display names may change, but game facts may not.

Replay compatibility is regression-checked against a pre-commentary semantic
digest and future Hard command/choice/dice/RNG streams. Named commentary is never
included in the semantic digest; original factual descriptions still are.
No save schema or engine-profile change is needed for optional rosters.
