# Milestone 25 draft and current alpha preparation review — 2026-10-30

## Scope and conclusion

The requested milestone number and public release lineage differ. GitHub main is
`3f46558` at immutable prerelease `v0.1.0-alpha.1`, with release preparation
assigned to **milestone 24**. Milestone **25** is batch PDF import, still
parked locally at `2822c3b` on `wip/5d-batch-import`. Reviewed the complete
five-file draft change, current importer behavior and tests, the alpha release
lineage, and the player documentation. The review covers both sets explicitly
rather than treating the draft as merged or complete.

Milestone 25 is not ready for acceptance: the batch draft still fails its
documented safety requirements. Milestone 24 produced verified alpha 1 native
artifacts and a public prerelease, while the review found follow-up manifest,
launcher, documentation, coverage and frontend-test issues for later repair.
No new engine gameplay change is introduced by this review.

Review changes are tickets and developer notes. Existing local `opencode.json`
edits are outside this review. All reproductions use synthetic fixtures or the
two authorized fictional samples; no historical files were inspected or changed.

## Paydirt references and applicable findings

Consulted the local Paydirt repository before reviewing implementation:

- `docs/chart-generator.md` and `extract_charts.py`: directory import and
  per-file status, but existing output can be partial and batch exit status
  does not prove success. Retain Bowl Bound's stronger per-PDF transaction,
  refusal, safe-diagnostic and aggregate-exit requirements; do not reuse the
  Excel layouts, legacy names/default directories or broad exception fallbacks.
- `docs/installation.md` and `docs/playing.md`: task-oriented installation and
  controls are useful models for the shorter player path. Do not import NFL
  options or use its broader quarantine command as a Bowl Bound default.
- `paydirt/packaging.py` and `tests/test_packaging.py`: separate bundled
  resources from writable user data and test platform paths. Adapt the
  separation as a design/test idea; Bowl Bound's explicit external library
  contract remains authoritative, with no new merge/discovery behavior.

No Paydirt code, chart data or runtime dependency was added.

## Findings and tickets

| Ticket | Priority | Finding / suggested change |
| --- | --- | --- |
| [IMPORT-003](issues/IMPORT/IMPORT-003.md) | High | Reject every PDF sharing a canonical team key; the current test asserts the first-winner defect. |
| [IMPORT-004](issues/IMPORT/IMPORT-004.md) | Medium | Share side-effect-free destination preflight between dry-run and export; simplify planning with typed records. |
| [IMPORT-005](issues/IMPORT/IMPORT-005.md) | High | Use safe owned error types/reason codes instead of printing arbitrary ValueError/OSError messages. |
| [IMPORT-006](issues/IMPORT/IMPORT-006.md) | Medium | Refuse symlinked input directories and require a file argument for inspection. |
| [DEV-045](issues/DEV/DEV-045.md) | Medium | Provide one short player quick start; move optional setup and technical importer detail to references. |
| [DEV-046](issues/DEV/DEV-046.md) | Low | Remove version/profile/tag and coaching-weight internals from player explanations. |
| [DEV-047](issues/DEV/DEV-047.md) | Medium | Print/open a URL that matches the explicit bound host. |
| [DEV-048](issues/DEV/DEV-048.md) | Low | Share launcher policy while preserving intentional API-only and production differences. |
| [DEV-049](issues/DEV/DEV-049.md) | Medium | Reject manifests that omit required sample/runtime components, even when the remaining hashes agree. |
| [DEV-043](issues/DEV/DEV-043.md) | Medium | Exercise release CLI/refusal paths and enforce separate packaging coverage in cumulative checks. |
| [DEV-044](issues/DEV/DEV-044.md) | Medium | Await React coaching updates through their visible result; remove act warnings without suppression. |

All 11 new tickets were created with `scripts/create_issue.py:create_issue`.
Importer work belongs to milestone 25; alpha fixes/docs to unfinished milestone
24; general frontend test hygiene to milestone 23. Each ticket has concrete
acceptance checks. No ticket is marked resolved from an uncommitted review.

Existing [IMPORT-002](issues/IMPORT/IMPORT-002.md) was updated and raised to High:
two reproduced rollback failures leave earlier files replaced after an import
fails. Reuse that ticket instead of duplicating its existing rollback scope.
The suggested simplification is a byte-oriented atomic-write helper plus
explicit recovery bookkeeping, with every recovery attempted independently.
DEV-036 and DEV-037 were completed on the public alpha 1 lineage with verified
three-platform builds and publication audit evidence. Existing broader gate
work remains assigned to DEV-004; the packaging/docs inconsistency in DEV-009
remains open.

## Reproduction evidence

Seven independent expected-behavior probes fail against the unchanged draft:
three-PDF collision, dry-run/existing target, non-UTF-8 restoration, failure of
one restoration, generic ValueError redaction, symlinked input directory and
single-PDF-directory inspection. The four shared dry-run/rollback/redaction
probes also fail on main. These corroborate documented draft blockers; they
are not claimed as seven newly introduced main-branch regressions.

A fifth main-branch probe mocks the listener/server and requests the explicit
documentation-only address `192.0.2.10`. The launcher advertises `127.0.0.1`
instead. No external listener was opened for this reproduction.

For manifest completeness, a source copy was made using the exact public
allowlist. Removing `seasons/2007/cedar-valley/special.csv` from both the
manifest inventory and sample hash map still permitted staging, synthetic UI
assembly and archiving. The resulting `/api/teams` listed only Harbor Tech.
This tests an accidental manifest omission, not deliberate hash-receipt forgery.

