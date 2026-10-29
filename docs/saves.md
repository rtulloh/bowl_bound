# Private game saves (schema 1)

## Save and resume in the browser

1. Open the header **Game** menu and click **Save game**, including while an engine decision is pending
   or after a final. The browser downloads `bowl-bound-save.json`; normal browser
   download handling avoids silently overwriting an existing file.
2. Keep the file private, preferably under ignored `private-data/saves/`. Default
   download names and numbered browser copies are also git-ignored. Renaming a
   save does not make its contents public-safe.
3. Use **Load saved game** from team setup, or **Game → Load saved game** during play, to choose that file.
   The server validates it and creates a **separate game ID**. Failed loads leave
   the current game and selections intact. Successful loads clear stale play/
   defense selections and the previous result panel; the engine view supplies the
   saved choices, log, score, clock, statistics and traces.
4. You may refresh or restart the server and then load the downloaded file. Merely
   refreshing does not automatically save or resume a game. Download before
   stopping the server: unsaved in-memory games are still lost on restart.
5. Loading clears hurry mode but keeps the browser **Control mode** explicitly
   selected on setup (human home/computer away by default). Saves never select a mode themselves.
   Choose a human/computer side on setup before loading to resume coaching;
   computer-only actions then advance automatically. Use **Game → New game** to
   return to setup if you need to change modes. Requests cannot overlap save/load.
   Save remains available while waiting for human input, a required decision,
   an automatic error/retry, or final status. There is no manual Pause button.

Downloads preserve the server’s save text exactly: the browser never parses and
reserializes it, so large integer gameplay/coaching seeds retain their full precision.

There is no server-side save directory, arbitrary filesystem-path API or automatic
upload to another service. Saves require the same matching local home/away teams,
including normalized chart data and chart provenance, but excluding optional rosters.
Missing or changed charts fail clearly, rather than substituting another team/season. Charts
are **not embedded** in a save, and loading never imports team data from it.

## Save and resume in the terminal

The [standalone CLI](cli.md) uses this same format: `save PATH` creates a new private
0600 file; `load PATH` validates before replacing the active game, keeping the
terminal control mode. Resume at launch with `python -m bowl_bound --load PATH
--human home --compact` (on one shell line). Use a new filename each time; existing
files/symlinks are refused. There is no auto-save on quit, EOF or interruption.

## Paydirt reference and Bowl Bound adaptation

The workflow follows Paydirt's versioned JSON/local-team references and browser
save/load interaction (reference checkout `bfaf841`; `paydirt/save_game.py` and
`paydirt-web/backend/routes.py` save-replay/load-replay routes). See
[attribution](ATTRIBUTION.md). No Paydirt package, NFL state, AI model or runtime
component is used. This codec is an independent Bowl Bound implementation.

Paydirt restores selected snapshot fields and its web loader repairs some pending
scoring from prose/history. Bowl Bound instead records fixed engine commands and
already-observed individual dice faces. Loading re-executes **only those recorded
commands with those recorded rolls**, rebuilding the real pending procedures,
including kick callbacks, without unpickling Python or inferring state from text.
It then verifies the complete engine view digest. It does not execute the next
pending choice or draw fresh random values during reconstruction. The future
random source is restored at the exact post-save position, shared by the game and
pending procedures, so continuation consumes the same next dice as uninterrupted
play. Saving/viewing does not advance the source.

This reconstructs actual state; it is not playback of canned descriptions. The
engine remains authoritative for field position, clocks, penalties, conversions,
overtime, scoring and statistics. Both the compatible drive mode and regulation
mode are save-capable. A per-game lock makes command completion and a save snapshot
mutually exclusive, preventing a half-recorded snap from being downloaded.

## Schema and compatibility

The top-level JSON fields are:

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly integer `1`; no guessing/defaulting missing versions |
| `engine_profile` | `bowl-bound-m21-v1`, identifying command/rules/trace replay semantics |
| `python` | Python major/minor pair; different pairs are rejected conservatively |
| `saved_at` | UTC timestamp metadata |
| `teams` | Canonical `season/slug` IDs and SHA-256 content fingerprints for home/away |
| `config` | Mode, gameplay seed, start spot, regular/postseason type, initial clock, optional independent `coach_seed` and versioned `coach_policy` |
| `commands` | Ordered `snap`/`kick`/`decide`/`action` operations, arguments and expected error class (null for success) |
| `rolls` | Previously observed offensive/defensive physical-face arrays, in request order |
| `random_state` | Python MT19937 version-3 state, or remaining synthetic scripted rolls |
| `state_digest` | SHA-256 of the semantic reconstructed engine view, excluding derived dice/ownership presentation additions |
| `integrity` | SHA-256 of the canonical document excluding this field |

Canonical hashing uses sorted-key compact JSON with enum values, UTF-8, and no
non-finite numbers. Team fingerprints include normalized chart/provenance content,
not filesystem locations. Physical face count distinguishes offensive (three) and
defensive (two) rolls; totals are not sampled or reverse-inferred.

