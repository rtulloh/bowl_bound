# Milestone 19 — Complete the human-playable UI

## Scope and acceptance

Implement UI-001–006, API-001, DEV-001 and DEV-011 alongside complete existing
engine decisions, halftime/overtime/final statistics and clean new-game state.
No AI, new football rules, private charts, remote or publication work is included.
The running backend on port 8000 must remain untouched.

Owner decisions: use Paydirt’s coin presentation, but let the engine supply the
existing toss winner (no browser randomness or second toss). Hurry-up is a mode:
keep it enabled until explicitly toggled off, applying only when engine-legal.
Do not skip decisions or stack timing reductions. A new game starts clean.

## Execution order

1. Original fictional sample teams, reproducible and narrowly tracked directly in
   seasons/2007/ using the team.yaml/CSV catalog contract (not team.json). No
   historical data or Paydirt chart values. Validate public CC0 provenance, complete
   charts, selection, deterministic play and saved continuation. Owner confirmed
   the supported 2007 profile instead of unsupported 2026; both samples are public.
   Ohio State/Miami stay local and out of release packages (DEV-012, milestone 24).
2. Test-first registry/journal hardening and standalone ticket creation tooling.
3. Engine-owned decision identity, kick context and persistent hurry legality;
   frontend contrast, focus, selection resets, coin presentation and guidance.
4. Unit/API/coverage/lint/build and isolated real-engine Chrome acceptance with
   both human sides, regulation/overtime and save/resume. Record exact commands,
   expectation changes, tested commit references; stop after milestone commit.

## Plan audit

Verified: engine is authoritative; Paydirt coin currently generates browser
randomness, which must not be copied. Samples must use the actual CSV loader,
not introduce a second format. Keep tracked authored generator and public-safe
terms; install only new allowlisted sample folders, never replace owner files.
Unknown behavior must get a failing synthetic regression before implementation.
Rollback is a dedicated milestone commit; no live server changes are needed.

## Validation evidence

- `.venv/bin/python -m pytest --cov -q --tb=short`: **1,602 passed**,
  **92.71%** branch-aware coverage (75% enforced), 135.92 seconds; no skips/warnings.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: 172 files formatted; passed.
- In frontend/: `npx vitest run --reporter=dot`: **59 passed**.
- In frontend/: `npm run build`: production build passed.
- In frontend/: `BB_E2E_CHANNEL=chrome
  BB_E2E_SEASONS="$TMPDIR/bowl-bound-m19-e2e-seasons"
  npx playwright test`: **18 Chrome tests passed** against isolated port 8123,
  including both sample home/away arrangements, regulation, overtime, pending
  decisions, conversions, committed statistics, save/reload and invalid saves.
- After adding chooser/focus/selector-identity assertions throughout both sample
  games, reran the same browser command with `e2e/milestone19.spec.js`: **4 passed**
  in 50.7 seconds. This is additional to the 18-test cumulative browser gate.
- Focused Python runs included 85 sample/presentation/save/API/tooling cases
  before the later edge-case additions, and 65 API/save/tooling cases after
  registry/identifier/symlink/body-limit changes. Final cumulative gate above
  includes all additions.
- Public bundles match the generator byte-for-byte and load normally. Git
  allowlist validation exposes exactly ten original data files plus two sample
  documentation/license files. Historical/extraneous chart, provenance and roster
  paths remain ignored. Local Markdown links passed in 16 changed documents.

## Review and changed expectations

- Engine presentation now supplies kick origin, named teams, flight distance,
  receiver-relative landing/depth, return distance and resulting position. Raw
  evidence remains in the expandable audit; no UI chart parsing was added.
- Save engine profile advances to bowl-bound-m19-v1 because descriptions affect
  replay digests. Tests demonstrate m18a rejection before team lookup. The owner
  confirmed there were no saves requiring migration; no migration was invented.
- No-op errors are omitted from new journals, but dice/state-changing errors and
  recorded replay errors remain preserved. Per-game command/view locks, captured
  seeds, LRU registry access, full identifiers, symlink refusal and bounded POST
  buffering have synthetic regressions (including streaming requests).
- Both samples cover every supported Priority Chart row/column, all variables,
  signed distances and offensive penalties for both fouling teams. An initial
  full-game failure exposed penalty cells on defense: those are not supported
  Priority Chart columns, so defensive fouls are represented correctly on offense.
- Complete-game clock checks clamp each charge to remaining time and reconcile
  900 elapsed seconds per regulation quarter. Requested seconds can exceed the
  remaining clock; changing equality to min(before, seconds) tests that contract,
  not a weaker timing invariant.
- Browser clock expectations changed from 14:20/14:00 to 14:10/13:40: a hurried
  snap itself already takes 20 seconds, and the engine does not offer a second
  hurry reduction for that 20-second duration. Mode remains on without stacking.
- Older browser loops now deliberately reselect both plays after possession
  changes; this is the requested UI-003 safety fix, not a removed assertion.
- Hover contrast initially measured 3.67:1; a lighter hover gradient now meets
  the existing 4.5:1 assertion. Required choices receive keyboard focus; optional
  modifiers do not steal focus. Selected play buttons expose aria-pressed.
- Ticket CLI reuses the index validator, exclusively creates files, handles ID
  collisions/exhaustion and symlinked destinations, preserves tickets on indexing
  failure and runs outside the repository. DEV-012 was created through this CLI
  to record the owner’s future release-package exclusion requirement.

The running backend/game on port 8000 was not restarted or exercised. No remote
was added, and nothing was pushed/published. Historical charts were not changed.
Implementation commit: **57b4dd6**, rechecked after commit with:
`.venv/bin/python -m pytest tests/test_sample_teams.py tests/test_presentation_context.py tests/test_save_game.py tests/test_api_hardening.py tests/test_create_issue.py -q --tb=short`
(**99 passed**). UI-001–006, API-001, DEV-001 and DEV-011 are resolved against
that tested reference, not closed; owner play-test confirmation is still required.
DEV-012 remains open for Milestone 24 release packaging. Milestone 20 has not begun.
