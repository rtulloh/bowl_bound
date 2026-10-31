# Bowl Bound Project Plan

## Purpose

Build Bowl Bound as a standalone project, selectively reusing suitable Paydirt ideas and components without a runtime dependency on Paydirt. Development is organized into small, independently testable milestones. Stop, review, validate, and commit after each milestone.

## Working agreement

For every milestone:

1. Confirm scope and acceptance criteria.
2. Write self-contained behavior tests first when changing behavior.
3. Demonstrate a meaningful baseline failure when possible.
4. Implement only the agreed milestone.
5. Run focused and cumulative applicable tests.
6. Update documentation and review limitations.
7. Commit before starting the next milestone. Use `milestone X: <description>` for commit subjects, replacing X with the milestone number; this overrides the original suggested prefixes below.

Historical PDFs, converted historical team data, saves, and audit reports are private by default and must be ignored. Use synthetic fixtures in committed unit tests unless chart redistribution rights are established.

Track defects and follow-ups in the [issue tracker](issue-tracker.md), using
[per-ticket conventions](issues/README.md). Every ticket has a target milestone;
review that milestone’s tickets as part of acceptance. A ticket assignment does not
claim that its fix or milestone is complete.

## Architecture boundaries

- **Importer:** owns PDF layout, text, colors, source locations, and extraction reports.
- **Chart model:** owns validated chart facts and team-data schema.
- **Engine:** owns dice, resolution, rules, statistics, and pending decisions.
- **AI:** chooses legal actions only; it never owns game rules.
- **API/UI:** transport and display engine-supplied labels, decisions, outcomes, and traces.

The engine must never inspect PDF colors. The UI must never infer rules from prose or raw chart data.

## Intended layout

```text
bowl_bound/
├── bowl_bound/          # Python engine, chart models, rules, AI
├── backend/             # Thin API adapter
├── frontend/            # Adapted web interface
├── tools/               # PDF extraction and validation programs
├── tests/               # Synthetic fixtures and regressions
├── docs/                # Rules decisions, guides, development notes
└── private-data/        # Ignored PDFs, converted teams, local reports
```

## Milestones

### 1. Initialize the standalone project

**Deliver:** initialize local Git, Python package, test/lint setup, README, project guidance, private-data ignore rules, and a record of Paydirt source/license attribution.

**Validate:** package import and smoke test pass; private data is untracked.

**Commit:** `chore: initialize standalone Bowl Bound project`

### 2. Define the initial rules profile

**Deliver:** a rules matrix linking behavior to rulebook sections; explicit choices for optional rules, conflicts, timing, and historical overtime; supported/deferred feature inventory.

**Specification:** [Initial rules profile](../rules-profile.md) defines the selected policies, historical season tables, conflict resolutions, and worked acceptance examples.

**Timing decision:** use standard Bowl Bound chart timing (Option A) initially, including the shortest-applicable-time rule and documented late-half out-of-bounds windows. Alternate and hybrid timing are deferred for consideration in Milestone 22; neither is initially selectable.

**Validate:** review worked examples for timing, penalties, option plays, conversions, and overtime.

**Commit:** `docs: define initial Bowl Bound rules profile`

### 3. Add chart models and exact dice behavior

**Deliver:** typed models for plays, defenses, cells, supplemental columns, PAT outcomes, recovery ranges, and provenance; injectable deterministic dice; versioned in-memory team schema (`schema_version = 1`). The on-disk file format and JSON codec are deferred to Milestone 5c by user decision.

**Validate:** enumerate all 216 offensive and 36 defensive dice combinations; exactly match rulebook distributions; reject invalid data.

**Commit:** `feat: add chart models and Bowl Bound dice`

### 4. Normalize chart-cell semantics

**Deliver:** conversion of text plus color into explicit semantics, preserving signed yardage, parentheses, brackets, out-of-bounds markers, and supplemental references.

**Validate:** synthetic cells distinguish red/green values, white blanks, and black incomplete cells; fumble/interception locations are not incorrectly negated; unknown forms fail clearly.

**Commit:** `feat: normalize chart cell semantics`

### 5a. Create the Python PDF importer CLI

**Deliver:** reusable Python program accepting a PDF or directory, output path, `--dry-run`, and safe overwrite controls. It must issue explicit unsupported-document errors.

