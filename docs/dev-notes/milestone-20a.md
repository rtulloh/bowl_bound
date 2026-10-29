# Milestone 20a — Interactive CLI play-testing

## Owner direction

Requested 2026-10-26: the owner prefers CLI play-testing, like Paydirt. Schedule
this milestone immediately after 20 and before chart-aware coaching in 21. This
is approved roadmap scope. Milestone 20 was accepted and committed before CLI
implementation; the terminal implementation below now awaits owner review.

## Deliverables

- A documented terminal launcher that needs neither a browser nor a web server.
- Team discovery from the normal seasons catalog, with Cedar Valley and Harbor
  Tech discoverable from a clean checkout. Local historical charts stay private.
- New regulation games, regular/postseason selection, human on either side versus
  the baseline computer, and retained two-sided manual play.
- Engine-provided status, score, clock, field situation, legal action/decision IDs
  and labels, descriptions and statistics. Optional detailed traces show recorded
  die labels, faces, totals and chart consultations without consuming new rolls.
- The same concealed simultaneous-call coordinator as the web game: the computer
  never receives an unsubmitted human call, and its call is not shown before
  resolution. Computer-only actions advance automatically; required human inputs
  always pause. Inspection commands must not advance play.
- Private save/load through the existing codec, including pending procedures and
  identical future gameplay/coaching. Do not create a separate CLI save format.
- Actionable invalid-input messages, help, and clean EOF/interruption/exit behavior.
  Do not silently decide football choices while exiting or recovering from errors.

## Architecture and scope limits

The terminal layer adapts engine views and sends legal IDs through the same saved
game/coaching methods as other clients. It must not interpret chart strings,
recalculate football state or import Paydirt at runtime. Audit Paydirt only for
suitable terminal interaction ideas; attribute any copied/adapted components.
Chart-aware strategy remains Milestone 21. No publication, release packaging,
historical data changes or automatic live-server restart is authorized here.

## Acceptance

1. Write failing synthetic scripted-input/output tests before behavior changes.
2. Complete games with the human home and away; reconcile score awards, 900-second
   regulation quarters, statistics, legal actions and structured observed traces.
3. Exercise required toss/halftime, kick reception, penalty, interception/recovery,
   conversion and overtime choices, plus disabled/unknown inputs and clean exits.
4. Demonstrate both directions of simultaneous-call privacy using the existing
   public-observation contract, not terminal text hiding alone.
5. Compare seeded terminal continuations and saves with direct engine/API paths;
   old supported saves still load. Inspection/invalid input must not consume dice.
6. Document exact launch/resume commands and an owner play-test checklist. Run
   focused CLI tests and applicable cumulative Python, formatting and web gates.
7. Review, commit with the canonical milestone subject, then stop before 21.

Implementation plan and automated acceptance evidence appear below. Owner terminal
play-testing and the milestone commit remain pending.

## Owner web play-test feedback before CLI implementation

The owner also requested the immediate web control simplification tracked in
[UI-019](issues/UI/UI-019.md): remove routine Pause/Resume, in-game control mode
and Snap controls, submit plays on selection, and move new/save/load to a compact
header menu. This is a focused play-testing follow-up under 20a, not a reopening
of completed Milestone 20 or a claim that CLI implementation is complete.
Browser loads use the mode selected at setup, since no in-game mode selector
remains. The default is human home/computer away; manual play remains last.
Existing manual/API/save contracts and engine rules are unchanged.

The same follow-up supplies verified engine defense selector names (UI-008) and
places one-shot Timeout/Spike alongside Hurry-up in a shared, wrapping modifier
row. OOB and IB are visible but disabled. Their owner-approved interaction is
mutually exclusive and per-play, resetting afterward; only no-huddle/hurry mode
persists. Actual declaration rules (Advanced I-4(C), I-6(C)), costs, exceptions,
timing and save/trace/coaching support remain separate advanced engine work in
[RULE-010](issues/RULE/RULE-010.md), milestone 22. This UI follow-up does not
implement or claim acceptance of those rules or the CLI.

Owner feedback also splits the opening toss into its own pre-play screen using
the existing engine opening phase, following Paydirt’s screen order rather than
its coin/rules logic. Kick/receive choices precede the collapsed dice audit; the
playing screen starts afterward with kickoff controls above the field. Controlled
computer turns, pending-save loading and errors retain the same engine contracts.
This is part of UI-019’s web follow-up, not CLI completion.

## Web follow-up acceptance (not CLI acceptance)

Validated 2026-10-26 with synthetic/public sample teams only:

- `.venv/bin/python -m pytest --cov -q --tb=short`: **1,656 passed**, **92.82%**
  branch-aware coverage, above the 75% gate. No Python production changes followed
  that full run; the final focused run below rechecks the edited areas and index.
- `.venv/bin/python -m pytest tests/test_defense_labels.py tests/test_issue_tracker.py tests/test_coaching_contract.py tests/test_session.py tests/test_coaching_saves.py -q --tb=short`: **51 passed**.
- In `frontend/`, `npm test`: **93 passed**, no warnings/skips; `npm run build`: passed.
- In `frontend/`, `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<synthetic-root> npx playwright test`:
  **26 passed** on one stable build. `<synthetic-root>` is the existing isolated,
  ephemeral `bowl-bound-m20-e2e-seasons` fixture directory, not local historical teams.
