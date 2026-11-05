# Alpha 5 preparation — Milestone 33

## Scope and authority

On 2026-11-04 the owner authorizes merging and pushing Milestone 33 for build and
release, then explicitly chooses the existing fictional sample teams. Alpha 5
contains only original Cedar Valley and Harbor Tech. Generated season charts,
Milestone 34 research and their announcement remain separate. Historical charts,
PDFs, saves and detailed owner audit reports remain private and excluded.

Release identity: Python `0.1.0a5`, public `0.1.0-alpha.5`. The intended immutable
tag is `v0.1.0-alpha.5`; it has not been created. Remote tag availability must
be verified after connectivity is restored. Do not delete or reuse any tag.

Tracking: [DEV-068](issues/DEV/DEV-068.md). This is preparation, not a completed
release or a replacement for earlier milestone acceptance checkpoints.

At the owner's explicit request, a persistent release goal now tracks this full
sequence through successful upstream native builds, inspected artifacts and the
published immutable prerelease. A candidate commit, stage ZIP or build dispatch
does not complete that goal. Authorization is retained across continuations.

## Paydirt consultation

Reviewed local Paydirt `.github/workflows/release.yml:1-135` and
`docs/dev-notes/release-readiness-2026-11-02.md:1-125` before this release phase.
Adapt version/tag agreement, verified artifact attachment, explicit known faults
and the distinction between engineering tests, calibration and native acceptance.
Do not copy automatic tag publication, unpinned dependencies, optional installer
failure, NFL behavior, private data or runtime dependencies. Bowl Bound's own
approved release manifest and native workflow remain authoritative.

## Integration and review

The candidate descends from cached public `origin/main` at `03d1992`, with
Milestone 33 and owner-playtest follow-ups through `4ca8858`. That code includes
the late-half field-goal range guard, early-down punt guard, pending Hail Mary
labels/context and halftime-style CLI final summaries. The public root remains
the sanitized `239ec044eb2e170bc6b04867e26b03883a7eaad1` lineage.

The unrelated pre-public local `main` is not merged or published. The original
working checkout's uncommitted maintenance ticket/index and active owner game
are preserved. Integration and release metadata are prepared in isolated local
worktrees; no interpreter or owner server is restarted.

Player notes are in [RELEASE_NOTES](../../RELEASE_NOTES.md). Version metadata,
installation examples and existing identity assertions advance together.
The save schema and `bowl-bound-m33-v1` engine profile are unchanged by this
metadata update. The mutable-ref rejection fixture using an older tag is
deliberately unchanged; it does not declare the current application version.

## Verification and limits

The full Python/coverage gate finished on combined `4ca8858`: **3,946 passed,
five failed and six setup errors in 1,018.20 seconds**, with **93.02% branch
coverage**. The committed Alpha 5 candidate
`170f5e053715ae7c5abb5f73a7019f5ce25cda75` was then tested without source changes:
**3,947 passed, five failed and six setup errors in 1,026.89 seconds**, with the
same **93.02% coverage**. Both commands exit 1. The five launcher failures occur
at loopback socket creation with EPERM; six packaging errors share an isolated
wheel fixture that cannot acquire its build dependency. Meeting the coverage
threshold does not make either full gate pass.

Exact command on each corresponding source: supported Python
`-m pytest --cov --cov-report=term-missing -q`. Local Python is 3.12; this does
not certify the workflow's pinned Python 3.13.17 environment.

Completed on the combined integration source:

- Ruff check and format check pass on all 597 Python files; `pip check` passes.
- Fresh lockfile installation succeeds with Node 24.22.1 and npm 11.19.1 using
  the existing verified offline cache. It reports the existing http-proxy config
  warning and deprecated `whatwg-encoding` dependency. Offline install output
  is not a current security-advisory audit.
- Frontend production build passes. Unit execution passes 143 cases; the four
  real-API cases do not run because their server hook times out after EPERM on
  loopback listen. The full frontend command therefore fails, with one unhandled
  server error; no test assertions are weakened and no skips are added.
- Playwright collects 54 cases in ten files. An actual Chromium launch fails
  before assertions because macOS denies MachPort registration. This is not a
  browser pass. UI-054, UI-058, UI-059 and UI-060 remain open for valid browser
  verification and owner acceptance; CLI-058 has the owner's halftime approval.
- GitHub remote/tag queries fail with CONNECT tunnel/HTTP 403. The npm online
  advisory request fails with HTTP 403 and `blocked-by-allowlist`.

Public-history inventory checks 4,421 reachable objects, including 2,383 blobs.
No private-path or PDF objects are found. The credential-pattern scan has no
private-key, GitHub-token or AWS-access-key matches. Forty-seven documentation
blob versions contain local host-path references, reviewed as source/tool command
references rather than copied private material. Pattern scanning alone does not
establish a complete secret audit. No detailed owner evidence is added.