**Validate:** test arguments, dry-run, page/team detection, and errors.

**Commit:** `feat: add Python PDF importer CLI`

### 5b. Extract vector chart cells from PDFs

**Deliver:** positioned text, rotation, vector backgrounds, grids, cell coordinates, and merged-background handling. Initially support the digitally generated OSU/Miami layout only.

**Validate:** synthetic PDFs cover rotation, colors, merged backgrounds, blanks, and ambiguity. Never turn missing data into a zero-yard result.

**Commit:** `feat: extract PDF chart cells`

### 5c. Validate and export imported teams

**Deliver:** validated team files written one per team under `seasons/<season>/<team-slug>/` (`--export`) in Paydirt's layout: `offense.csv`, `defense.csv`, `special.csv`, and `team.yaml` (rating, privilege markers, nickname, source hash), plus `seasons/<season>/provenance/<team-slug>.csv` holding each cell's source hash/page/location/text/color evidence. Chart cells use Paydirt notation with Bowl Bound play names; recovery ranges and dedicated PAT outcomes are included. Folder names are lowercase hyphenated slugs. `seasons/` is git-ignored and not packaged. See [Team file format](../team-bundle.md).

**Validate:** incomplete charts and invalid semantic combinations are rejected; output refuses overwrite without explicit approval.

**Commit:** `milestone 5c: validate and export imported teams`

### 5d. Batch import (moved to Milestone 25)

Deferred by decision. See Milestone 25. The importer processes one PDF per run until then.

### 6. Verify the OSU/Miami importer output

**Deliver:** locally import the supplied two-team PDF and independently reconcile all positions. Use the reusable verification report in `tools.pdf_import.verification` to check exported structure and record corrections/evidence privately under ignored `private-data/verification/`. Do not commit the PDF, converted team files, or detailed report.

**Validate:** reconcile the complete chart and PAT coordinates, recovery ranges, ratings and printed markers against independently recorded private expectations. Keep all historical-team values and detailed comparison results private. Run the public synthetic verification checks documented in [import verification](import-verification.md).

**Commit:** `test: add import verification workflow`

Only tools, synthetic tests, and workflow documentation are committed unless chart distribution rights are confirmed.

### 7. Resolve ordinary plays and priority rules

**Deliver:** offensive/defensive lookup, numeric combination, priority overrides, incompletions, and structured lookup traces.

**Validate:** exhaustively test every offensive-row × defensive-column intersection on the published Priority Chart, including blank/incomplete cells, signed numeric values, parentheses, brackets, TD, B/QR/QT, interceptions, and fumbles. Maintain an independently transcribed expected-result matrix, not expectations generated from the resolver’s implementation table. Parameterized tests must identify each chart coordinate and assert the exact outcome/operation, selected source, and structured trace; no skipped intersections. Test special SOP/BLP and penalty override rows explicitly, using deferred-resolution facts where full execution belongs to later milestones. Add boundary/value tests for comparisons and special fumble/interception locations in addition to the matrix. Use only synthetic cells and document any rules-profile corrections to the printed chart.

**Commit:** `feat: resolve ordinary plays and priority rules`

### 8. Resolve option and supplemental results

**Deliver:** Breakaway, QR, QT, and Option-to-SOP/BLP resolution. Preserve both called and resolved play classifications.

**Validate:** cover every branch and defense-retention/cancellation rule.

**Commit:** `feat: resolve option and supplemental results`

### 9. Add basic game-state transitions

**Deliver:** possession, field position, downs, distance, first downs, turnovers on downs, and engine-owned descriptions.

**Validate:** test midfield, goal-to-go, fourth-down, and end-zone boundaries plus state invariants.

**Commit:** `feat: apply basic game-state transitions`

### 9b. Add team roster files for commentary

**Deliver:** an optional per-team `roster.json` in Paydirt's format, beside the team's other files (`seasons/<season>/<team-slug>/roster.json`). It holds player-name lists by position (`qb`, `rb`, `wr`, `te`, `ol`, `dl`, `lb`, `db`, `k`, `p`, `kr`) and is used only to name players in engine-generated commentary. Add a strict loader in `bowl_bound` (unknown keys, wrong types, and non-string names are rejected). A missing roster is not an error: the engine falls back to generic wording such as "The quarterback". Document the format next to the team file format, and write a short workflow for creating rosters for the teams being play-tested (Ohio State and Miami 2002 first).

