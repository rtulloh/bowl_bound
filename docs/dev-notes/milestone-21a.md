# Milestone 21a — Roster-backed player commentary

## Status and boundaries

Planning/ticketing authorized 2026-10-28; **no runtime implementation started**.
This is the next roadmap milestone, before advanced options (22). Milestone 21
acceptance/review remains a prerequisite to runtime work; this plan does not
close its tickets or claim owner play-test confirmation. DEV-029 is deferred,
with owner approval, to the regression-gate cleanup milestone (23), not fixed.

Use optional positional rosters to label engine-established actions. Names are
illustrative commentary, not simulated player performance, ratings, statistics,
or evidence that a specific historical person performed an action. All football
state, results, timing and structured traces remain engine-owned.

## Paydirt consultation and current Bowl Bound foundation

Reviewed before planning:

- Paydirt `paydirt/commentary.py:18–114`: positional roster shape, missing-name
  fallbacks, team-specific context and cached file loading. Adapt the context/role
  separation, but use Bowl Bound’s existing strict loader; do not copy silent
  malformed-file handling or global mutable caches keyed by display names.
- Paydirt `paydirt/commentary.py:305–398`: offense/defense context, run/pass
  classification and role-specific templates. Adapt the concept, not NFL play
  mappings, randomly selected actors/templates, embellished action claims or
  independent narration RNG. Bowl Bound already supports explicit-index naming.
- Bowl Bound `bowl_bound/roster.py`: strict optional `load_roster`, validated
  positional lists and RNG-free `player_name`. Keep its file/path/error contract.
- Bowl Bound `bowl_bound/session.py:138–180`: reports already expose called/resolved
  plays, statistics, traces and generic turnover commentary. Enrich recorded
  facts without interpreting chart tokens or rewriting saved outcomes.
- `docs/rosters.md`, CLI-036, the 21a roadmap, and
  `frontend/src/components/PlayLog.jsx`: fictional local rosters are prepared,
  but gameplay integration is absent and browser logs currently show description.

No Paydirt runtime dependency, NFL rules, historical data or private play logs.
Retain the owner’s Paydirt reference command for comparative local play-testing:
`python3 -m paydirt --play -d hard --away 1983/Bears --home 1983/Vikings --compact`
(run only in the local Paydirt repository; it is not a Bowl Bound test command).

## Ticket map and execution order

| Order | Ticket | Deliverable | Prerequisites |
| --- | --- | --- | --- |
| 1 | [DEV-030](issues/DEV/DEV-030.md) | Reviewed actor/narration, deterministic-index and save/privacy contract | None |
| 2 | [FLOW-003](issues/FLOW/FLOW-003.md) | Engine-owned run/pass narration and generic fallbacks | DEV-030 |
| 3 | [FLOW-004](issues/FLOW/FLOW-004.md) | Supported kick/return/turnover narration; truthful pending/chained outcomes | DEV-030, FLOW-003 |
| 3 | [FLOW-005](issues/FLOW/FLOW-005.md) | Optional team roster context for CLI/API new/load lifecycles | DEV-030, FLOW-003 |
| 4 | [DEV-031](issues/DEV/DEV-031.md) | Pre-commentary save compatibility and exact gameplay/coaching continuation | FLOW-003, FLOW-004, FLOW-005 |
| 5 | [API-004](issues/API/API-004.md) | Serialize engine narration consistently in reports and logs | DEV-031 |
| 5 | [CLI-036](issues/CLI/CLI-036.md) (existing) | Synthetic roster fixtures and terminal named/generic play-test | DEV-031 for terminal integration; fixture checks may precede engine work |
| 6 | [UI-039](issues/UI/UI-039.md) | Browser live/log display, safe rendering and real-engine tests | API-004 |
| 7 | [DEV-032](issues/DEV/DEV-032.md) | Paired determinism audit, docs, privacy review and final acceptance evidence | CLI-036, UI-039, all preceding work |

Metadata links are reciprocal related-ticket references, not a directed graph;
the prerequisite column and each task’s Execution order define dependencies.
Implement in focused commits with tests first and red failures recorded where
meaningful. Same-order tasks need not be implemented concurrently. Do not
duplicate or recreate CLI-036’s already-prepared local fictional roster files.

## Decisions reserved for DEV-030 review