- `.venv/bin/ruff check .`: passed. `.venv/bin/ruff format --check .`: **187 files formatted**.

Browser acceptance includes two complete manual sample games and four complete
coached sample games (human home/away, both matchups), with scoring, timing,
statistics, privacy and observed-dice reconciliation. Pending-save continuation
retains exact future dice. Desktop/mobile tests verify all six defense labels,
menu overlays, the shared modifier row, default home coaching, first-enabled
opening-choice focus, the real coin animation, and initially visible toss/kickoff
controls at 1280×720 and 390×700. Reduced-motion paths skip animation/delay.

Changed expectations are documented in UI-019 and UI-008: immediate fresh-call
submission replaces Snap; manual scenarios explicitly select manual rather than
assuming it; opening clocks are verified before/after the separate toss screen;
layout measurements target the full shared row and focus follows engine order.
Gameplay/save assertions were retained. Earlier failed browser runs and their
causes remain in UI-019 rather than being hidden.

Tested implementation: **4afc72e** (`milestone 20a: streamline web play-testing controls`).
UI-008 is closed with the automated browser play-test confirmation authorized by
the owner; UI-019 is resolved and awaits owner play-testing. No CLI,
chart-aware coaching, IB/OOB engine rules, publication or live-server restart is
claimed here. `opencode.json` remains tracked; private charts are unchanged.

## Further owner play-test corrections

UI-020 adds known-result penalty-decline labels (without rerolls), preserves old
pending-save wording digests, shows recorded before/after field context and
expandable dice/cells in the play log, and removes the redundant routine scoreboard
prompt from the visual layout. New tests first reproduced the failures.

DEV-014 corrects the fictional sample recipe to v2 after the owner authorized
chart replacement and restarting the local game. Playable teams no longer double
as exhaustive stress fixtures. See the [all-cell audit](sample-v2-audit.md) for
1,680 checked entries, 839,808 weighted primary combinations, limits and evidence.
All ten public chart/provenance files reproduce the new recipe; historical charts
are unchanged. V1 sample saves require their unchanged old charts, retained locally
in an ignored backup. No fingerprint bypass is implemented.

Validation: `.venv/bin/python -m pytest --cov -q --tb=short` — 1,677 passed,
92.63% branch-aware coverage; `npm test` — 101 passed; `npm run build` — passed;
26 isolated Chrome tests — passed; Ruff check/format — passed. The two further
test-only all-cell/weighted audits pass in the final 15-test sample gate. Existing
full-game clock/scoring/statistics/privacy and exact save continuation assertions
were retained. No production/chart changes followed the full implementation gate.
No skips added. Sample coverage expectations changed intentionally: exhaustive
stress-family presence is replaced with play compatibility, legal coordinates,
ordinary-event coverage and bounded values; exhaustive engine fixtures stay intact.

Local backend restart was explicitly owner-authorized, completed, and smoke-tested.
This remains a focused 20a web/play-test follow-up, not CLI acceptance or a change
to historical chart interpretations. Nothing pushed or published.

Tested implementation for the further corrections: **f571840**. UI-020 and DEV-014
are resolved against that commit and await owner play-testing before closure.
Final focused sample/decision/index gate: **47 passed**; Ruff lint/format pass
(192 Python files). The two all-cell/weighted audit additions are test-only.

## Owner CLI reference for later refinement

The owner typically runs Paydirt as:

```sh
python3 -m paydirt --play -d hard --away 1983/Bears --home 1983/Vikings --compact
```

Retain this as a UX reference for Bowl Bound CLI refinement: direct play launch,
explicit away/home team selection, difficulty selection, and compact output.
This is a Paydirt command, not a supported Bowl Bound invocation; it does not
bring historical NFL teams into Bowl Bound or establish hard-mode coaching as
implemented. Keep the CLI milestone and later chart-aware coaching scope distinct.

## Friendly defense summaries and compact recorded dice (UI-021)

Engine report fields/descriptions now use the existing defense selector labels
with their chart letter, e.g. `C Short yardage (wide)`, instead of `Formation C`.
Detailed trace identifiers remain unchanged. Legacy report wording is normalized
only during save-digest verification; different defense selections still change
the digest. All six formations have synthetic label/digest tests. Three existing
summary assertions intentionally changed to friendly names; trace assertions did
not change. Test-first gate: 14 expected failures and 16 passing controls.

The web log shows every recorded trace roll in a compact, always-visible line.
Faces are listed in brackets with an arrow to the engine-recorded total; the UI
does not calculate totals or outcomes. Expanded cell audits remain available;
no-roll entries invent no line. Two expected frontend failures preceded the fix.

Validation commands/results:

- `.venv/bin/python -m pytest tests/test_defense_labels.py tests/test_session.py tests/test_save_game.py tests/test_penalty_choice_labels.py -q --tb=short`: 107 passed.
- `.venv/bin/python -m pytest --cov -q --tb=short`: 1,691 passed, 92.64% coverage.
- `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`: passed (193 files).
- `npm test` and `npm run build` in `frontend/`: 104 passed; build passed.
- `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<isolated-v2-synthetic-root> npx playwright test`: 26 passed after the engine wording change.
- Same Chrome command with `--grep 'ordinary next snaps|game menu overlays'` after compact-dice/build changes: 3 passed, including friendly summary/dice visibility and desktop/mobile controls.

No chart, rule, dice distribution, coaching or CLI production changes. No skips
added. Live service subsequently reported SIGTERM shutdown; not restarted by
this follow-up. Owner play-test confirmation is pending. Nothing published.

Tested UI-021 implementation: **57f1d1f**. Resolved pending owner play-testing;
final issue-index and defense-label checks: **32 passed**.

## Patched Node toolchain (DEV-015)

Owner-requested frontend tooling upgrade pins Node **24.22.1** / npm **11.19.1**,
with engine-strict installs and documented `nvm use`. Global default unchanged.
No frontend lint migration, source changes or dependency updates were required;
all 380 locked dependency entries are identical. Clean install, **104 frontend
tests**, production build and **26 Chrome tests** passed on the new runtime.
See [Node 24 acceptance](node24-upgrade.md) for exact commands, eMudhra advisory
references, rejected Node 18 dry-run and retained installation warnings.

Separate **DEV-016** remains open for five existing development-tool audit
findings (two critical). Production-only audit is clean; that does not make the
full toolchain audit clean. Deliberate Vite/Vitest major remediation is needed
before alpha; no blind force upgrades included in the Node pin.

Tested Node toolchain implementation: **5a1f63f** (DEV-015 resolved). DEV-016
remains open; no claim that the full frontend dependency audit passes.


## UI-only event emphasis and issue reconciliation (2026-10-27)

[UI-022](issues/UI/UI-022.md) removes pale compact-dice text and adds high-contrast
textual badges in the latest result and play log, using only existing structured
outcomes, interception credit and recorded procedure sections. Fumble/touchback
can be emphasized together; pending interceptions remain decisions, breakaway
lookups say Breakaway roll, and conversions do not claim another touchdown.
No prose/raw-cell parsing, large-gain threshold, new API fact or engine/save
change is included. Earlier in-progress summary/digest edits were withdrawn at
the owner's UI-only correction; the synthetic turnover test verifies unchanged
behavior and no extra rolls. The original dice contrast regression measured
1.1299:1 and failed the 4.5 minimum before the fix.

[DEV-017](issues/DEV/DEV-017.md) records owner-approved npm/Playwright permissions
and trusted private test-workspace access in project-local OpenCode V2 config.
[DEV-018](issues/DEV/DEV-018.md) records the always-file-issues requirement and
recent-fix reconciliation, including stale UI-010/014/017 statuses. Existing
resolved tickets were reused; partial or unrelated requests remain open.

Current checks: 115 frontend tests, production build, 84 focused turnover/save/
label controls, Ruff lint and format (200 files) pass. Full Chrome acceptance
is being rerun with a 600-second harness timeout after the earlier 120-second
timeout and orphaned isolated-server cleanup documented in UI-022. No live
backend restart, game action, historical chart change, push or publication.
Final browser results and implementation commit reference pending.

Full Python regression completed: `.venv/bin/python -m pytest --cov -q --tb=short`
— **1,692 passed**, **92.64% coverage**, no warnings/skips. Issue creation/index
and synthetic touchback checks: **29 passed**. JSON and documented wildcard
checks verify eight validation-command forms, the trusted temp-directory boundary
and no shell allow-rule for destructive operations. The validation helper was
corrected to match V2 simple wildcard semantics (not Python fnmatch character
classes), including optional trailing arguments; config rules did not need a fix.

Owner reports "UI looks good" on the rebuilt live frontend and requests notice
when ready to commit. Record that confirmation without claiming manual coverage
of every event; do not commit until the owner approves. UI-022/DEV-017/DEV-018
remain open until their tested implementation is committed. Previously committed
fixes UI-010/014/017 resolve against their existing hashes.

Final stable-build browser command (Node 24 PATH as above):
`BB_E2E_CHANNEL=chrome BB_E2E_SEASONS=<isolated-v2-synthetic-root> npx playwright test`
with a 600-second harness timeout — **26 passed in 4.6 minutes**, no skips.
Actual computed contrast assertions for compact dice and event badges meet
**4.5:1**; six complete sample games and unchanged clock/scoring/statistics/
save-continuation checks pass. Ready for the owner-authorized commit; nothing
committed or published by this follow-up yet. Engine/backend/charts unchanged.


## Committed follow-up acceptance

Owner authorized committing with ticket IDs in the message. Implementation:
**faf995e** (`milestone 20a: emphasize play events and reconcile reported fixes`).
UI-022, DEV-017 and DEV-018 are resolved against that tested reference;
UI-010/014/017 retain their existing implementation references. Post-commit
issue-tooling/index and unchanged synthetic turnover checks: **29 passed**.
Owner UI approval is recorded without claiming manual observation of all event
branches; tickets remain resolved, not closed. Partial-fix UI-013/016/018 and
DEV-016 security remediation remain open. Nothing pushed or published.