Temporary failing probes are outside ordinary test collection under
`/private/tmp/bb-review-2026-10-30/`. Tickets describe their construction so
the evidence does not depend on retaining temporary files. No existing test
assertion was weakened, skipped or changed.

## Validation

Commands below use the project `.venv/bin/python`; draft commands ran in its
existing clean worktree with that interpreter. Frontend commands selected the
installed Node 24.22.1/npm 11.19.1 binaries on PATH.

- Draft: `python -m pytest tests/test_pdf_batch.py tests/test_pdf_cli.py
  tests/test_pdf_cli_export.py tests/test_export_hardening.py -q
  --cov=tools.pdf_import.cli --cov-report=term-missing --cov-fail-under=0`:
  **82 passed**, **95%** rounded CLI coverage. Passing tests miss the safety
  requirements above; the focused measurement is not the cumulative floor gate.
- Release script: `python -m pytest tests/test_release_package.py
  tests/test_release_archive.py --cov=scripts.release_package
  --cov-report=term-missing --cov-fail-under=0 -q`: **27 passed**, **80.06%**
  branch-aware coverage. The normal application coverage source excludes scripts.
- Frontend: `npm test -- --reporter=dot`: **122 passed**, with repeated React
  act warnings and jsdom performance advice. `npm run build` passed.
- `python -m ruff check .` and `python -m ruff format --check .`: passed
  (360 formatted files at the initial review checkpoint).
- `python scripts/build_issue_index.py` and `python -m pytest
  tests/test_issue_tracker.py tests/test_create_issue.py
  tests/test_release_player_docs.py -q`: **35 passed** after ticket creation.
- Full Python coverage and real-engine Chrome regression results are recorded
  at the final review checkpoint below. Native Windows x64, macOS arm64 and macOS Intel execution was established
  later on the public alpha 1 lineage; the initial review checkpoint predated those runs.

The sandbox blocked a temporary pytest ancestor scan and the browser test
server's localhost bind. Scoped probes and browser tests were rerun with
approved access. Environmental failures are distinguished from assertion failures.

## Duplicate audit and final checkpoint

Reviewed the full existing ticket inventory and compared the candidate findings
with the relevant ticket bodies before finalizing. No separate rollback,
native-build or network-sensitive wheel-test ticket was opened: IMPORT-002,
DEV-009 retains that existing wheel-isolation work; DEV-036 is complete on the public alpha 1 lineage.

Related umbrella tasks have reciprocal links to narrower new findings:
DEV-035 to DEV-045/046 (editorial follow-ups), DEV-034 to DEV-047/048
(specific launcher defect/simplification), DEV-012 to DEV-049 (sample omission
validation), and DEV-004 to DEV-043 (packaging coverage integration). The
unified gate remains DEV-004's scope. DEV-044 addresses existing React test
completion warnings, distinct from DEV-006's Python lock/fixture issues and
UI-038's missing browser behaviors. All 11 new tickets remain open; none is a
second ticket for the already tracked rollback or native-build blocker.

- Full Python command: `.venv/bin/python -m pytest --cov
  --cov-report=term-missing --cov-report=json:/private/tmp/bb-review-coverage.json
  -q` ran all **2,275** cases: **2,267 passed**, three localhost-bind failures
  and five wheel-fixture errors from sandbox restrictions, in **462.95s**.
- Approved rerun: `COVERAGE_FILE=/private/tmp/bb-review-2026-10-30/main.coverage
  .venv/bin/python -m pytest tests/test_launcher.py tests/test_packaging.py
  --cov --cov-append --cov-report= -q`: **19 passed**, including all eight
  blocked cases. No code was changed between these runs. Thus every existing
  Python case passed across the full run and targeted environmental rerun;
  this was not a single uninterrupted green full-suite invocation.
- After appending that rerun, `coverage report
  --include='backend/*,bowl_bound/*,tools/*' --fail-under=75` reports
  **93.38% branch-aware application coverage**, launcher **84%** rounded.
  Application/script runs initially shared the default coverage file, so the
  final report explicitly selects the configured application source packages;
  the separate script JSON reports **80.06%**. These percentages are not mixed.
- `BB_E2E_CHANNEL=chrome
  BB_E2E_SEASONS=/private/tmp/bb-review-2026-10-30/e2e-seasons
  npm run test:e2e -- --reporter=line`: **32 passed in 3.6m**, no test retries
  or skips. This includes complete games, reconciliation, overtime and
  save/load against the real engine and the fresh production build. A Node
  NO_COLOR/FORCE_COLOR environment warning was reported.
- Focused frontend warning check: `npm test -- src/test/coaching.test.jsx
  --reporter=dot`: **22 passed**, **49 act warnings** across seven contexts;
  tracked in DEV-044, not suppressed.
- `npm audit --json` with the pinned frontend toolchain: **0 vulnerabilities**
  across production and development dependencies. The first attempt was blocked
  by sandbox DNS access; the approved registry query completed successfully.
- Final index regeneration and ticket/document tests: **35 passed**. All
  **51** local Markdown links checked in the review, roadmap/milestone notes
  and new/updated review tickets resolve; `git diff --check` passed.

The intentionally failing review probes establish the ticketed gaps despite
the existing regression suite passing after environmental reruns. Native build
and publication-history acceptance are recorded in milestone 24. The review
itself claims no new gameplay play-test closure.