1. Exact role mappings for supported resolved classifications and multi-stage
   outcomes; generic wording when actor evidence is insufficient. No invented
   receiver, tackler, fumbler, return or recovery based on prose or the final spot.
2. Stable explicit name indices with no display counter or RNG draws. Repeated
   reads, retries, previews and loading must not rotate names unexpectedly.
3. Presentation contract for legacy description versus named commentary in
   live/log reports; preserve replay integrity without silently weakening checks.
4. Optional roster context on new/load, and behavior if a roster changes after
   saving. Old same-profile saves remain loadable; unrelated older engine-profile
   rejection remains intact. Any schema/profile change needs explicit justification.
5. Missing files/positions use generic wording; malformed existing files retain
   strict, private-safe error handling. No accidental export of whole rosters.

These decisions are prerequisites, not architecture silently chosen by ticketing.

## Acceptance and validation

- Synthetic test matrix: both possessions, home/away human control, reversed teams,
  run/pass resolved branches, supported kicks, interceptions/fumbles/chained
  returns, pending versus committed results, missing/partial/malformed rosters.
- Equal seeds and calls with/without names must produce equal engine outcomes,
  legal actions, clock, scoring, statistics, structured physical-dice traces and
  coaching choices/history; only approved presentation fields may differ.
- Repeated render/help/preview/API GETs consume no gameplay, coaching or global
  randomness. Save/load preserves replay-determined future streams; naming adds
  no draws. Test old same-profile saves and future commands.
- Public tests generate fictional fixtures in temporary directories. Local sample
  files are optional play-test material, not a CI dependency. Historical files
  stay ignored/unpackaged; do not change release/sample allowlists in this work.
- Focused tests per ticket, then full Python coverage (75% floor), Ruff lint/format,
  API/frontend tests, production build, real-engine browser tests and reconciled
  complete-game audits. Frontend commands use Node **24.22.1**.
- Update roster/CLI/save/API documentation with behavior changes; record exact
  commands, failures, retries, warnings/skips, tested commit references and
  play-test evidence. No closure based solely on a passing test or final score.
- Stop for review and the dedicated commit
  `milestone 21a: add roster-backed player commentary`; do not begin 22 early.

## Out of scope and rollback

No player-specific simulation or stats, historical roster publication, automatic
roster scraping, new packaging, commentary RNG, advanced rules, AI retuning,
dependency changes, save deletion/migration or CLI save-picker redesign.
DEV-016, DEV-020, CLI-037 and other assigned follow-ups retain their scope.
No pushes, new remotes or publication.

Generic narration must remain usable with optional roster context absent. Keep
semantic replay protections; do not use a broad digest exemption or private-save
rewrite as a workaround. If compatibility cannot be demonstrated, stop at the
contract review rather than shipping partial runtime integration.

## Planning review

### Assumptions and resolved evidence

Four of five planning assumptions are verified: the strict optional loader and
RNG-free selector exist (`roster.py:80–121`); structured report context and a
derived commentary property exist (`session.py:138–180`); replay checks include
serialized descriptions (`save_game.py:642–683`); browser logs currently render
description (`frontend/src/components/PlayLog.jsx:10`). Local fictional roster
availability is documented in CLI-036 but was not re-inspected: automated tests
must generate their own fixtures, so an absent ignored local file cannot block CI.

### Open Questions — blocking for runtime work, owned by DEV-030

The five decisions above remain open: exact actor mappings, stable indices,
live/log presentation contract, load/changed-roster policy and private-safe error
propagation. Code establishes the existing behavior but cannot determine the
owner-approved desired policy. These do not block ticket creation; they do block
a claim that autonomous runtime implementation is ready. Prefer the smallest
additive derived-presentation boundary if it passes replay compatibility; do not
preselect a broad report/schema rewrite.

### Grilling Notes

**Assumptions verified:** 4/5.
**Open Questions:** 5 -> 5 (removed 0, added 0, sharpened the replay requirement).
**Status changed:** No; QUESTIONS_PENDING for runtime implementation, task plan complete.
**Key revision:** Loading intentionally replays recorded commands
(`save_game.py:613–624`), so the guarantee is no *additional* RNG consumption
introduced by naming and identical future streams, not that loading performs no
replay work. Corrected the acceptance wording in DEV-032.