The live Bowl Bound process later received SIGTERM and shut down gracefully;
no restart was performed. Owner clarified port **8000 is reserved for Paydirt**.
Future Bowl Bound UI sessions should use **8001**, with isolated browser tests
still on **8123**. This operational note does not change backend defaults or
claim unsaved in-memory sessions survived shutdown.


## CLI implementation plan (DEV-019)

Status: **REVIEW — CHANGES REQUESTED**. DEV-020 save-cleanup safety and UI-023
manual command labels require follow-up before owner acceptance/commit and 21.

1. Add synthetic tests against a missing CLI module and demonstrate failure.
2. Add a thin terminal adapter and module/console entry points. Load the existing
   YAML/CSV catalog directly, not through a running API. Default to the two public
   fictional teams; keep human-home default, human-away and explicit manual mode.
3. Dispatch only legal engine IDs through SavedGame public execution/coaching
   methods. Show public coaching controls only, never private plans or selections.
   Manual snaps specify both fresh calls in one command. Accept optional modifiers
   without requiring ordinary runoff confirmation. Keep explicit baseline-only
   difficulty; do not claim Paydirt hard mode.
4. Provide status/stats/log/trace/help inspection, optional compact output and
   recorded trace verbosity. Inspection/invalid input must not advance play.
5. Add explicit private create-only saves and bounded loads with atomic game
   replacement; preserve the chosen terminal human mode rather than invent a
   new engine save field. EOF/interrupt/quit never auto-save or decide a choice.
6. Complete scripted games with both human sides and manual play; reconcile
   900-second quarters, scoring/statistics/traces, exact restored continuation
   and direct engine/API paths. Document commands and owner play-test checklist.
7. Run focused/full Python and applicable web regression gates; review and stop
   for milestone acceptance/commit before starting 21.

### Grilling Notes

**Assumptions verified:** 5/5. SavedGame exposes view, execute_with_view,
coach_view/coach_execute/coach_step and the existing codec (save_game.py);
CoachingTurn contains public controls only (coaching_session.py); engine views
provide labels/state/statistics/recorded dice (session.py/regulation.py);
load_team uses the normal team.yaml/CSV contract (team_csv.py); packaging has
module/console-entry support without web dependencies (pyproject.toml).
**Open Questions:** 0 -> 0. **Status changed:** No (READY).
**Key revision:** do not automatically resume the computer after inspection or
an error; require explicit retry after failure/guard. Saves refuse overwrite
and use 0600 permissions; loads are bounded and validate before replacement.

Remaining CLI syntax/display choices are reversible presentation details. The
verified public engine/coaching/codec boundaries are sufficient without rules
changes. Rollback is a dedicated revert of the CLI milestone; existing engine,
web, charts and saves remain compatible. Read-only Paydirt __main__.py help
review confirms useful direct --play/--home/--away/--compact patterns; omit
its server, full-season and NFL features. No runtime dependency or code copying.


### Additional owner reference review

Owner reiterated the retained `python3 -m paydirt --play -d hard --away ...
--home ... --compact` command and suggested computer_ai.py / ai_analysis.py.
Reviewed Paydirt docs/playing.md and docs/saved-games-and-standings.md for
invocation, compact controls, stats/help and private resume UX. Preserve direct
--play/-d/--away/--home/--compact shape, but BB supports only -d baseline until
Milestone 21. Do not silently relabel baseline as hard. Use canonical BB
season/team slugs from --list-teams, not Paydirt team-name identifiers.

Read-only AI review: useful ideas for 21 include distinct gameplay/coaching RNG,
legal fallbacks, comparable-situation call diversity/tendency audits, and reporting
probability coverage/exclusions instead of claiming partial averages are full
conversion odds. Do not port full-engine-object access, raw-string chart parsing,
Paydirt clock/field-position conventions, difficulty factory fallback, or its
10–39 chart range into BB. Use BB normalized facts and exact dice/engine paths.
No Paydirt source, rules, historical data or runtime dependency copied.

Initial CLI tests failed collection as expected because bowl_bound.cli did not
exist. First implementation run: eight passed, three fixture-setup failures
revealed the reusable default synthetic team has unsupported 2026 season; tests
now explicitly use approved synthetic 2002 charts, matching their catalog IDs.
No engine validation or gameplay assertions were weakened.


## Terminal implementation verification (DEV-019)

The standalone adapter is implemented in bowl_bound/cli.py with python -m
bowl_bound and installed bowl-bound entry points. It uses SavedGame public views,
execution/coaching methods and the unchanged save codec; no engine, web production,
chart, dependency or profile changes. Documentation: [CLI guide](../cli.md),
[save/resume](../saves.md), README launch example. No Paydirt source was copied.

Synthetic test-first evidence:

- Missing-module collection failure preceded initial implementation.
- Bare coaching keys/inspection aliases, timeout/toss display and equals-syntax
  startup conflicts: four expected failures before adapter corrections.
- Final review: unsupported reports repeated 100 times, and a file swapped to a
  symlink passed validation. Two expected failures preceded single-step pause and
  descriptor-level no-follow/nonblocking regular-file validation fixes.