**Constraints:** the PDF importer does not produce rosters. Player names come from historical rosters published on the internet, gathered by hand or by a small helper script for the teams being play-tested. For each roster, record where it came from (the page and the date retrieved) in a `roster-sources.md` note next to it, so a name can be traced and re-checked. Do not copy a site's page text or layout beyond the player names. Rosters live under the ignored `seasons/` folder, are never packaged, and public tests use synthetic names only; treat them as private by default until redistribution is reviewed. Choosing a name must not consume or perturb the gameplay random stream (Paydirt had a regression in exactly this area), and a name never affects results, state, statistics, or trace rolls.

**Validate:** synthetic rosters load and round-trip; malformed rosters fail with actionable errors that do not echo values; a missing roster falls back cleanly; the same seed produces identical outcomes, state, and statistics with and without a roster (only the wording differs); the wheel-contents test confirms no roster files are packaged.

**Commit:** `milestone 9b: add team roster files for commentary`

This must land before play testing begins (Milestone 10 onward).

### 10. Demonstrate one real engine play in the web UI

**Deliver:** thin API adapter and adapted field, scoreboard, selector, and result components. Labels/actions come from the backend.

**Validate:** browser action resolves a real engine play; no Paydirt labels or client-side football decisions remain.

**Commit:** `feat: connect Bowl Bound engine to web interface`

### 11. Implement Bowl Bound penalties

**Deliver:** rerolls, accept/decline, offsetting fouls, enforcement, pass interference, and rules-profile interpretation of `DEF5X` as `DEF5Y` while retaining source evidence.

**Validate:** accepted/declined results and pending-decision safety.

**Commit:** `feat: implement Bowl Bound penalty procedures`

### 12. Resolve turnovers and recovery chains

**Deliver:** interceptions, fumbles, team-specific recovery, returns, return fumbles, penalties, and end-zone outcomes.

**Validate:** cover offensive/defensive recovery and chained returns without inventing trace rolls.

**Commit:** `feat: resolve turnovers and recovery chains`

### 13. Implement basic special teams

**Deliver:** kickoffs, punts, returns, touchbacks/fair catches, and field goals. Use home-season kickoff placement and free-kick touchback spots from the rules profile; fair catches initially apply to punts, not advanced kickoff options.

**Validate:** orientation, possession, penalties, end-zone behavior, punt markers, and field-goal semantics.

**Commit:** `milestone 13: implement basic special teams`

Implementation and acceptance evidence: [Milestone 13 review](milestone-13.md).

### 14. Implement scoring and conversions

**Deliver:** touchdowns, safeties, PATs, two-point tries, conversion returns, and scoring ledger.

**Validate:** dedicated PAT data is used and score totals reconcile.

**Commit:** `milestone 14: implement scoring and conversions`

Implementation and acceptance evidence: [Milestone 14 review](milestone-14.md).

### 15. Implement timing and regulation flow

**Deliver:** standard Bowl Bound chart timing selected in Milestone 2, timeouts, Hail Mary, hurry-up/spike/kneel, quarter/half transitions, and immutable final state. Implement Bowl Bound procedures rather than copying NFL behavior. Alternate and hybrid timing remain deferred to Milestone 22.

**Validate:** first-down, incomplete, out-of-bounds, penalty, and expiration timing; correct second-half choice; Hail Mary eligibility and every outcome; hurry-up hazards, spike/kneel down consumption, non-stacking clock reductions, and no reopening final games.

**Commit:** `feat: implement timing and regulation flow`

Implementation and acceptance evidence: [Milestone 15 review](milestone-15.md).

### 16. Implement college overtime

**Deliver:** home-season-selected major-college overtime profiles, including historical regulation ties, the 1995 postseason/1996 introduction, the 1997 two-point requirement, and 2019/2021 paired-try changes from the rules profile.

**Validate:** both possessions, defensive scores, repeated rounds, and termination; do not silently apply current NCAA rules.

**Commit:** `milestone 16: implement selected college overtime rules`

Implementation and acceptance evidence: [Milestone 16 review](milestone-16.md).

### 17. Reconcile college statistics

**Deliver:** college-specific rushing/passing/sack accounting and team summaries.

