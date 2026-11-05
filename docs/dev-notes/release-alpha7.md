# Alpha 7 visual-chart candidate

Status: corrected candidate local acceptance complete. DATA-039's correction is
independently accepted and public; all markers remain faithful to the loaded CSV.
The dedicated release branch and exact-SHA native build are authorized after the
completed full gate and review. Alpha 7 tag/release publication remains coordinated
after Alpha 6's actual release/Latest. Owner play testing continues on preview 8143.

## Exact source and scope

Start from public origin/main `9a2897f7d45d9b2b6c48fc21fd311b02562d788b`,
verified with git ls-remote before worktree creation. This includes the complete
approved Alpha 6 catalog, M39 displaced-try analysis fix and public M40/DEV-073
native discovery deadline fix. Do not substitute the owner's private local main.

Merge only reviewed M38 and canonical M41 viewer work from
`eb2ebcd41449ff09a7ae85fbd6a489c051cc3a55`. Original tested implementation
commits `39a0e84e319094cd44fb5811447f0299edfed06c` and
`92fc811dafd6c56cabcb554451f43d2aa45bd42a` remain ancestors.
The numbering-correction commit preserves their hashes and historical labels.

In the initial integration, only the generated issue index conflicted; rebuild it from the merged ticket
files, retaining public DEV-073/M40 and separate UI-061/M38 and UI-062–069/M41.
No production source conflict or imported football-rule change occurred.
The public M40 notes remain the native-catalog fix; viewer notes use M41.

The candidate bumps coordinated Python/public/frontend versions to 0.1.0a7 /
0.1.0-alpha.7, leaving the existing engine profile/save schema unchanged.
Version tests first fail twice on the unchanged a6 implementation, with 15
passing controls; the required change is release identity only. Synthetic native
smoke fixtures may retain a6 as an arbitrary fake API version.

## Guidance and provenance

Reviewed the candidate's AGENTS.md, exact release manifest, Alpha 6 acceptance
record, player packaging/documentation tests and native discovery fix.
Reconsulted Paydirt `.github/workflows/release.yml`,
`tests/test_release_metadata.py` and
`docs/dev-notes/release-readiness-2026-11-02.md`. Adapt coordinated version
validation, separate build/publication stages and reconciled complete-game
evidence. Keep Bowl Bound's own exact manifest, generated-catalog rights scope
and native-smoke guards. Reuse no NFL behavior, private chart data or runtime
Paydirt dependency.

The generated catalog is byte-for-byte the reviewed public Alpha 6 set; no new
team, roster, provenance permission or source-data scope is added. Preserve
all three local previews on ports 8139, 8140 and 8141. Port 8141 is the owner's
rapid full-catalog play-test server and is not restarted by this work.

## Validation

Focused integration checks and one established full baseline gate are complete
on the full viewer candidate. They verify frozen CSV cells, full 10–39 desktop
fit, closed help, shared Priority, safe detached views, save/game purity and
retained exact 118-team packaging. Corrected-data acceptance remains on hold. Native multi-platform artifacts/publication are later steps
after owner play testing and root coordination.

## Owner board-style follow-up

Before the integration gate completed, owner layout references added prominent
formation groups, boxed dice totals, strong chart colors, Running1–4 / Option5 /
Passing6–9 headers, separate supplemental offense columns, and Special Teams.
UI-066–069/M41 track these new presentation objectives, including prominent
new-tab/window launchers. The first integration
gate was interrupted deliberately after 35 browser checks passed; remaining
checks and partial Python coverage are not acceptance. Renew the final gate
after all follow-ups are integrated. Preserve the baseline logs.


Board-style follow-up implementation `d2222beca34c4392285e14f953b7f523da57eb4d`
and acceptance `efa9fbc5b96f46100cbaca925a24c2531ed09f77` are integrated in
`2bb082a521c98e365898268d2a6402ce96bb05b2`. Follow-up conflicts were only the
generated issue index and an appended notes link; retain both notes sections and
regenerate the index. Root read-only review found no blocking issues. All new
UI-066 through UI-069 tickets are resolved awaiting owner play testing.

The matched candidate backend and production bundle are ready for a new port-8142
preview; the older three preview processes/bundles are preserved. Focused follow-up
checks pass: 434 Python/metadata cases, 157 frontend cases and 10 real-engine
browser cases. These cover every displayed frozen cell, 30-row geometry, aligned
supplemental tables, formation/dice semantics, Special Teams/PAT facts, context-
correct BLACK help, secure prominent launchers and unchanged game/save state.
The renewed full candidate gate runs after this complete implementation.


## Renewed final gate evidence