The simplest failure is named descriptions breaking old save digests. DEV-030
reviews that boundary before any engine work, and DEV-031 gates downstream API/
UI integration. Generic naming remains the fallback; no migration, broad digest
exemption, new narration RNG or release-data change is presumed.

## Planning-only validation — 2026-10-28

- `.venv/bin/python scripts/build_issue_index.py` regenerated the tracker with
  milestone assignments and reciprocal related-ticket links.
- `.venv/bin/python -m pytest tests/test_issue_tracker.py
  tests/test_create_issue.py tests/test_roster.py -q --tb=short`: **86 passed
  in 0.46s**, no reported skips/warnings. Existing documentation/tooling/roster
  checks only; no artificial behavior test for ticket creation.
- Validated all **17 relative Markdown links** across the new plan/eight tickets.
- No runtime, team data, dependencies, packaging, save files or OpenCode config
  changed. The prior full runtime gate remains applicable; this change records
  future work rather than claiming that work is complete.

## DEV-030 reviewed implementation contract — 2026-10-28

Owner authorized ticket-by-ticket implementation, review before test runs and
before commits. Milestone 21a runtime work proceeds under that direction; the
earlier planning-only hold is superseded, not a claim of retrospective M21
play-test confirmation. Preserve local opencode.json work.

### Presentation and replay boundary

Implement a pure engine `narrate_report(report, home_roster=None,
away_roster=None)` formatter. Its base is the existing `report.commentary`;
`description`, dataclass fields, command journals, chart fingerprints, save
schema/profile and semantic digest remain unchanged. No roster or named text is
added to serialized engine state. Optional context belongs privately to SavedGame,
which exposes `commentary(report)` for adapters. CLI displays that engine string;
API adds a `commentary` field to report/log payloads outside dataclass serialization;
React displays it with legacy-description fallback. Never replace semantic fields.

Local rosters are validated and snapshotted at game creation and after successful
save replay, before installing the loaded game. Missing files/positions use
generic wording; malformed present files fail safely without echoing contents
or replacing a live game. Load uses current installed rosters, so changing a
roster may change displayed historical names but never historical game facts or
future streams. Saves neither embed names nor require a roster fingerprint.
Repeated display within that snapshot is stable. API intentionally exposes names
in commentary only, never full roster tables or filesystem/provenance contents.

### Actor mapping and deterministic indices

Use `max(report.number - 1, 0)` as the explicit positional-list index, independently
for each role/team. No RNG, display counters, regex/prose/chart-token inference or
mutable global roster caches. Names are illustrative positional labels, not
recorded player identities. Preserve base facts verbatim as a separate sentence.

| Structured evidence | Allowed named roles |
| --- | --- |
| Committed RUSH credit | Offensive rb; qb only for an active QR/QT semantic trace branch |
| Committed COMPLETE credit | Offensive qb and wr as illustrative passer/receiver labels, not personnel simulation |
| INCOMPLETE or INTERCEPTION credit | Offensive qb; do not invent a caught pass or intended receiver |
| SACK credit | Offensive qb; do not invent a particular defender or tackle |
| Kickoff, field goal or kick conversion | k on the recorded kicking side |
| Punt | p on the recorded kicking side |
| Explicit completed return stage | kr only when the returning team and actual return are unambiguous |
| Recovery, fumbler, fair catch, touchback or chained ambiguous stages | Preserve existing factual generic commentary; never guess the person from final possession |
| Pending, unsupported, penalty-only or unknown classification | Existing generic commentary; do not narrate uncommitted future actions |

Discarded reroll branches cannot choose a participant; active QB branch evidence
is limited to the final resolution segment. Bad-snap/other ambiguous rushing
actors remain generic if the record cannot establish a role. No named defensive
actor is inferred solely from interception or sack outcome. No unsupported
advanced action, extra physical roll, player statistic or football decision.

### Validation and review order

For each ticket: read-only review tests before their first run; demonstrate
meaningful red-first failure; implement; review changes before running tests;
run focused/cumulative checks; final diff review before committing. Review
findings must be addressed before proceeding. Each ticket is committed before
the next. Final DEV-032 runs the full Python coverage and application gates.
This documentation-only contract uses existing tracker checks, not invented
behavior tests. Paydirt consultation repeated: commentary.py:315–425 supplies
role/context separation, but its random actors and invented defensive details
are deliberately not reused.