The Alpha 5 focused metadata/launcher/docs/issue/packaging/workflow selection
passes 88 cases and fails five launcher cases because loopback socket creation
is denied with EPERM. These failures precede launcher behavior and reproduce the
same environment restriction as the frontend real-API tests; they remain failed
checks and are not skipped. The changed version assertions pass.

The exact-stage build exposed [DEV-069](issues/DEV/DEV-069.md): the allowlist
omitted `HalftimeReview.jsx`, although App imports it. A new staged-local-import
regression fails on precisely that missing component before adding its exact
manifest entry. All 40 packaging cases then pass. A new metadata, player-doc,
workflow, standalone-build/smoke and tracker selection passes 127 cases. The
misspelled optional native-test path collected no tests and is not counted.

A fresh stage now clean-installs from the locked verified offline cache, builds
the real frontend, assembles Alpha 5 runtime inputs, imports backend/launcher/CLI
without checkout fallback and verifies the archive/hash inventory. Runtime
inventory has 75 selected files; the seasons selection has exactly the 15 pinned
original fictional sample files. This is a native-builder input ZIP, not a
finished standalone executable or a release artifact. No existing build output,
worktree dist or node_modules was copied into the stage.

On this Alpha 5 worktree, a second clean lock installation and full-source build
also pass. Frontend unit execution again reports 143 passed and four not run due
to the same EPERM server setup, one unhandled error and its 20-second timeout;
the command exits 1. Ruff lint/format on 600 files and pip check pass. Fresh
Git fetch and Alpha 5 release/tag API checks still return HTTP 403, so current
upstream/tag availability cannot be certified. No push or dispatch was attempted.

Supplemental wheel verification uses an immutable archive of `170f5e0`, with
network disabled and the already cached setuptools 84.2.1 wheel supplied only to
that child process. All seven unchanged `tests/test_packaging.py` cases pass.
The cached wheel SHA-256 is
`ca140b45d5325a9478f880e351484f62fef15f336462e449ca0c03c873d589c2`.
This diagnoses the build-dependency acquisition failure; it does not replace the
failed full gate or certify the pinned native dependency environment.

The assembled runtime also completes two isolated public-fictional games, with
Hard v15 controlling opposite sides and seeds 101/307. There are 172/166 committed
plays, four reconciled 900-second periods per game, eleven successful strict
save/replay checkpoints and no missing runtime imports. A temporary probe's first
attempt incorrectly summed nominal timing charges; the corrected probe measures
actual before/after elapsed time, respecting quarter-boundary clamping. The
initial failed probe remains recorded. No engine code or test expectation changes.
These are packaging smoke checks, not historical calibration or native acceptance.

All 97 selected stage source inputs match the committed candidate byte for byte.
The 18-file candidate delta is reviewed without private charts, PDFs, saves or
credential-pattern findings. The original 15 sample hashes remain unchanged.

After the owner's explicit commute pause and resume, bounded probes at
2026-11-05 00:18 UTC reproduce GitHub CONNECT tunnel 403, npm audit 403
`blocked-by-allowlist`, loopback EPERM and Chromium MachPort error 1100 before
browser assertions. No full gate is needlessly restarted under unchanged
restrictions. No running regression process remains. The release goal remains
unfinished; publication authorization persists.

Detailed logs and scan receipts remain ignored under `private-data/`.
CLI-072 remains a known minor commentary follow-up; it does not alter the
football result. The owner audit is game-specific evidence, not historical
chart calibration or full release acceptance.

## Remaining authorized steps

1. Candidate `170f5e0` contains the tested metadata and exact-manifest fix;
   DEV-069 is resolved against that reference and remains unclosed pending native
   acceptance. Keep DEV-068 open until all remaining release steps succeed.
2. In an environment that permits the required services, run the established
   complete gate in `.github/workflows/tests.yml`: pinned Python 3.13.17 and
   Node 24.22.1, Python coverage/lint/dependencies, clean frontend install,
   unit/build/online audit, and real-engine Chromium tests. Resolve failures and
   selected release acceptance before pushing; collection is insufficient.
3. Fetch upstream refs and tags, verify the candidate is a descendant of current
   public main and Alpha 5 is unused, and reconcile any new upstream changes.
   Publish the reviewed candidate without force or pre-public history.
4. Dispatch the manual `Standalone release build` workflow on main, supplying
   the approved full 40-character source SHA as `source_ref`. Build dispatch
   does not itself create a tag or GitHub release.
5. Verify macOS arm64, macOS x86_64 and Windows x64 artifacts, checksums,
   installer/extracted-executable smoke results, license and required native
   acceptance. Only then create the unused immutable Alpha 5 tag and publish
   the reviewed release assets. Record actual URLs and tested source SHA.