- Fixture/API comparison corrections did not change gameplay expectations: use
  approved 2002 synthetic regulation teams, JSON enum encoding equivalent to the
  API, and compare snapshots excluding only saved_at/integrity timestamp metadata.

Acceptance coverage:

- Complete CLI games with human home, human away and two-sided manual control.
  All enable detailed trace rendering, reconcile score awards and each 900-second
  regulation quarter, and match direct engine replay of commands, scores, clock,
  statistics, structured traces, observed rolls and future RNG state exactly.
- Seeded manual game explicitly exercises opening/halftime, accepted penalties,
  interceptions, end-zone choices, conversions and overtime. Separate synthetic
  fumble/end-zone and required kick-touchback/overtime-choice scenarios retain the
  same engine IDs. Unknown controls are covered. Review found that the conditional
  disabled-choice loop sees no disabled options in its current fixture; explicit
  disabled-choice coverage is still required under DEV-019.
- Both coaching sides match the concealed public coordinator and exact saved
  continuation over subsequent calls, decisions and computer-only turns. Pending
  interception save/load and subsequent dice match the real API view exactly.
- Read-only inspection, invalid input, automatic errors/unsupported results/guard,
  explicit retry, EOF/Ctrl-C, create-only 0600 files, partial-write cleanup, bounded
  invalid loads, symlinks and atomic live-game replacement have focused coverage.
- Standalone subprocess play actively rejects imports of backend/FastAPI/uvicorn,
  PDF tooling and Paydirt. Installed console launcher smoke test starts samples,
  inspects status and quits successfully without a server or private teams.

Current validation:

- .venv/bin/python -m pytest tests/test_cli.py tests/test_cli_games.py tests/test_issue_tracker.py -q --tb=short:
  **56 passed** (39 CLI and 17 issue-tooling checks).
- .venv/bin/ruff check . and .venv/bin/ruff format --check .: passed, **206 files**.
- Node 24.22.1 PATH in frontend/: npm test — **115 passed**; npm run build — passed.
- .venv/bin/python -m pip install --no-deps -e .: passed, console entry installed.
  Initial --no-build-isolation attempt failed because this venv lacks setuptools;
  the normal isolated build succeeded without adding runtime dependencies.
- First full pytest --cov attempt hit a 120-second harness timeout at about 37%,
  without reported failures. Fresh 600-second run after final CLI corrections:
  **1,731 passed in 194.88 seconds**, **92.82% branch-aware coverage**, no
  warnings/skips; CLI module coverage is 95%. The earlier timeout is not counted
  as a passed gate.
- Full isolated Chrome suite: **26 passed in 4.6 minutes**, no skips/warnings,
  with a 600-second timeout, Node 24 PATH, BB_E2E_CHANNEL=chrome and
  BB_E2E_SEASONS=<private-temp-root>/bowl-bound-sample-v2-e2e-seasons. Only test
  port 8123 was used; all six complete-game reconciliation checks passed.

No skips/assertions weakened; no live backend restart on 8000 or 8001, historical
chart modification, push or publication. DEV-016 dependency remediation and
UI-013/016/018 partial web fixes remain separate/open. DEV-019 stays open until
review and a tested commit reference; owner CLI play-testing is pending. Stop
before milestone 21 and use the milestone subject plus DEV-019 when authorized.


### Owner-authorized reviewed implementation commit

The owner explicitly requested committing after the review findings were reported.
Commit the reviewed CLI implementation as-is, including the public-safe issue
records; do not interpret this authorization as resolution of DEV-020 or UI-023,
or acceptance of DEV-019’s missing guaranteed disabled-choice coverage. All three
remain open. The passing cumulative gates above apply to the reviewed production
code; subsequent changes here only record review/authorization and issue evidence.
This is an implementation checkpoint, not completion of Milestone 20a. Do not
proceed to 21 until the follow-ups are reviewed, tested and committed. No push,
publication, historical chart change or live-server restart is authorized.


### Bracketed shortcuts and contextual help (UI-023 / UI-024 / UI-025)

Owner requested Paydirt-like per-play shortcuts and supplied bracketed toss,
kickoff and defense/help examples. This follow-up changes only the terminal
adapter: preserve BB engine-owned toss resolution, play names, legal controls,
clock policies and concealed coaching. No Paydirt source/rules or historical
material is copied. In particular do not invent onside kicks, heads/tails input,
blank-input defaults, hard coaching, or NFL play names.

Existing numeric/letter calls are now visible as bracketed menu keys; legal
special plays and pending decisions have contextual aliases. ?/help expands the
current menu without advancement; manual play takes both fresh IDs together.
Explicit full commands remain accepted. A guaranteed synthetic disabled-choice
case replaces the previous coverage gap without altering engine behavior.

