# Milestone 18 — Versioned save/resume

## Acceptance

- Version-1 private JSON saves restore drive and regulation games, initial options,
  seed, exact future random state, current engine choices, log, chart traces,
  scoring, statistics, clock/timeouts, opening kicker and historical overtime.
- Synthetic cases resume pending penalties (previous/end acceptance and decline),
  interceptions (return/incomplete), punts (fair catch/return), deferred return-fumble
  recovery after a return penalty, PAT/two-point setup and tries, halftime choices,
  hurry-up, overtime toss/series/timeouts/repeated rounds/paired tries, and finals.
- Loading consumes only already-observed rolls, with strict count/kind checks. A
  test forbids fresh RandomDice calls during load, then compares the next real snap.
  Repeated views/saves cannot perturb the future random stream. The wrapper's seeded
  behavior is compared directly with the existing unwrapped drive/regulation engines.
- A complete synthetic regulation game is resumed at new quarter/phase/OT checkpoints
  and compared step-by-step with uninterrupted play, including exact reports/traces,
  state, statistics, score and clock. Each quarter reconciles to 900 seconds; the
  game finishes in overtime and final-state protections remain authoritative.
- Malformed/incompatible versions, duplicate keys, non-finite JSON, invalid types/
  faces/RNG state/commands, traversal-like team IDs, changed/missing local teams,
  replay evidence mismatches and digest mismatches fail safely. Resigned malformed
  fixtures test structural/replay validation beyond the corruption checksum alone.
- Two MiB byte bounds are enforced while streaming uploads. Command/roll/export-size
  bounds refuse a save without changing live play. A per-game lock prevents snapshots
  from observing a completed engine snap whose journal has not committed yet.
- API download/load uses opaque JSON and canonical local team references, never
  arbitrary save paths or embedded charts. Failed loads do not register a game or
  replace the current one. A separate API instance demonstrates cold-server loading
  and identical pending-decision continuation. Downloads use no-store and generic names.
- Browser Save game / Load saved game controls work from setup and live/final games,
  including pending choices. Uploads never choose a football action. A real Chrome
  download/refresh/load test compares the pending view and next return with the
  original game; invalid-upload coverage preserves the visible state/selections.
- Default and browser-numbered download filenames are ignored; public fixtures and
  browser games are synthetic. Historical charts, rosters, saves and private audits
  are neither loaded by ordinary CI nor added to this commit.

## Paydirt/design review

Per the user's request, reviewed Paydirt at `bfaf8410cb586149f06f98bf98ecca572cae360d`:
`paydirt/save_game.py` and the web save-replay/load-replay routes in
`paydirt-web/backend/routes.py`. Retained versioned JSON, local-team references and
file download/upload. The attribution record documents this workflow reference;
no Paydirt package/code or NFL rule state is a runtime dependency.

Its selected-field snapshot/repair approach is not sufficient for Bowl Bound's
engine-owned pending dice and closure-backed kick decisions. `SavedGame` instead
composes the existing engine, journals public commands and observed physical faces,
then reconstructs exactly those procedures using a strict observed-roll tape.
The stored future RandomDice/script position is activated only after replay and
complete view verification. There is no dynamic import, pickle, eval, callable
payload, prose-based state inference or rerolling during load. No engine gameplay
rule or original engine class was changed.

[The save contract](../saves.md) records schema/profile/Python compatibility, team
content fingerprints, corrupt-vs-authenticated boundaries, bounds, and the replay
cost tradeoff. This is intentionally not a public/competitive tamper-proof format,
a Paydirt migration, a cross-Python guarantee, or retroactive save support for games
already running on the old backend. Unjournaled private engine mutations and custom
unrestorable dice are unsupported. Saving does not impose a gameplay round cap.

No tickets are assigned to Milestone 18. UI-013 (persistent hurry-up), UI-014 (opening
toss/handoff), UI-015 (accessible play/formation help), and UI-016 (visible primary
controls using Paydirt layout guidance) remain Milestone 19 work. Their ticket/index
changes and existing OpenCode configuration changes stay outside the milestone
commit. No Milestone 19 gameplay/UI work is begun.

## Test-first evidence and expectation corrections

1. The initial synthetic save suite failed collection because the save module did
   not exist; API cases then failed on missing download/load routes (404/405), and
   frontend cases failed on the absent SaveControls component before implementation.
2. A concurrency regression failed first because export observed a snap before its
   command record committed. A reentrant per-game lock now protects commands,
   views and export consistently; no duplicated clock/rule logic was added.
3. Privacy regression failed first for the hyphenated default download filename;
   ignore rules now protect the actual name and browser-numbered copies.
4. Initial fixture corrections preserve engine contracts: invalid ordinary play
   strings raise the existing ValueError, not InvalidDecisionError. Two successful
   OT field goals would tie, so the final-guard fixture now uses four second-series
   kneels to produce an actual final rather than assuming a tie ends overtime.
5. The codec initially needed explicit Enum-value JSON normalization for Possession
   in statistical facts; the same complete-view digest now works after real snaps.
6. Two synthetic-source boundary regressions failed first: an oversized remaining
   script and an exhausted-script failed request could export files that could not
   replay. Export now refuses these unsupported states without altering live play.
7. No existing expectations were weakened; no skips or artificial warnings were added.

## Validation

All fixtures are synthetic. No skips or warnings were reported. Commands are from
the repository root unless a directory is noted.

- `.venv/bin/python -m pytest --cov -q`: 1,484 passed; 92.63% branch-aware coverage.
- `.venv/bin/python -m pytest tests/test_issue_tracker.py -q`: 17 passed after adding UI-016.

- `.venv/bin/python -m pytest tests/test_save_game.py tests/test_api_saves.py tests/test_smoke.py -q`: 61 passed.
- `.venv/bin/python scripts/build_issue_index.py`: regenerated the deferred-ticket index.
- `.venv/bin/ruff check .`: passed.
- `.venv/bin/ruff format --check .`: 131 files already formatted.
- `npm test` in `frontend/`: 49 passed.
- `npm run build` in `frontend/`: production build passed.
- `BB_E2E_CHANNEL=chrome npx playwright test` in `frontend/`: 14 real-engine Chrome tests passed.

## Operational boundary

The running private-team backend was not restarted, its old unsaved game was not
reset, and no historical chart/save was exported. A user-coordinated restart is
needed to activate the new backend; it will discard old unsaved in-memory games,
which cannot be retroactively saved by the new journal. Nothing was pushed or
published. Stop after Milestone 18 review/commit; do not automatically start 19.