## Ticket execution record

- DEV-030: `412730a`. Read-only contract review before tests: no findings.
  Existing issue-tracker gate: 17 passed in 0.28s.
- FLOW-003: tests reviewed and strengthened before red-first run (24 missing-module
  failures). Implementation reviewed before green tests; no findings.
  `.venv/bin/python -m pytest tests/test_commentary.py tests/test_roster.py
  tests/test_statistics.py tests/test_cli_presentation.py tests/test_coaching_profiles.py
  -q --tb=short`: 160 passed in 4.44s. Formatter-only branch-aware coverage gate
  (`--cov=bowl_bound.commentary --cov-fail-under=95`): 24 passed, **96.00%**.
  Ruff check/format passed. Engine-only foundation; adapters still pending.

- FLOW-003 committed as `1505562` after final read-only approval.
- FLOW-004: pre-test fixture review; initial red16fail/4pass. Pre-green review
  found safety/end-zone/reroll gaps; reviewed additional regressions failed6/pass22
  against unchanged code. Fixes reviewed before tests. Focused command:
  `.venv/bin/python -m pytest tests/test_commentary.py tests/test_commentary_special.py
  tests/test_session_special_teams.py tests/test_session_turnovers.py
  tests/test_return_fumble_series.py tests/test_hurry.py -q --tb=short`:
  110 passed in 1.34s. Formatter coverage56 tests passed, **95.12%** branch-aware
  coverage with95% floor; Ruff passed. No profile/schema/semantic changes.

- FLOW-004 committed `3b8b8e4` after final review.
- FLOW-005 reviewed tests then8 red expected failures after correcting synthetic
  regulation season. Production review found no blockers; acceptance matrix
  expanded and reviewed before green. Focused174 passed in16.81s:
  `.venv/bin/python -m pytest tests/test_commentary_lifecycle.py
  tests/test_commentary_lifecycle_extra.py tests/test_roster.py tests/test_cli.py
  tests/test_cli_games.py tests/test_api_saves.py tests/test_save_game.py -q --tb=short`.
  Private context excluded from all save/digest fields; strict errors/atomic
  replacement verified. Full coverage/future-stream parity remain later gates.

- FLOW-005 committed `0b2f030`.
- DEV-031 verification-only: independent pre-commentary2004a21 digest retained,
  semantic-description sensitivity preserved; Hard future streams checked with
  present/missing/changed rosters and both human sides, pending regulation replay.
  Read-only review approved before tests;82 passed in19.91s:
  `.venv/bin/python -m pytest tests/test_commentary_replay.py tests/test_save_game.py
  tests/test_coaching_saves.py tests/test_coaching_profiles.py -q --tb=short`.
  No production change/red-first behavior edit necessary. Golden digest is not
  a full saved-file historical fixture; no private data involved.

- DEV-031 committed `55246bd`.
- API-004: reviewed tests before4 red missing-field failures; implementation
  reviewed before67 green tests in9.25s:
  `.venv/bin/python -m pytest tests/test_api_commentary.py
  tests/test_api_commentary_commands.py tests/test_api.py tests/test_api_saves.py
  tests/test_api_coaching.py tests/test_api_regulation.py tests/test_api_hardening.py
  -q --tb=short`. Ruff passed; engine text only in additive report/log field.

- API-004 committed `babf44f`.
- CLI-036: reviewed red5failed/4generic passed;2 display-site changes. Reviewed
  green run exposed2 cross-interface expected-schema mismatches (91 passed),
  updated full equality expectations to include exact engine commentary, reviewed
  before rerun:93 passed in10.67s, Ruff passed. Command:
  `.venv/bin/python -m pytest tests/test_cli_commentary.py tests/test_cli.py
  tests/test_cli_presentation.py tests/test_cli_easy_helper.py tests/test_cli_games.py
  tests/test_cli_solitaire.py -q --tb=short`. Local fictional roster/provenance
  checks passed without raw-data output or file edits. Owner play-test pending.