Test-first evidence: 17 expected failures / 2 passing controls. Focused cumulative
CLI and issue gate: 96 passed. Ruff lint/format pass (211 files). Full Python
gate: **1,771 passed in 224.97 seconds**, **92.87% branch-aware coverage**
(CLI 96%), no skips/warnings. Public-sample standalone ? / R / K / ? / quit
smoke test also passes with no rejected commands. Ready for owner review/commit;
no production changes followed validation. No frontend, core engine,
save codec, charts or dependency changes, and no web servers started. Previously
recorded web gates apply to unchanged web code; no new web-gate run is claimed.
DEV-020 remains open and outside this shortcut request. All follow-up tickets
remain open pending review/commit; do not proceed to 21.


### Owner play-test follow-ups (UI-026 / UI-027 / UI-028 / UI-029)

- UI-026: choosing Kick at toss/halftime submits the offered human kickoff without
  a second K, through unchanged public SavedGame operations. Both full-ID and
  short forms work; required choices still stop for their owner. Receive, load
  and inspection do not invent a human action. Follow-up failure preserves the
  applied election, reports the partial success and waits for explicit recovery.
- UI-027: one-line quarter/time/score/timeout/situation/possession display and
  blank-line result brackets. The engine commentary and committed call labels
  provide play-by-play emphasis; no new outcomes, hidden-call leaks or NFL rules.
- UI-028: engine-package public coaching helper supplies a deterministic human
  down/distance suggestion. Display it and allow Enter to submit that legal
  scrimmage call, with no default for required/manual/automatic/error turns. CPU
  policy, gameplay dice, save codec and backend contracts are unchanged.
- UI-029: sample smoke found duplicate commentary on computer clock runoff;
  suppress only identical consecutive terminal reports, not changed reports
  or explicit log/trace inspection. No engine-history edits.

Test-first: kickoff election 23 failures / two passing controls; presentation
and default recommendations 14 failures / one passing control; duplicate
commentary two failures. Combined CLI and generated-index gate: 140 passed.
Old tests intentionally change only scoreboard formatting and kick-election
continuation expectations, retaining exact engine/dice/journal parity.
Public-sample smoke uses seed 39, human home, K / Enter / quit. Full coverage
was started before discovering UI-029 and must be repeated for final production
content. Final coverage and owner review/commit are pending; no milestone
acceptance, commit, push, publication, web server or chart changes are claimed.
All ticket IDs must be retained in the eventual owner-authorized commit message.
DEV-020 remains unfixed/out of scope; do not proceed to milestone 21.


Final follow-up validation (supersedes pending full-gate notes above):

- `.venv/bin/python -m pytest --cov -q --tb=short`: **1,815 passed** in
  **217.82 seconds**, **92.91% branch-aware coverage** (CLI 96%), no skips/warnings.
  This fresh run includes the UI-029 duplicate-commentary fix.
- `.venv/bin/python -m pytest tests/test_cli.py tests/test_cli_games.py
  tests/test_cli_shortcuts.py tests/test_cli_kick_election.py
  tests/test_cli_presentation.py tests/test_issue_tracker.py -q --tb=short`:
  **140 passed**.
- `.venv/bin/ruff check .`: passes. A format check caught one slice-spacing
  correction in a new test; `.venv/bin/ruff format tests/test_cli_presentation.py`
  applied it without behavior changes. Final `.venv/bin/ruff format --check .`
  passes: **217 files already formatted**. Ruff lint also passes again.
- Public fictional sample module smoke: baseline, human home, seed 39, coach
  seed 31, compact, K / Enter / quit. One kickoff prompt/election, two distinct
  commentary blocks total, displayed A then D defaults, no rejected commands.
- `.venv/bin/python scripts/build_issue_index.py` regenerates the issue index.

No web/frontend code or dependencies changed, so previous web-gate results are
not claimed as fresh runs. No chart, save-codec, core football-rule or CPU-policy
changes. Ready for owner review/play-test; all follow-up issues remain open
until tested commit references and confirmation exist. Nothing committed or
pushed; DEV-020 remains open and milestone 21 is not started.


### Remove repetitive selection text (UI-030)

Owner requested removing generic play-selection and concealed-call instructions
every play. Filter only those three exact display strings in the terminal;
scoreboard, role labels, legal controls, defaults and actionable decision/error
messages remain. Engine/web status contracts and gameplay are unchanged.

Test-first: six expected failures plus 20 passing presentation controls.
Cumulative CLI/index gate: **147 passed** using the same focused command above.
Ruff lint and format checks pass (218 files). docs/cli.md updated. No existing
expectations changed, skips added, commits made or private data modified.
The previous full 1,815-test gate is historical, not a fresh result for UI-030.
Issue remains open pending owner review and a tested commit reference; include
UI-030 alongside the other follow-up IDs in the eventual commit message.


### Compact summaries and grouped contextual help (UI-031 / UI-032)

Owner requested Paydirt-style sparse prompts with full grouped choices only on
help. Compact scrimmage display now shows OFF/DEF legal key summaries plus offered
special/clock shortcuts, stats/help and visible default. Manual fresh-pair
instructions remain; restricted legal sets never advertise a full unavailable
range. Required decisions still show actionable labels.

Expanded help uses aligned bracketed engine labels and glossary descriptions
under Running / Option Plays, Passing Plays, Special Plays, Special Teams and
Options (or Defensive Formation). Empty groups are omitted. Explicit command
syntax remains accepted and has a separate read-only commands reference instead
of the tutorial preamble and per-play (call KEY) clutter. No rules, CPU choices,
engine/web status contracts, charts or saves changed.