Milestone 21 uses `bowl-bound-m21-v1`: the RULE-011 return-fumble new-series
correction changes replay semantics. Older `bowl-bound-m19-v1` saves are rejected
before team lookup; no migration or deletion of private saves is performed.
Do not hand-edit engine profiles to bypass this check.

Within the current engine profile, `coach_policy` accepts `baseline`, `chart-v1`,
`easy-v1`, `medium-v1` and `hard-v1`. Omission retains baseline compatibility;
`SavedGame.new` defaults to baseline, while CLI/API new-game defaults are Medium.
The saved policy and independent coach seed are restored, not replaced by setup
selections. No additional mutable coaching RNG state is serialized.

Coached commands journal resolved ordinary engine calls rather than rerunning
the selector on load. Successful committed snap pairs rebuild difficulty
history (including Hard tendencies/recent calls); previews, rejected snaps and
concealed current calls are not training data. The command is journaled before
its derived-history callback, so save/reload can recover if that callback fails.

The semantic digest excludes derived `dice`, `dice_label`, `chooser_side`,
`toss_dice` and `overtime_toss_dice` presentation fields; recorded physical faces
and gameplay fields remain protected.

The loader rejects missing/unknown fields, duplicate JSON keys, invalid types,
booleans where integers are required, invalid faces/RNG states, invalid commands,
path-like team references, mismatched teams, missing/extra/wrong-kind observed
rolls, replay error mismatches and state-digest mismatches. All lookups stay in the
configured local seasons root. Errors never echo uploaded data or local paths.
The integrity digest detects corruption, **not authenticity**: this is not a
signed, tamper-proof or competitive-game format.

Limits are 2 MiB UTF-8, 10,000 command records and 50,000 observed rolls; remaining
synthetic scripts also have a 50,000-roll export/load limit. Saves after an exhausted
or wrong-kind synthetic dice request are refused rather than exported unreplayably.
Unsupported oversized games cannot be exported/loaded, but save refusal does not
end or change the live game.
There is no added gameplay/overtime round cap. Loading costs work proportional to
the recorded game (including engine history/view processing), not a constant-time
snapshot restore. Replay is offloaded from the API event loop.

No legacy Paydirt files, older pre-save Bowl Bound games or cross-profile/runtime
migration is promised. Change the schema/profile or provide an explicitly tested
migration when state/command/trace semantics change; never accept an old save by
silently filling fields or rerolling a missing result. The current live pre-save
backend cannot retrospectively export games whose commands were never recorded.

Milestone 19 rejects both m18 and m18a profiles before team lookup/replay: the
engine view digest now includes richer kick descriptions. No migration is promised.
Owner confirmed there were no existing saves to migrate. Do not hand-edit profile
identifiers. Running games on the old backend are not changed.

No-op rejected requests are not journaled. Errors that consumed dice or changed
visible engine state remain recorded; exhausted scripted requests remain unsaveable.
Gameplay responses capture report/view under one per-game lock. Registry lookup
and least-recently-used eviction are synchronized, with seeds read from the captured game object.
Hurry mode is a browser preference, not a stored football rule; loading clears it.

## API and Python interface

- `GET /api/games/{id}/save` returns the JSON document with `Cache-Control: no-store`
  and a generic attachment filename. Unknown game: 404; unsupported export: 422.
- `POST /api/games/load` accepts that JSON as its request body, not a server path or
  multipart upload, and returns `{game_id, seed, coach_policy, view}` after complete validation.
  Invalid/incompatible/unavailable-team save: 422; oversized streamed body: 413.
  Registration/normal 50-game retention occurs only after successful reconstruction.
- Existing gameplay request/response formats and default drive mode are unchanged.
- Engine callers create `SavedGame.new(home, away, home_id=..., away_id=..., seed=...)`,
  then use `snap`, `kick`, `decide`, `action` and `view`. `dumps_game(game)` returns
  JSON; `loads_game(text, local_team_loader)` returns an independent `SavedGame`.
  The wrapper composes, rather than replaces/subclasses, the existing real engine.
  Direct unjournaled mutations and wrapping an already-played engine are unsupported.
  Default seeded `RandomDice` and synthetic `ScriptedDice` are supported; arbitrary
  custom dice sources cannot be exported by pretending they are the standard RNG.

All saves are private even though they omit chart tables: commands, team identities,
dice, timing and game history remain sensitive local play/audit material.

## Roster presentation compatibility

Optional local roster snapshots and derived named commentary are not saved.
Original descriptions remain semantic and replay-validated. Current-profile
saves remain compatible; loading uses current validated local rosters only after
replay succeeds. Changed names may alter displayed history, never saved facts or
future dice/coaching streams. Missing files stay generic; malformed present
rosters reject adapter load without replacing the current game.