**Validate:** reconcile scripted complete-game sequences; exclude penalties/conversions where required.

**Commit:** `milestone 17: reconcile college game statistics`

Implementation and acceptance evidence: [Milestone 17 review](milestone-17.md).

### 18. Add versioned save/resume

**Deliver:** save/load state including pending decisions and deterministic random state.

**Validate:** resume around penalties, conversions, halftime, and overtime; fail safely for incompatible saves.

**Commit:** `milestone 18: add versioned game saves`

Implementation and acceptance evidence: [Milestone 18 review](milestone-18.md).

### 18a. Harden engine correctness before UI completion

**Deliver:** resolve RULE-002–009: end-zone turnovers and returns, defensive turnover
locations, full-feature ordinary variable yardage, offensive-recovery return fouls,
penalty-decline continuations, and offered-action/period-boundary edge cases.

**Validate:** test each behavior first with synthetic charts and exact dice, checking
state, points, pending choices, statistics, timing and observed traces. Verify save
continuation and explicitly reject pre-hardening replay profiles; run cumulative
Python/API/frontend/build/browser checks without restarting the live backend.

**Scope:** authorized on 2026-10-26 after the full review. Move RULE-002–009 here;
UI, API-001, DEV-001 and the broader refactoring/gate work keep their assignments.

**Commit:** `milestone 18a: harden engine correctness`

Implementation and acceptance evidence: [Milestone 18a review](milestone-18a.md).

### 19. Complete the human-playable UI

**Deliver:** all implemented decisions, halftime, overtime, final statistics, clean new-game state, Bowl Bound branding, and guidance.

**Validate:** browser tests complete real-engine games with either human side; audit reused components for NFL assumptions.

**Commit:** `feat: complete human-playable Bowl Bound interface`

### 20. Add a baseline computer opponent

**Deliver:** legal offensive, defensive, special-team, and pending-decision choices with safe fallbacks.

**Validate:** seeded games complete without deadlocks/illegal actions; AI only sees coach-available data.

Implementation and acceptance evidence: [Milestone 20](milestone-20.md).
The baseline supports concealed simultaneous calls with either human side;
chart-aware policy remains Milestone 21.

**Commit:** `feat: add baseline computer opponent`

### 20a. Add an interactive CLI for play-testing

**Deliver:** a terminal game for the owner’s preferred play-testing workflow, reusing
the engine, baseline coaching coordinator and private save codec. Support normal
team discovery (including both public samples) and human home/away versus computer.
Solitaire only: owner removed two-sided terminal play on 2026-10-27 (CLI-040).
Show engine-owned state, legal choices, results and
optional labeled dice/chart traces. Conceal simultaneous computer/human calls
until resolution; advance computer-only actions automatically and pause for human
input. Support private save/load, useful invalid-input feedback and clean exit.
Do not duplicate football rules or require the browser/web server.

**Validate:** scripted terminal games finish with either human side; compare
commands, scores, timing, statistics, traces and saved continuation with the same
engine/API paths. Check pending penalties, kicks, conversions, overtime, input
errors, EOF/interruption and call privacy using only synthetic/public fixtures.
Document launch commands and an owner play-test checklist. Review suitable Paydirt
CLI ideas without inheriting NFL behavior or adding a runtime dependency.

Scope and acceptance: [Milestone 20a](milestone-20a.md). Added at the owner’s request
on 2026-10-26; Milestone 20 was reviewed/committed before implementation.
The [CLI guide](../cli.md) documents launch, controls and private resume. CLI
checkpoints are committed as `f121c92` and `ec50e1a`. On 2026-10-27 the owner
authorized the documentation handoff commit and proceeding to Milestone 21.
DEV-020 save-cleanup safety and CLI-037 newest-save/picker work remain open
follow-ups, not fixed or closed by this handoff; named commentary is deferred to 21a.

**Commit:** `milestone 20a: add interactive CLI play-testing`

### 21. Add chart-aware coaching and audits

**Deliver:** choice evaluation based on actual Bowl Bound probabilities, options, field position, clock, and score; audit reports. Owner-approved Easy/Medium/Hard difficulty in CLI and browser (Medium default), with unchanged dice odds. Easy-only CLI player coaching and Z toggle must follow the [difficulty contract](difficulty-contract.md). Hard includes weighted individual-play analysis, recent-call variety and committed-public opponent tendencies.