Test-first: compact rendering four expected failures with 26 controls passing;
grouped help/command reference three failures plus a failing special-group check.
Cumulative CLI/index gate: **157 passed** with the focused command recorded above.
Ruff lint and format pass (**220 files**). Public-sample offense/defense module
smoke (seed 39, coach seed 31, R or K / ? / quit) confirms summary-first and exactly
one expanded contextual menu, no rejected commands, no raw call suffixes.

Changed old expectations are intentional: compact-manual labels are checked on
help, with additional assertions that display omits them; role/isolation tests
use titles and legal human labels instead of tutorial words/command suffixes.
Concealed-call, saved-state/RNG, disabled-option and no-advance assertions remain.
No skips or assertion weakening. docs/cli.md documents both modes and commands.
Full Python coverage is running; owner review, tested commit references and final
acceptance remain pending. Include UI-031 and UI-032 in the eventual commit.


UI-031/032 full-gate completion: `.venv/bin/python -m pytest --cov -q --tb=short`
passed **1,832 tests** in **215.07 seconds**, **92.95% branch-aware coverage**,
CLI 96%, no skips/warnings. This result predates UI-033/034.

### Turnover detail and recorded roll diagnostics (UI-033 / UI-034)

Owner reported an Option result reading only defensive recovery, then supplied
a Paydirt interception/return/roll-trail example. The outcome label alone is
ambiguous (it is also used after interceptions). Synthetic Option FUMBLE -4
from opponent 13 reproduces a defensive recovery at own 17. Confirm the original
private/live game with its recorded trace, not by interpreting that outcome prose.

Add an engine-owned derived PlayReport.commentary property, used by terminal
result and log rendering. It uses structured recovery traces and committed
interception statistics, names actual fumblers, marks completed net turnovers,
and shows known recovery/final ball location. Never label the final return spot
a recovery spot or invent players, extra rolls or return lengths. Required
end-zone recovery choices remain pending, not prematurely resolved in commentary.

Keep stored descriptions and all dataclass serialization unchanged: modifying
the description would invalidate legacy semantic save digests. The new property
is derived, not a serialized field, and exact save reload tests pass. No codec,
API/web status/description contract, resolution, statistics, RNG or chart changes.
Compact result rendering now shows actual recorded section:total→cell entries;
--trace retains full faces/labels/context and trace remains read-only.

Test-first: four missing-commentary failures and a missing compact-evidence
failure. New tests cover both recovery sides, Option loss/recovery location,
actual interception versus fumble, pending/end-zone returns, save compatibility
and no invented dice. Corrected one new fixture exception type to the actual
DiceSequenceError. The prior output spacing expectation intentionally now puts
the inline evidence before the blank line; gameplay assertions remain intact.