Candidate implementation under test: `2bb082a521c98e365898268d2a6402ce96bb05b2`.
Root independently reviewed source and the matched 1440-pixel offense, defense
and Special Teams screenshots; no blocking code or visual findings. The port-8142
preview exposes the full 118-team catalog for the owner's new play test. The
previous preview games remain live; no publication has occurred.

Completed checks:

- Frontend: 157 tests, production build, npm audit with zero vulnerabilities.
- Standard real-engine Chromium gate: all 64 cases pass in 4.2 minutes, no skips.
- Repository-wide Ruff check and format: 632 files formatted; pip check passes.
- Documentation/metadata follow-up: 22 checks pass; diff check passes.
- Fresh exact source staging, pinned clean frontend build, runtime assembly and
  deterministic archive creation pass. Runtime inventory contains 658 files and
  exactly 118 team bundles. Season catalog/source contents are unchanged from
  public `9a2897f`; no private historical import, roster or log is added.
- Isolated Python `-I` runtime imports are asserted to originate in the staged
  runtime, outside checkout imports. Exact catalog/UI/assets plus a real snap
  and strict save/load for all 118 teams pass. Reading all 236 home/away frozen
  chart books leaves saves unchanged; offense/defense/ST/Priority dimensions
  and Special Teams' context-specific BLACK legend are verified.
- The actual staged production bundle passes Chromium inspection at 1280×1000:
  all 30 rows, no inner vertical overflow, initially closed help and a secure
  independent Special Teams tab. This checks the exact build-stage assets.

Private validation artifacts are outside the repository in
`/private/tmp/bb-alpha7-final-verification/`; the runtime archive SHA-256 is
`d1f16c1cb56c92afef9157a72aa5f1146168800fb363c01ef004676a974f5bf9`.
Original fictional CSV screenshots and geometry are retained only under ignored
`private-data/alpha7-charts/`. They confirm aligned main/supplemental rows, strong
normalized fills, large formation letters, closed help and prominent launchers.
No reference chart image or screenshot is committed.

Observed advisories: npm's existing whatwg-encoding deprecation during clean
stage install; Vitest's repeated-jsdom performance advisory; Playwright's existing
NO_COLOR/FORCE_COLOR environment warning. No warnings are suppressed. Full Python baseline gate: 4,003 passed in
877.52 seconds (14m37s), 93.41% branch-inclusive coverage (75% minimum). No skips
or pytest warnings. This completes the viewer baseline, not corrected-data
acceptance.

Commands (Node 24.22.1 on PATH):

```sh
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pip check
npm test --prefix frontend
npm run build --prefix frontend
npm audit --prefix frontend
BB_E2E_SEASONS=/private/tmp/bb-alpha7-final-e2e-seasons npm run test:e2e --prefix frontend
.venv/bin/python scripts/release_package.py stage /private/tmp/bb-alpha7-visual /private/tmp/bb-alpha7-final-verification/stage
.venv/bin/python scripts/release_package.py frontend /private/tmp/bb-alpha7-final-verification/stage
.venv/bin/python scripts/release_package.py runtime /private/tmp/bb-alpha7-final-verification/stage /private/tmp/bb-alpha7-final-verification/runtime
.venv/bin/python scripts/release_package.py archive /private/tmp/bb-alpha7-final-verification/runtime /private/tmp/bb-alpha7-final-verification/runtime.zip
.venv/bin/python -c "import runpy; runpy.run_path('private-data/alpha7-validation/smoke_staged.py', run_name='__main__')"
.venv/bin/python -c "import runpy; runpy.run_path('private-data/alpha7-validation/check_staged_ui.py', run_name='__main__')"
.venv/bin/python scripts/build_issue_index.py
.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_release_player_docs.py tests/test_release_metadata.py -q
git diff --check
```


## Generated-catalog marker audit hold

Owner play testing found nearly every ordinary numeric offense entry marked
out of bounds. Root confirmed that the loaded normalized facts and viewer match
the generated CSV; the generator is auditing DATA-039. Do not remove markers in
presentation or change football behavior to conceal data semantics. Preserve the
port-8142 preview and existing games while the current Python baseline finishes.

The exact staging/archive and 118-team checks above validate the pre-audit
catalog structurally; they are not corrected-data acceptance. Publication is
held, including Alpha 6 tag/release, pending independently validated corrected
catalog source and root coordination. Any corrected catalog requires fresh
manifest/package verification and applicable complete release gates; treat the
current archive as superseded for release after that change.


## Baseline handoff

All established viewer/integration checks above completed successfully before
this documentation-only checkpoint. Program source remains
`2bb082a521c98e365898268d2a6402ce96bb05b2`. Original viewer tested hashes and
canonical numbering are preserved, and public DEV-073/M40 remains unchanged.
UI-062 through UI-069 are resolved with tested references and await owner
play-test confirmation before closure. DEV-074 stays open for DATA-039,
corrected-catalog validation and later release coordination.