**Validate:** compare against baseline with independent seeds; inspect call variety and repetition as well as scores.

Implementation plan and evidence: [Milestone 21](milestone-21.md), tracked by
[AI-001](issues/AI/AI-001.md), [AI-002](issues/AI/AI-002.md),
[CLI-041](issues/CLI/CLI-041.md) and [RULE-011](issues/RULE/RULE-011.md)
(post-review engine correctness dependency, added under the owner’s High-to-Low
remediation request). Other review follow-ups retain their assigned milestones.
Implemented in the worktree: probability foundation,
isolated engine evaluation, all three difficulty tiers, Easy terminal helper and
[32-game baseline comparison](coaching-audit-m21.md). Final evidence/review and
dedicated milestone commit remain pending. Owner subsequently authorized
Milestone 21a ticket-by-ticket implementation; that direction supersedes the
earlier implementation hold without claiming retrospective Milestone 21 acceptance.

**Commit:** `milestone 21: add chart-aware coaching and audits`

### 21a. Add roster-backed player commentary

**Deliver:** engine-generated player-named commentary using optional positional rosters, with generic wording when a roster or position is missing. Connect roster context to new games and loaded games; the CLI/API/frontend display engine wording rather than assigning players themselves. Use the fictional Cedar Valley and Harbor Tech rosters for public-safe validation. Names are illustrative commentary labels, not player-specific performance or statistics. Never invent a player action that the engine outcome does not establish.

**Validate:** write synthetic tests first for named run/pass and supported special-team/turnover commentary, correct team/position attribution, missing-roster fallback, and CLI output. Same seeds/calls must retain identical outcomes, state, statistics and structured dice traces with or without rosters. Test read-only rendering and save/resume compatibility, including pre-commentary saves; naming must not consume gameplay or coaching randomness. Keep historical rosters private and preserve the existing packaging exclusions unless a separately reviewed change is approved.

Scheduled at owner request on 2026-10-27, after Milestone 21 and before advanced options. The [Milestone 21a task plan](milestone-21a.md) maps CLI-036 and eight focused implementation/verification tickets with dependencies. Owner authorized implementation on 2026-10-28; engine, lifecycle, replay, CLI/API/browser work is committed ticket-by-ticket through `4457887`. Final cumulative validation: 2,231 Python tests at 93.48% branch-aware coverage, 122 frontend tests/build, and 32 real-engine browser tests passed. Owner play-test/acceptance remains pending; automated validation does not close gameplay/UI tickets. Named commentary is not an acceptance requirement for chart-aware coaching in 21.

**Commit:** `milestone 21a: add roster-backed player commentary`

### 22. Add advanced options one at a time

Each is a separate test/review/commit milestone:

1. Wild Card defense and option-specific guesses.
2. QB Sneak and other situational plays.
3. Yardage factors and rating-dependent eligibility.
4. Advanced kicking and block decisions.
5. Consider alternate timing (action + return + dead time) and hybrid timing (standard timing normally, alternate timing in the last two minutes of each half). Review rulebook conflicts, season-profile interactions, and play-count effects before approving either option. If approved, implement each as a separate tested timing profile; otherwise retain standard chart timing.
6. Remaining optional rules, each subject to separate scope approval.

Unsupported options remain unavailable and documented.

### 23. Establish the complete regression gate

**Deliver:** documented workflow for engine, importer, API, frontend, production build, browser tests, full-game simulations, AI audits, and clean-checkout validation.

**Validate:** scheduled games complete and reconcile; synthetic tests cover rare transitions; private checks are separately reported.

**Commit:** `test: establish full application regression gate`

### 24. Prepare GitHub publication

**Deliver:** dependency/security review, attribution, installation guide, release checklist, and private-data audit. Release builds include only the original fictional Cedar Valley and Harbor Tech sample bundles. The owner directed on 2026-10-26 that Ohio State and Miami remain unpublished in game packaging; exclude their charts, provenance and rosters from GitHub release artifacts and runtime bundles. Do not copy the entire local seasons directory. Historical files, the rulebook, source PDFs, saves and detailed reports stay out. See [attribution](../ATTRIBUTION.md) and [sample teams](../sample-teams.md).