Focused command: `.venv/bin/python -m pytest tests/test_fumble_commentary.py
tests/test_session_turnovers.py tests/test_turnovers.py tests/test_engine_hardening.py
tests/test_cli.py tests/test_cli_games.py tests/test_cli_shortcuts.py
tests/test_cli_kick_election.py tests/test_cli_presentation.py
tests/test_issue_tracker.py -q --tb=short`: **242 passed**.
`.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass (223 files).
A fresh full Python coverage gate is running. docs/cli.md updated; regenerate
index after ticket edits. All tickets remain open pending owner review and tested
commit references. No commit, push, publication, server or private-chart changes.


### Issue-prefix correction (CLI-001)

Owner directs CLI for terminal work and UI for web/browser work. Terminal tickets
previously UI-023 through UI-035 are reclassified to CLI-023 through CLI-035,
retaining numeric suffixes, prior-ID metadata, status and original evidence.
Historical comments above use the previous IDs; consult issues/README.md for the
canonical linked mapping. Commit history is unchanged. Eventual commit messages
use CLI IDs, along with DEV-019 where applicable; DEV-020 remains separate.

The retired-ID registry prevents the standalone ticket creator from reusing old
UI numbers after migration. Test-first: five expected failures and 11 passing
creator controls before implementing registry reservation/validation. Existing
exclusive-create, collision and index-failure-preservation behavior is retained.
Final issue/CLI checks and a fresh frozen-source full gate are pending. Earlier
coverage jobs overlapped active follow-up changes and are not final gate evidence.


### One-key saves (CLI-035) and migration verification

Owner supplied the Paydirt W save example. Add case-insensitive W with a default
new ignored/private save path, or W PATH as an explicit-save alias. Preserve
create-only 0600 files and the existing codec; print saved location and a quoted
resume command using the installed interpreter and terminal mode flags. Repeated
W never overwrites an earlier save. Default directory symlinks are refused and
saving/inspection never selects a play or resumes paused computer turns.
Custom --seasons must still be supplied when applicable; no AI sidecar or copied
Paydirt debug/team paths. DEV-020 cleanup race is explicitly not fixed here.

Test-first: six expected failures plus two negative controls. New save tests
verify exact reload/state/RNG, permissions, repeated saves, symlink/error handling
and menu advertisement. The initial test assumed python3; require sys.executable
instead so the printed command uses the installed runtime. No old save or
privacy assertions are removed. docs/cli.md documents W and resume behavior.

The canonical CLI migration is complete and active links are checked. Reserve
old UI numbers via retired-ids.yaml; future references/commit messages use CLI IDs.
Issue/creator tests pass, including all original collision/index-error controls.

Focused combined command: `.venv/bin/python -m pytest tests/test_create_issue.py
tests/test_issue_tracker.py tests/test_cli_save_shortcut.py
tests/test_fumble_commentary.py tests/test_session_turnovers.py tests/test_turnovers.py
tests/test_engine_hardening.py tests/test_cli.py tests/test_cli_games.py
tests/test_cli_shortcuts.py tests/test_cli_kick_election.py
tests/test_cli_presentation.py -q --tb=short`: **266 passed**. Ruff lint/format
pass (**226 files**). Full runtime coverage jobs completed during active changes
are not claimed as the final frozen-source gate; final validation is pending.
No changes to charts, codec, CPU policy or web code; no commits/publication.


### Final cumulative verification — 2026-10-27 15:49

After freezing all gameplay-adapter, derived engine commentary, W-save and
retired-ID allocator changes, reran `.venv/bin/python -m pytest --cov -q
--tb=short` in the foreground: **1,851 passed in 226.96 seconds**, **92.97%
branch-aware coverage**, CLI **96%**, no skips/warnings. This includes the five
new registry tests absent from the earlier 1,846-test collection. Prior runs
overlapping active source changes are not the final gate; this run supersedes
those pending notes. No production edits followed this validation.

Focused runtime/turnover/CLI/index/creator gate: **266 passed**. Ruff lint and
format pass (**226 files**). Regenerate the issue index after evidence updates.
Canonical tracking is CLI-001 plus CLI-023 through CLI-035; preserve previous
UI references via the documented mapping and reserve retired UI numbers.

CLI changes are ready for owner play-testing/review, not milestone acceptance
or an implicit commit. All follow-up tickets remain open until tested commit
references and owner confirmation exist. Existing DEV-020 and other separately
tracked findings remain unresolved. No changes/publishing of private charts,
no web servers started, nothing committed or pushed, milestone 21 not started.


### Owner-authorized CLI follow-up commit — 2026-10-27

Owner explicitly requested committing the current changes and listing tickets in
the commit message. Commit scope is the tested CLI follow-up, documentation,
synthetic tests and issue-prefix migration: CLI-001, CLI-023 through CLI-035,
and DEV-019 disabled-choice coverage. Use canonical CLI IDs, preserving prior
UI identifiers in the ticket records. The last full frozen-source gate is
1,851 passed / 92.97% branch-aware coverage; no production changes followed it.

This authorizes a dedicated milestone 20a checkpoint commit, not publication,
final milestone acceptance, ticket closure or a fix to DEV-020. Keep outstanding
review/play-test acceptance and known save-cleanup safety findings visible.
No push or milestone 21 work is authorized.


### Fictional roster preparation (CLI-036)

Owner requested fake sample-team rosters to test player-name commentary. Added
local ignored roster.json and fictional-source notes for Cedar Valley and Harbor
Tech, 30 invented names each spanning all 11 supported positions. Existing roster
loader/selector validates both files, unique team-separated names, round trips
and deterministic wraparound. Existing roster/index tests: 70 passed.

This is data preparation, not completed named commentary: gameplay currently
does not call load_roster/player_name. Engine integration and end-to-end naming
tests, including RNG/save compatibility, remain pending under CLI-036. No engine
or chart changes, packaging changes, publication or automatic commit. Local
roster files remain ignored/unpackaged under the existing roster policy.


### Owner deferral of named commentary — 2026-10-27

Owner explicitly requested scheduling player-named commentary for a subsequent
milestone. The roadmap now assigns engine roster integration and named-commentary
verification to Milestone 21a, after chart-aware coaching (21) and before advanced
options (22). CLI-036 is reassigned from 20a to 21a and remains open/deferred.
Local fictional roster preparation is complete; runtime naming is not claimed.
This removes named commentary from 20a acceptance and does not by itself accept
20a, resolve DEV-020, or change CLI-037 save-picker scope. No runtime changes.


### Owner-authorized handoff to Milestone 21 — 2026-10-27

Owner requested committing the scheduling/tracking changes and proceeding to
the next milestone. Treat this as approval to hand off the committed CLI baseline
(`f121c92`, `ec50e1a`) to chart-aware coaching in 21, with explicit outstanding
follow-ups: DEV-020 (save-cleanup safety), CLI-037 (newest-save default/picker),
and CLI-036 (named commentary, now deferred to 21a). No ticket is automatically
resolved or closed by this scheduling/acceptance decision.

This documentation-only commit also records DEV-021 verified local duplicate
cleanup. Private roster/chart files are not staged, packaged or published.
Applicable verification: roster/index tests 70 passed; final issue-index checks
17 passed. The last runtime gate remains 1,851 passed, 92.97% branch-aware
coverage with no production edits since. Nothing pushed.