No push, main merge, remote build dispatch, tag or publication was performed.
The port-8139, 8140, 8141 and 8142 previews and their games remain available;
only the agent's temporary geometry server on 8144 was stopped.


## Corrected-catalog integration phase

Root accepted DATA-039 after independent all-116 semantic/216-outcome/source
support checks, corrected current-engine timing/coaching/replay review across
128 distinct games plus two repeats, and the renewed Alpha 6 full gate. Public
source `a95ded69082e5e65833c93d3321630bb515e49d8` was verified with git ls-remote
and fetched from origin/main before integration. No private generator history or
code is imported. The corrected 116 teams and two samples retain the catalog
scope; only approved numeric-cell out-of-bounds markers/provenance hashes and
public-safe records change. Alpha 7 retains its viewer and coordinated a7 identity.

Reconsulted Paydirt `.github/workflows/release.yml`,
`tests/test_release_metadata.py` and the 2026-11-02 release-readiness notes before
this integration phase. Adapt exact version/source checks, separate build and
publication, and reconciled validation evidence. Bowl Bound's own manifests,
permissions and college rules remain authoritative; reuse no Paydirt data,
private audit records or NFL behavior, and add no runtime dependency.

The previous pre-audit archive remains historical baseline evidence only. Renew
one complete final candidate gate and assemble a fresh corrected exact runtime;
no redundant complete-game cohort is needed if football application sources are
byte-identical to the accepted Alpha 6 source. Preserve ports 8139–8143 and every
existing game. Source/native publication awaits Alpha 6 completion and root
coordination while the owner uses corrected preview 8143.


Only the generated issue index conflicted when merging the accepted correction;
regenerate it from the combined public DATA-039 and M38/M41 tickets. All accepted
sample/generated resource pins match public `a95ded` exactly. The only additional
manifest entries remain the reviewed `bowl_bound/chart_view.py` and
`frontend/src/components/ChartViewer.jsx`.

Application comparison against accepted Alpha 6 confirms all common Bowl Bound
module bytes match except coordinated `__init__.py` version metadata and
`save_game.py`'s reviewed read-only chart accessor. The added chart presenter and
web API/display are covered by the renewed viewer gate; no football rule, dice,
clock, AI, chart normalization or gameplay state-transition source changed. The
accepted broad corrected-data game/timing audit therefore applies without
repeating its 128 games.


## Corrected candidate package and review

Integration source: `93765b96e8c04e60254df40138cf3b53bbcb405d`, preserving exact
public correction `a95ded69082e5e65833c93d3321630bb515e49d8` and reviewed viewer
history. The complete seasons tree equals that public correction byte for byte;
only the two approved chart-view source entries extend its exact manifest.
All common football application module bytes match the accepted Alpha 6 source;
the deliberate differences are a7 version metadata, the existing read-only chart
accessor, and the added chart presenter/API/display. No private generator history,
PDF, image, audit log or save appears in the unique integration history.

Renewed frontend 157 and standard real-engine Chromium 64 cases pass (4.4m),
with no skips. Ruff check/format (634 files), pip check, production build and npm
audit pass, with zero vulnerabilities. Production assets were built to an external
outDir to preserve all active preview assets; its hashes equal the existing
matched bundle. Documentation/metadata checks: 22 pass.

Fresh corrected stage/runtime/archive construction passes. The runtime contains
658 files and exactly 118 teams. Isolated Python `-I` imports originate in that
runtime; catalog/UI/assets, every-team snap/strict-save-load and all 236 frozen
chart books pass with unchanged saves. Actual staged Chromium checks all 30 rows
at 1280×1000, closed help and secure detached Special Teams. Corrected runtime ZIP:
SHA-256 `662148cb5a5b8590fe4e4a7b9290548a87bb7c98da7bc5ec48f6c2ab5619ba13`,
under `/private/tmp/bb-alpha7-corrected-verification/`. The pre-audit archive is
superseded. No reference values or imagery are copied into the viewer.

The existing broad corrected-data 128-game audit plus two repeats applies because
football sources are unchanged; it remains mechanics/timing/coaching/replay
validation rather than a historical-calibration claim. Root's independent
all-116 semantic/216-outcome/source-support audit and accepted DATA-039 record
remain the catalog authority.