**Validate:** fresh checkout builds/runs with the two fictional teams and no private files; inspect built archives/bundles against an exact sample allowlist, explicitly checking that Ohio State/Miami and historical provenance/rosters are absent. Review repository contents and visibility before adding a remote.

**Blocking prerequisite before linking/adding a GitHub remote or publishing:**
[DEV-011](issues/DEV/DEV-011.md) must be resolved: two original, redistributable
synthetic Bowl Bound teams must be created, validated and available in the
`seasons/` layout as the default reusable test/demo teams. This is required even
if its planned Milestone 19 assignment moves. The word "free" in a historical
filename is not sufficient evidence of redistribution rights; any historical
publication remains a separate explicit review.

**Commit:** `chore: prepare initial GitHub publication`

### 25. Add batch import and documentation (deferred from 5d)

Completed 2026-10-30. The parked `wip/5d-batch-import` draft was selectively integrated
and the repaired workflow passed the full milestone acceptance gate. See the
[Milestone 25 work log](milestone-25.md) and [IMPORT-001–009](issue-tracker.md).

**Deliver:** directory processing, per-file status, examples, troubleshooting guide, and isolated PDF-tool dependencies. Fix the open review findings from the draft first:

- A team repeated across PDFs must be refused in every PDF, not only the later ones; this needs a pre-pass that counts keys across all PDFs, and the existing test currently asserts the old behavior.
- `--dry-run` must run the same output checks as the real run, so it cannot report success where the real run fails.
- Rollback must restore bytes directly and survive a failing restore step, so a failure cannot leave a half-restored team.
- Failure reasons must come from a whitelist of safe exception types; everything else gets the fixed message.
- Inspection mode must require a single PDF file, and a symlinked input directory must be refused.
- Add tests for a team repeated in three PDFs, a collision inside one PDF, a non-UTF-8 rollback, and dry-run against an existing target.

**Validate:** batch success, partial failures and overwrite safety, plus the synthetic
collision, dry-run, rollback, diagnostics, input-contract, dependency and release checks
recorded in the milestone work log.

Tracked work: [IMPORT-001](issues/IMPORT/IMPORT-001.md) through
[IMPORT-009](issues/IMPORT/IMPORT-009.md), covering color/provenance integrity,
rollback, collision refusal, dry-run parity, safe diagnostics, input contracts,
the positive batch workflow, documentation/dependency isolation and final
milestone acceptance. See the [Milestone 25 work log](milestone-25.md).

**Commit:** `milestone 25: support batch team PDF imports`

### 26. Support local play-testing from free MaysFootball chart PDFs

Added 2026-10-30 after Milestone 25 acceptance. The owner authorized retrieving the
MaysFootball files listed as free downloads for private exporter testing. This does
not grant redistribution rights: source PDFs, converted historical charts, and reports
remain private and excluded from source control, runtime bundles, and releases.
The owner approved rating 200 as a clearly marked local-only placeholder when a chart
has no numeric rating; printed ratings remain unchanged.

**Deliver:** support the distinct page geometry and metadata used by the MaysFootball
2002–2008 free-download PDFs. Keep each profile explicit and evidence-based. Do not
guess missing cell values or colors. Also create private rosters for every imported team
from public internet sources and record those sources beside each roster. Where reliable
lineup evidence is available, order verified QB, RB, WR, and TE starters first and give
commentary an explicit starter pool so listed reserves are not selected in their place.
Document source limits rather than guessing starter status.

**Validate:** add synthetic PDF regressions before production changes for every newly
supported page profile and metadata rule. Run the exporter against all seven source
PDFs outside ordinary test collection, round-trip every exported team through the team
reader, and verify source provenance and required game data. Confirm each roster is for
the matching season and team; verify starter metadata with synthetic tests and source
evidence. Keep rosters, source URLs/notes, PDFs, converted teams, and detailed reports in
ignored/private locations pending a separate rights review. Re-run the full regression gate
and local real-chart and roster checks before the dedicated milestone commit.

Tracked work: [IMPORT-010](issues/IMPORT/IMPORT-010.md) through
[IMPORT-019](issues/IMPORT/IMPORT-019.md), plus
[FLOW-006](issues/FLOW/FLOW-006.md). See the
[Milestone 26 work log](milestone-26.md).

**Commit:** `milestone 26: support local MaysFootball chart testing`