The owner's authorization is already recorded. Outstanding work is technical
verification and access, not an additional publication permission request.

## Main-thread publication continuation

After the owner restarted execution with full access, GitHub git/API and local
server probes pass. Publication remains authorized from the main thread. A fresh
Python 3.13.17 environment and Node 24.22.1 use the established workflow commands.

Before the release-check repair, reconsulted Paydirt `tests/test_save_game.py`
and `paydirt/save_game.py`: adapt explicit round-trip state assertions, not its
NFL state or looser save compatibility. Bowl Bound retains strict Python-minor
compatibility. DEV-070 reproduces a synthetic fixture's 3.12 envelope rejection
on the pinned 3.13 runtime. Reusing the existing legacy-fixture runtime adapter
changes only test envelope metadata/integrity; original fixture bytes, chart facts,
rolls, digest checks and replay assertions remain unchanged. The unchanged
cross-minor rejection test remains required. All 79 focused save tests pass.

DEV-071 reproduces an older manual complete-game browser driver timing out at
the new halftime review. The page correctly disables kickoff until START 2ND HALF;
the driver omitted that acknowledgement. Adapt the existing M20 driver's
engine-provided review action, preserving complete-game score/statistics/state
assertions and existing timeouts. No frontend or engine behavior changes.
Interrupted preliminary full runs are retained privately and are not counted
as passing gates. Fresh complete gates follow the fixes.

After the fixes, all 54 real-engine Chromium cases pass in 3.9 minutes, including
manual and computer complete games, halftime, pending saves and invalid-save
protection. All 147 frontend unit cases pass, production build succeeds, and the
online npm audit reports zero vulnerabilities. Installation retains the existing
`whatwg-encoding` deprecation notice. Ruff/pip checks pass. The final complete
Python/coverage gate is still running; the earlier interrupted run is not a pass.

DEV-070 follow-up inventory finds the same strict-runtime envelope in CLI-067
and all four CLI-069 stages. Their unchanged tests reproduce five failures
before using the existing adapter. All 168 save/context/Hail Mary/zero-choice
regressions then pass on Python 3.13.17; all five legacy-stage cases and explicit
cross-minor rejection pass on Python 3.12.8 (six tests). Original fixture files,
recorded state/dice and production save policy remain unchanged.

## Restored-access local acceptance — 2026-11-04

The complete pinned-runtime gate on implementation `94e6ecb` now passes:

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **3,958 passed
  in 787.96 seconds**, **93.35% branch-aware coverage**, unchanged 75% floor.
  No Python skips or warnings are reported. Earlier interrupted runs are not
  counted as passing and remain available privately.
- Ruff check/format pass on all 602 Python files; `pip check` passes.
- Node 24.22.1/npm 11.19.1 clean lock install, all 147 frontend tests, production
  build and online npm audit pass; audit reports zero vulnerabilities.
- All 54 real-engine Chromium cases pass in 3.9 minutes. The installation's
  existing `whatwg-encoding` deprecation and Vitest's jsdom environment performance
  advisory are retained, not suppressed. These are not failed tests or skips.
- All 168 focused legacy-save/context/Hail Mary regressions pass; six explicit
  legacy-stage/cross-minor cases also pass on Python 3.12.8. Fixture metadata is
  adapted only in tests; production runtime rejection stays strict.
- Tracker/player-doc/priority-doc checks pass 22 cases after ticket maintenance.

DEV-070/DEV-071 and UI-054/UI-058/UI-059/UI-060 have committed implementations
and valid engineering/browser verification; they are resolved pending owner
play-test closure. The owner's earlier CLI halftime confirmation is retained.
CLI-072 remains the disclosed minor QB Sneak commentary follow-up.

The current sanitized implementation history has 4,487 reachable objects and
2,417 blobs, with no private-path or selected credential-pattern findings. Its
root is still `239ec044eb2e170bc6b04867e26b03883a7eaad1`. All 15 approved sample
hashes, native dependencies and native notice catalog match Alpha 4. The Alpha 4
release commit is a parallel metadata-only child of public main; its release
notes are already preserved byte-for-byte and its immutable tag is retained.
No pre-public history or chart-research branch is merged. New changes after
`94e6ecb` record acceptance/ticket metadata only.

Fresh GitHub git/API probes succeed; upstream main remains `03d1992` and Alpha 5
is unused. Owner publication authorization remains explicit. Push the reviewed
sanitized descendant without force, then run the manual three-platform workflow
at its full immutable source SHA. Native verification and public publication
remain outstanding at this checkpoint; broader native/legal audit tickets are
not silently closed by source tests or an unchanged catalog.