Build/publication controls were reviewed: `build.yml` checks out the full
`source_ref`, validates it through reusable `tests.yml`, builds/smokes all three
native targets and uploads inspected artifacts without creating a release.
Dispatch on the dedicated `release/alpha7-visual` branch with the final full SHA
keeps its concurrency independent from Alpha 6's main-branch run. Only that
branch may be pushed nonforce at this checkpoint; origin/main is not advanced.
Alpha 7 tag/release publication remains coordinated after Alpha 6 is released
and marked Latest. All previews through 8143 and their games remain live.


Corrected full Python gate: 4,003 passed in 883.29 seconds (14m43s), 93.41%
branch-inclusive coverage against the 75% minimum; no skips or pytest warnings.
This is corrected-data candidate acceptance, superseding the pre-audit baseline.
Final review confirms the accepted catalog/pins, reviewed read-only viewer and
public-safe history; no football-source, workflow or dependency change occurred.
Only documentation is added after the tested integration source, with focused
metadata/player-documentation checks before the dedicated-branch push.

Corrected gate commands use `/tmp/bb-alpha7-corrected-*.log` for retained private
outputs, `BB_E2E_SEASONS=/private/tmp/bb-alpha7-corrected-e2e-seasons` for the
standard browser gate, and `/private/tmp/bb-alpha7-corrected-verification/` for
fresh stage/runtime/archive inputs. The ignored runtime and staged-UI helpers
reuse the strict smoke procedure with corrected paths and assert every-team
snap/save-load plus 236 unchanged chart books. All selected staged inputs remain
byte-identical to the final allowed checkout files. Native dispatch/run evidence
will be reported separately; no tag/release is created by the build workflow.


## Native acceptance and Alpha 6 receipt integration

Immutable built source: `4da8c0ff288052f7a2d60bd2d63399e49af1fa7a` on
`release/alpha7-visual`. Exact-SHA native run
[42102433641](https://github.com/rtulloh/bowl_bound/actions/runs/42102433641)
passes its source gate and all three native targets. CI confirms 4,003 Python
cases, 93.41% coverage, 157 frontend cases and 64 real-engine browser cases.
All three portable executables pass the 118-team snap/strict-save-load smoke.
The Windows installer additionally passes install, registry, game/save,
uninstall and user-file preservation. A separate local run of the downloaded
Apple Silicon executable passes all 118 teams and 236 unchanged frozen chart
books. All 11 downloaded files pass checksums; native inventories contain the
exact 597 approved season-related resources and reviewed frontend assets,
licenses/notices, with no private paths. No build artifact is committed.

Observed CI advisories remain visible: 75 existing React act warnings, two
existing duplicate-key warnings in unchanged synthetic App/PlayLog tests,
whatwg-encoding deprecation, and Windows' optional hidden-import tzdata warning.
No skips or failing checks are concealed.

Alpha 6 is published at immutable `a95ded` with all 11 inspected assets and the
repository Releases panel verified. Its docs-only receipt
`92f99f84fad4d95c9b3cf542cfd6e0a95a08be48` is incorporated locally here. Only
the generated issue tracker conflicted; regenerate it from the combined tickets.
Before this receipt phase, reconsulted Paydirt
`docs/dev-notes/release-readiness-2026-11-02.md`,
`.github/workflows/release.yml` and `tests/test_release_metadata.py`. Adapt
explicit immutable source, separate validation/publication and disclosed warnings;
reuse no NFL behavior, data, dependencies or permissive installer failure policy.

The receipt merge and these acceptance records change developer documentation
only. Verify every exact release-selected source input, frontend input/lockfile and
chart against built `4da8c0ff`, plus native frontend resource pins; run focused
issue-index, release metadata and player-documentation checks. The existing full
source/native gates remain authoritative because packaged inputs do not change.
Keep the Alpha 7 tag targeted at built `4da8c0ff`, independently of this local
acceptance merge. Do not rebuild or retarget the tag merely for receipt records.

Alpha 7 publication and main advancement remain with root after owner web play
testing. UI-062 through UI-069 remain resolved rather than closed. Preserve all
preview processes and games through port 8143. No tag, draft, release or main
push occurs in this local integration step.


Receipt verification completes: all 681 exact selected inputs/manifest bytes equal
built `4da8c0ff` and its accepted stage; all 658 runtime file hashes remain intact.
Every packaged non-Python resource, including frontend assets and charts, matches
all three inspected native inventories. Preview assets equal their pre-receipt
ordinary-checkout build; release-stage assets equal the accepted runtime. The
clean release excludes test-tree CSS utilities, so those two intentional build
contexts are checked against their own baselines rather than conflated.
Only nine developer-documentation files differ from the built commit. All 22
issue-index, player-documentation and release-metadata checks pass, and both
working/staged diff checks are clean. No full gate or native rebuild is needed
for these byte-identical packaged inputs.