### 27. Apply play timing automatically and support combined timeout input

Added 2026-10-30 after Milestone 26 play-testing. The owner supplied `7T` as the
expected offense syntax; the matching defense syntax is `AT`. The owner later
directed that normal play timing advance periods automatically, without a separate
no-play runoff choice; kneeldown is the play for intentionally running down time.

**Deliver:** accept a legal human offensive call or defensive formation with an
appended `T`. Apply a requested timeout only when the engine offers it after the
play; otherwise keep the play and use standard timing. Apply standard play timing
automatically and advance quarter, half, game, or overtime boundaries without a
separate normal-runoff choice. Preserve kneeldown as a normal play for running
down the clock.

**Validate:** use synthetic engine, terminal, API, and browser tests for timeout
suffixes, unavailable timeouts, period transitions, halftime, game end, and
invalid suffixes. Verify timing and state parity, no extra snap or dice at a
boundary, and no player-facing runoff or Continue action. Preserve replay
compatibility for existing saved games. Explain timeout syntax only in requested
help output, update player documentation, and run the full regression gate before
the dedicated milestone commit.

Tracked work: [CLI-038](issues/CLI/CLI-038.md) and
[RULE-017](issues/RULE/RULE-017.md). See the
[Milestone 27 work log](milestone-27.md).

**Commit:** `milestone 27: apply play timing automatically`

### 28. Preserve save replay across automatic timing changes

Added 2026-10-31 after an owner-reported saved game from before Milestone 27
failed to resume. Local comparison confirmed that the previous implementation
loads it and that the current replay reaches the same game state; only the
normal-timing method label in the semantic view digest changed from
`clock:runoff` to `standard`.

**Deliver:** keep valid same-profile pre-Milestone 27 saves loadable by verifying
their replay against a narrowly reconstructed legacy digest for normal timing
labels and the removed runoff choice. Check the current digest first, and never
restore the obsolete choice to live controls. Retain integrity, exact chart
fingerprints, command replay, roll consumption, and state validation. Do not
migrate or edit user saves.

**Validate:** add synthetic pre-Milestone 27 saves at both a live scrimmage and a
pending clock choice; they must fail before the fix and load after it. Confirm
malformed digests and incompatible charts remain rejected, then resume the
owner-provided local save without changing it. Run focused save/CLI checks and
the applicable cumulative regression gate. Keep private save files and details
outside tracked tests and documentation.

Tracked work: [CLI-048](issues/CLI/CLI-048.md). See the
[Milestone 28 work log](milestone-28.md).

**Commit:** `milestone 28: preserve pre-timing save replay`

## Decision gates

Before Milestone 3, decide the initial rules profile—especially timing, optional rules, and historical overtime. Chart distribution: the 2026-10-25 owner statement about charts marked free is not a release-packaging instruction. On 2026-10-26 the owner directed that Ohio State and Miami remain unpublished in game packaging. Use only the two original CC0 fictional samples for public game distributions; keep historical teams local-only. Nothing is published before Milestone 24 or without explicit approval.

Roster player names come from historical data published on the internet (decided). Before Milestone 9b, choose which sites to use for each team and confirm that using their data fits those sites' terms. Until rosters are reviewed for redistribution, they stay local-only like the charts.

Before creating a shared Paydirt library, demonstrate a real stable overlap. Prefer small, attributed copied components over premature coupling.

## First target

Complete Milestones 1–2, review the rules profile, then proceed to chart models and exact dice behavior. The PDF importer is deliberately split into Milestones 5a–5c (with batch support deferred to Milestone 25) so it becomes a reusable, tested Python program rather than a one-off conversion.

Full milestone 25/current-alpha review: [2026-10-30 review](full-review-2026-10-30.md).

## Early alpha publication preparation — owner direction 2026-10-28

After M21a implementation/audit commit `d030974`, the owner requested early
GitHub/standalone-release preparation while remaining roadmap work continues.
The [Milestone24 task plan](milestone-24.md) reuses DEV-012/DEV-016 and adds
DEV-033 through DEV-037 for license/version, startup, player documentation,
platform builds and final readiness. MIT is approved; the owner supplied
`bowlboundsupport@gmail.com` as the public bug-report contact.
This changes execution priority, not acceptance of unfinished Milestones22/23.
No remote, tag, push or publication occurs during preparation.