- CLI-036 committed `c676f4f`.
- UI-039 reviewed before unit red2fail/2fallback pass, then reviewed before
  green122 frontend tests and production build, all Node24.22.1. Focused
  real-engine Chrome browser3/3passed in8.6s (`commentary.spec.js`), synthetic
  named/reversed/missing rosters;mobile wrapping and download/load checked.
  Commands use the selected Node 24.22.1 `node` executable with
  `frontend/node_modules/vitest/vitest.mjs run`, `vite/bin/vite.js build`, and
  `@playwright/test/cli.js test e2e/commentary.spec.js` from frontend directory.
  User requested Node executable allowlist addition; opencode.json preserved
  outside milestone commits and validated as JSON.

## DEV-032 acceptance review matrix

| Requirement | Evidence / remaining boundary |
| --- | --- |
| Engine owns all actor roles/wording | FLOW-003/FLOW-004 formatter; unknown defenders/recovery chains remain generic |
| Stable names without RNG | Report-number indexing; repeated-render/global RNG checks; Hard replay parity |
| Optional private context | FLOW-005 atomic per-game snapshots; malformed/symlink rejection; missing files generic |
| Save compatibility | DEV-031 independent old digest; unchanged profile/schema/descriptions; future streams retained |
| CLI/API/browser transport | API-004/CLI-036/UI-039; exact engine text and legacy fallback; no UI actor mapping |
| Safe browser display | Escaped hostile-looking names, long-name390px wrapping; synthetic real-engine download/load |
| Privacy | No chart/roster/provenance/package edits; only synthetic generated CI data; user config excluded |
| Complete games/full gates | Paired full/partial/generic audit passed; Python 2,231 passed/93.48% coverage, frontend 122/build and browser 32 passed |
| Owner acceptance | Not inferred from automated tests; no gameplay/UI ticket closure; no Milestone22 work |

Comprehensive read-only pre-gate review found no runtime blockers. It identified
and corrected obsolete claims in docs/saves.md about roster fingerprints, and
future-only integration wording in docs/rosters.md. Repository-wide Ruff lint
passed and format check reported334 files already formatted before full gates.

### Final cumulative gate results

- Full browser gate: **32/32 passed in3.9m**, no retries/skips/warnings reported.
  `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS="$TMPDIR/bowl-bound-m21a-final-browser" node node_modules/@playwright/test/cli.js test`
  from frontend directory. Runtime tested: `4457887`.
- Final tracker/create-issue gate:33 passed in0.45s after resolution metadata
  updates and index regeneration. Commit hashes quoted to avoid all-digit YAML
  values being parsed as integers; initial index validation caught this before
  corrected regeneration.
- 56 local Markdown link targets validated across maintained guidance and plans.
- Repository-wide Ruff lint/format passed (334 files already formatted).
- Python full branch-aware coverage gate still pending at this checkpoint.
- DEV-029 remains explicitly deferred/open; passing browser gate is not a fix.

Python first cumulative attempt: **2229 passed,2 failed in440.44s**, coverage
**93.51%**. Both failures were the newly added paired-audit fixture attempting
to export public sample charts through a helper with unrelated synthetic source
hash metadata, not gameplay mismatches. Corrected to canonical
`install_samples(tmp_path)`; no production code or audit assertion changes.
Correction reviewed before focused rerun:2 passed in10.33s. Full coverage
rerun started after the initial gate completed; final green still pending.

### Final audit outcome — 2026-10-28

- Full rerun `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`:
  **2,231 passed in436.20s;93.48% branch-aware coverage**. No skips/warnings
  reported;75% project floor unchanged. This exceeds the prior93.42% M21 gate.
- Full frontend **122 passed**, production build passed, Node **24.22.1**.
- Full real-engine Chrome **32/32 passed**, no retries;3.9m.
- Complete-game audit compares six seeded regulation games (generic/full/partial
  contexts for each human side), reconciling all engine views/turns/results and
  future journal/roll/RNG/digest streams. Hard history parity covered separately.
- Original2 fixture failures are documented above; corrected focused and full
  reruns passed. No production semantics or assertions weakened to make them pass.
- All nine tickets resolved with committed/runtime-tested references, not closed.
  Owner play-test and milestone acceptance remain explicit follow-ups.
- Final audit commit is scoped to DEV-032 evidence/tests/docs and ticket status
  reconciliation. User-requested `opencode.json` changes stay uncommitted.
- No remotes/pushes/publication, historical-data changes or release/package edits.
  Next direction agreed with owner: publication-readiness planning for a
  fictional-team-only alpha, then community feedback alongside remaining work.
