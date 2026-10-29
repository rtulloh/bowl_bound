# Milestone 24 — Initial alpha publication preparation

## Owner direction and boundaries

On 2026-10-28 the owner requested GitHub/release preparation after the M21a
implementation/audit commit d030974, with community feedback alongside remaining
roadmap work. This authorizes preparing tooling and documentation early; it does
not mark Milestones 22/23 complete or authorize a remote, push, tag or publication.
Keep local opencode.json changes outside project commits.

Decisions confirmed: MIT for original code; standalone apps for the initial alpha.
Owner supplied the public bug-report contact on 2026-10-28:
**bowlboundsupport@gmail.com**. Include it in the player reporting guide.
Proposed initial public version: 0.1.0-alpha.1 (Python normalized 0.1.0a1).
No tag is created during preparation; existing tags remain immutable.

## Paydirt consultation

Reviewed a local Paydirt checkout:

- paydirt.spec:5–18: selective data staging; adapt explicit resource inventory, not
  broad docs/images/directory globs or historical team inclusion.
- .github/workflows/release.yml:1–215: native platform builds and frontend build;
  adapt test/build/platform separation and checksum artifacts. Do not copy
  automatic public-release creation, broad dependency collection, unreviewed
  action versions or silent installer failures.
- paydirt-web/start.sh:1–48: path-independent startup and shutdown; do not ship
  uvicorn reload/Vite development servers or fixed readiness sleeps to testers.
- docs/installation.md:1–65 and docs/playing.md:1–75: separate install/run/play
  walkthroughs, platform-specific launch steps, clear troubleshooting. Do not
  inherit NFL play mappings, unavailable features or security-workaround commands.
- RELEASE_NOTES.md:1–63: versioned notes, but Bowl Bound public notes must contain
  player-facing features/limitations only, never private audit/seed/host details,
  local paths, internal ticket histories or agent configuration.

These are design references, not runtime dependencies. Retain copied-code
attribution when adaptation actually copies expression rather than an idea.

## Ticket sequence and commits

Each behavior change is test-first. Review tests before red, implementation
before green and final scoped diff before commit, as directed for M21a. Commit
each ticket before starting the next; run focused gates per ticket and the full
application gate before final milestone commit/publication recommendation.

1. [DEV-033](issues/DEV/DEV-033.md): license and version contract. Keep gameplay
   profile/save schema unchanged; test metadata mapping rather than bump rules.
2. [DEV-016](issues/DEV/DEV-016.md): separately scoped pre-alpha development-tool
   security remediation, retained in its existing milestone assignment. Review
   supported upgrades, clean install/audits, Node24.22.1 unit/build/browser gates.
   Never run blind force fixes or claim production exposure from dev advisories.
3. [DEV-012](issues/DEV/DEV-012.md): explicit release staging/manifest builder;
   no recursive inclusion of local seasons/, docs/, home directories or worktree
   contents. Fail on unexpected symlinks, missing inputs, unsafe destinations,
   stale assets and mismatched metadata; stage transactionally without destructive
   broad cleanup. Synthetic tests inject forbidden files and inspect archives.
4. [DEV-034](issues/DEV/DEV-034.md): standalone entry point and source launchers.
   Default production web mode uses one local FastAPI/Uvicorn process with built
   assets, no Node on player machines; preserve explicit CLI entry point. Loopback
   only unless explicit remote opt-in. Handle frozen/resource paths independently
   of cwd, missing resources, port conflict, readiness/browser opening and shutdown.
   Do not store player files in transient or read-only bundled resource directories.
5. [DEV-035](issues/DEV/DEV-035.md): README, player documentation index,
   installation/play/troubleshooting, public alpha notes and bug-report template.
   Reports request game version, short description/repro steps and optional
   inspected logs/save; never request chart PDFs, raw chart dumps, personal data
   or secrets. Email remains a publication blocker until owner supplies it.
6. [DEV-036](issues/DEV/DEV-036.md): PyInstaller and draft build workflow using
   only staged inputs. Target macOS arm64, Windows x64 and macOS Intel x86_64; no
   support claim until native runner smoke passes. Initial portable archives may
   avoid installers/signing complexity; document unsigned/platform caveats honestly.
   Pin reviewed tool/action versions; build from locked dependencies. Produce
   artifact manifest and SHA256 checksums. Prepare builds, not automatic publishing.
7. [DEV-037](issues/DEV/DEV-037.md): final source/history/privacy and fresh-machine
   audits, license inventory, full regression/security gates, player docs verification,
   platform evidence and owner go/no-go. Separate source-repository publication
   audit from distributable inspection: a clean ZIP does not make Git history safe.

## Artifact contract and excluded material

Include only engine/runtime modules needed to run the game, built frontend assets,
selected player docs, license/attribution/version metadata and exact original
Cedar Valley/Harbor Tech chart files plus their public synthetic provenance/license.
No optional local rosters, even fictional ones, are bundled without a separately
reviewed exact allowlist change. Historical team charts, source PDFs/rulebook,
saves, play/audit logs, developer notes/config, test fixtures, importer tooling,
node_modules, development servers, environment files and unrelated local files
are excluded from player artifacts. .gitignore is not a release manifest.

## Final acceptance / publication hold

- Test malformed/hostile staging inputs, filename/path traversal and symlinks;
  verify extracted contents, not just source-selection code.
- Fresh source checkout and built artifact load public samples, serve UI, play,
  save/reload, print version and shut down without private files or Node/Python
  installations for standalone users.
- Full Python coverage/lint/format, frontend unit/build, browser/full games and
  dependency/security checks pass; report all failures/retries/warnings honestly.
- No copied chart rights or official game affiliation implied by MIT/code license.
- Verify player-facing release notes have no developer-private content.
- Confirm email, license notices, platform/signing caveats and known limitations.
- Review public Git contents and reachable history before remote/tag/push approval.
  Never sanitize history destructively or change existing tags without approval.
- Stop after the dedicated milestone24 preparation commit for owner review. GitHub
  setup and first release-tag build are the next explicit owner-authorized step.

## Planning validation

Pending read-only plan review and existing issue-tracker checks. No runtime edits
or packaging/publication actions are part of this planning checkpoint.

### Grilling Notes

**Assumptions verified:** 4/5: existing backend serves built UI and binds locally
(backend/__main__.py); Python/API/npm currently duplicate version 0.0.1
(pyproject.toml, backend/app.py, frontend/package.json); source license was
undecided (docs/ATTRIBUTION.md); original sample reproduction/provenance already
exists (bowl_bound/sample_teams.py). Native cross-platform build support remains
unverified until actual runners execute smoke tests.

**Open Questions:** 2 -> 0: owner selected MIT and supplied the public support
email. Version 0.1.0-alpha.1 is a preparation default, not a tag.
**Status changed:** No; READY for preparation, NOT READY for publication.
**Key revision:** Stage before PyInstaller analysis, not just filter its data
files: dependency analysis from a dirty worktree can otherwise include unwanted
modules. Source launchers must also use built assets, not Vite/reload. Rollback
is a new immutable release/tag later; retain prior artifacts and do not mutate
existing saves/profiles, delete private material or rewrite history. Portable
archives are simpler than installers; native execution and signing caveats
remain explicit release gates rather than assumed capabilities.

## DEV-033 implementation evidence

Paydirt metadata/workflow consultation above applies to this ticket. Independent
version contract avoids copying runtime code. Reviewed tests before red:2 expected
failures (old version, absent license). After implementation review:51 focused
metadata/API/regulation/replay tests passed; focused Ruff passed. API health
payload, engine profile and save schema remain unchanged. License/version/API
documentation updated together; no tag or release exists.

## DEV-016 cumulative result

Separate prerequisite completed: selected Vite8.3.5, Vitest5.0.5 and React plugin
6.1.2 after engines/peer/advisory review. Clean install with --ignore-scripts,
full/production audits0,122 frontend tests/build and32 Chrome cases passed
(3.7m, no retries). Retained whatwg-encoding deprecation and informational jsdom
performance advice; no warning suppression or test-isolation weakening. See
[dependency security](dependency-security.md). Support email is now confirmed.

## DEV-012 release selection evidence

Implemented exact source/resource manifest and transactional stage/build/runtime/
archive script. Selected sample SHA256 pins match original public fictional
charts/provenance/license; no historical team or optional roster selected.
Synthetic injected private files, paths/symlinks/stale inputs/assets, immutable
outputs and archive content inspections covered. Reviewed tests before initial
missing-module/API reds and4 meaningful malformed-lock failures; implementation
review found no gameplay coupling. Focused29 tests passed with80.06% script
branch-aware coverage. Actual isolated staged clean frontend build and isolated
Python UI/team/game/save smoke passed; clean runtime ZIP assembled.
[Build guidance](release-builds.md) explains exact commands and remaining gates.
This ZIP is native-builder input, not the standalone alpha. Final lint/test
rerun after review precedes the ticket commit.

## DEV-034 starter evidence

Implemented production local launcher and source/standalone start.sh/start.bat
selection, preserving existing terminal entry point. Consulted Paydirt starter
above; deliberately avoided reload/Vite/child-process cleanup complexity. Tests
reviewed before missing-module red and failed-startup false-success regression.
After implementation review82 focused launcher/packaging/API tests passed; Ruff
lint/format passed. Live synthetic-resources startup from unrelated directory
confirmed API/UI readiness and graceful Ctrl+C exit. Browser never opens for an
occupied port and waits for actual startup. Source paths with spaces and frozen
resource resolution are synthetic-tested; actual Windows/frozen platform smoke
still required. Exact manifest now includes launcher and starter scripts.

## DEV-035 player documentation evidence

Replaced stale README and added player index, installation, play, startup,
troubleshooting, versioning, public draft release notes and email bug reporting.
Owner follow-ups included BowlBound.exe Windows naming, verified-download
security guidance, chart-extractor/platform-library instructions and official
Python/Homebrew/pip/venv links. Support address is bowlboundsupport@gmail.com.

Adapted Paydirt guidance structure, not private developer release-note content
or broad security bypasses. Exact package inventory includes only player guides
and a public attribution summary; no detailed source attribution register or
developer notes. Native dependency license texts are still a later gate.
44 focused checks (including local documentation targets/selection/privacy and
report contact) and64 synthetic importer CLI/export/e2e tests passed after
review. All8 official setup links returned HTTP200; importer help flags match
examples. No gameplay changes or historical-chart imports/tests were needed.

## Cumulative checkpoint — runtime/docs through 5bb3b3c

`.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **2,275 passed
in470.17s**, **93.38% branch-aware coverage**; no skips/warnings reported.
The unchanged75% floor passed. Launcher84% rounded module coverage. The earlier
DEV-012 script-specific80.06% check is separate: scripts are outside the normal
application coverage source list, not silently counted by this gate.
Frontend122/build and full32 Chrome cases passed with the remediated toolchain.
Repository Ruff lint/format and77 focused metadata/package/launcher/docs/tracker
checks passed at the player-doc commit. These results do not establish native
Windows/Intel/Linux standalone support or publication readiness.

## Owner-approved source publication snapshot

The owner separately authorized a public source push, then approved creating a
clean public snapshot after the pre-public history audit found private
verification expectations in documentation. This does not complete Milestone 24
or authorize tags, native artifacts or a GitHub release.

Reconsulted Paydirt `.gitignore`: retain separation of private charts, saves,
logs, environments and generated builds, but keep Bowl Bound's stricter exact
fictional-team allowlist. No Paydirt code or data is copied by this step.

The new public repository is independent of the retained pre-public checkout.
Old commit IDs in milestone/ticket notes describe that retained archive; they
are not ancestors that can be resolved in public Git history. Develop and push
from the new public checkout going forward; do not merge/push the old private
history. The original checkout and local agent configuration are unchanged.

Sanitization changes documentation/configuration only: remove historical-team
verification expectations, use an explicitly fictional schema example, clarify
current distribution permission, and generalize host-specific paths in prior
command examples. Omit opencode.json entirely. Engine, frontend, importer, tests,
fixtures, version/save profile, release manifest and public sample bytes remain
unchanged from the reviewed source. No behavioral red test is warranted.

### Source gate results

Fresh Python 3.12 environment installed with
`.venv/bin/python -m pip install -e ".[dev,web,pdf]"`. This source regression
uses local Python 3.12.8; it is not endorsement of that patch for native shipping.

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **2,275 passed
  in 450.68s**, **93.38% branch-aware coverage**; no skips/warnings reported.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: **360 files** already formatted.
- `.venv/bin/python -m pip check`: no broken requirements.
- Frontend, Node **24.22.1**: `npm ci --ignore-scripts`, `npm test` (**122 passed**),
  `npm run build`, `npm audit` and `npm audit --omit=dev`: passed; audits **0**.
- Full real-engine Chrome gate: **32 passed in 3.7m**, zero retries/skips.
  Command in frontend: `BB_E2E_CHANNEL=chrome BB_E2E_SEASONS="$TMPDIR/bowl-bound-public-source-e2e" npm run test:e2e`.
- Launcher `--version` prints 0.1.0-alpha.1; `python -m bowl_bound --seasons seasons
  --list-teams` lists exactly Cedar Valley and Harbor Tech (2007).
- **641** local Markdown file/directory targets exist; **11** pinned sample hashes
  match. Staged source contains **428** text files; no private libraries, PDFs,
  rosters, saves/logs, build/dependency trees, local config or prior Git history.
- Pattern-based credential/host-path scans found no matches. These checks are
  defense in depth, not a guarantee against every possible secret or a full
  dependency/native-artifact security audit.

Retained notices: npm reports deprecated whatwg-encoding@3.1.1; Vitest prints
informational jsdom pool-performance advice; pip reports an available update.
No warnings were suppressed and no assertions/skips/coverage thresholds changed.
Native builds, exact bundled dependency notices and platform acceptance remain
open under DEV-036/DEV-037. Source publication is not a standalone alpha release.

### Owner clarification: three native build targets

During source publication the owner requested macOS Apple Silicon arm64,
Windows x64 (BowlBound.exe) and macOS Intel x86_64 ("ix86"). No 32-bit macOS
or Linux standalone target is planned for the initial alpha. Reconsulted
Paydirt release.yml: adapt its separate ARM/Intel native builds, not its extra
Linux artifact, broad staging or automatic public release. DEV-036 and player
installation guidance updated; 77 focused release/launcher/metadata/tracker
checks passed after the documentation-only change. Native implementation and
smoke evidence are still outstanding; this source push creates no builds/tag.

## DEV-036 workflow implementation plan

Reconsulted Paydirt spec and release.yml before this phase. Adapt native
ARM/Intel/Windows matrix, not broad collect_all, full-tree data copying,
unpinned installs, optional failing installers or automatic release publication.
Add a manually dispatched test-gated workflow, isolated pinned native build
environment, onedir portable ZIPs, dependency notices/inventory, exact resource
and module inspection, SHA256/manifest, and extracted executable API/save smoke.
Keep native support provisional until actual runners pass; no tag/release job.
Tests first cover architecture/name contracts, selected resources, stale/private
inputs, ZIP inventory/checksums and workflow permissions/action pins.

### DEV-036 Windows installer extension and local evidence

Owner requested a Windows installer like Paydirt. Reconsulted
`packaging/windows/installer.nsi` and `docs/installation.md`: adapt NSIS
shortcuts, installed executable and uninstall registration, but not HKLM/admin
installation or recursive uninstallation. Use per-user LocalAppData/HKCU, an
empty destination and exact packaged-file removal; preserve personal files.

Tests preceded implementation: missing native/installer modules and absent
workflow/lock reds; added malformed archive/Windows wildcard/path cases failed
before guards. A real isolated build found checkout egg-info was incorrectly
treated as an installed project; synthetic regression failed before scoping
the installed-project check to environment site-packages. Workflow review
found the Playwright harness requires `.venv/bin/python`; the corresponding
workflow regression failed before aligning the Ubuntu test environment.
No existing assertions, skips, coverage floor or engine behavior changed.

Validation so far:

- Isolated native graph installed with `pip install --only-binary=:all:
  --no-deps -r release/requirements-native.txt`; `pip check` passed.
- Real local macOS arm64 PyInstaller build and extracted executable smoke
  passed: version, UI/assets, exact fictional samples, snap, save/load, graceful
  shutdown. This prototype used local Python **3.12.8**, not workflow-pinned
  **3.13.17**; it is not approved for shipping.
- 79 focused native/smoke/installer/workflow/release/launcher tests passed
  before the final workflow-harness regression was added.
- Full Python gate: **2,318 passed in 432.13s**, **93.38%** branch-aware
  application coverage; no skips/warnings. Build scripts remain outside the
  established application coverage list, not silently counted by that gate.
- Frontend Node24.22.1: **122 tests passed**, production build passed, npm
  audit **0**. Retained Vitest informational pool advice and staged npm
  whatwg-encoding deprecation; no suppression.
- actionlint **1.7.12** passed (`-shellcheck=` because ShellCheck is not part
  of this local check); executable download matched release asset SHA256.
  This validates workflow syntax/types, not successful native runner execution.

Manual-only test-gated workflow has exactly three native jobs, read-only
contents permission, SHA-pinned actions and no tag/release publication. Actual
Windows/Intel and pinned-runtime ARM runner evidence, installed Windows smoke,
bundled native-library licensing and owner acceptance remain open under
DEV-036/DEV-037. No native support claim or release has been made.

### DEV-036 final local review checkpoint — 2026-10-29

Reviewed staged changes before commit. Keep PyInstaller optimize=0 (regression
failed before changing the recipe) to retain normal engine assertions. Windows
shutdown review found Uvicorn replays SIGBREAK after graceful shutdown; a
synthetic replay failed before temporary Ctrl+C-equivalent handling and
handler restoration were added to the launcher. Paydirt has no SIGBREAK
implementation to reuse; actual Windows process-group behavior is still a
native acceptance gate. This does not change football rules or save formats.

Final commands/results:

- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: **2,321
  passed in 439.89s**, **93.41%** branch-aware application coverage; no
  skips/warnings. Same established 75% floor and coverage source list.
- `.venv/bin/python -m pytest tests/test_standalone_build.py
  tests/test_standalone_smoke.py tests/test_windows_installer.py
  tests/test_build_workflow.py tests/test_release_package.py
  tests/test_launcher.py tests/test_release_metadata.py
  tests/test_release_player_docs.py tests/test_issue_tracker.py -q`: **103 passed**.
- `.venv/bin/python -m ruff check .` and
  `.venv/bin/python -m ruff format --check .`: passed (**367 files**).
- `.venv/bin/python -m pip check`: no broken requirements.
- `npm --prefix frontend test`: **122 passed**;
  `npm --prefix frontend run build`: passed; `npm --prefix frontend audit`: **0**.
- From frontend, with Node24.22.1, an external synthetic sample directory and
  `BB_E2E_CHANNEL=chrome`, `npm run test:e2e`: **32 passed in 3.8m**, no retries
  or skips. Vitest informational pool advice remains unsuppressed.
- Rebuilt the final local ARM prototype with the clean build-environment
  interpreter: `python -m scripts.build_standalone --target macos-arm64
  --output "$ABSENT_EXTERNAL_OUTPUT"`; then
  `python -m scripts.smoke_standalone "$ABSENT_EXTERNAL_OUTPUT"`: passed.
  This still uses local3.12.8, not the approved workflow runtime3.13.17.
- actionlint1.7.12 (`-shellcheck=`) passed after the final workflow change.
- Dependency-marker graph checked for workflow Python3.13.17: Windows22
  selected distributions, each Mac21, no unsatisfied default dependency edges.
  This metadata check is not a Windows/Intel wheel installation or native run.
- `.venv/bin/python scripts/build_issue_index.py`: regenerated, no index delta.

Milestone24 and DEV-036 remain open for actual three-runner evidence, Windows
installed/uninstall smoke, full bundled native-library license audit and owner
acceptance. No push, workflow dispatch, tag or release occurred in this step.
Local permission configuration remains ignored and outside the staged changes.

## First GitHub build gate and UI-040 follow-up — 2026-10-29

Owner explicitly approved pushing 7b97ce7 and dispatching the manual workflow.
Run 40822200799 passed Python and frontend unit/build/audit gates; browser gate
reported 31 passed/1 failed: optional controls measured 88px against existing
<85px desktop limit. Native jobs were skipped as designed. Source publication
and a local ARM prototype are not alpha readiness. React act(...) warnings
in passing frontend CI tests remain visible; they did not cause the failure.

Consulted Paydirt PlayModifiers.jsx compact padding/wrapping before this fix;
adapt presentation spacing only, not NFL rules, copied chart data or hidden
actions. UI-040 belongs to current milestone 24 as a newly exposed alpha
blocker, not a reopened prior milestone. Local native font passed unchanged;
wider Verdana metrics reproduced exactly 88px, from two 40px rows plus 8px gap.

Reviewed expanded browser test before red: native passed, wide-font failed 88px.
Scoped modifier-button padding reduces current button height 40px to 36px,
leaving main play selectors, engine actions/labels, difficulty, dice and saves
unchanged. Retain <85px desktop/<130px mobile checks; add unclipped/no-overflow
label checks and >=24px button targets. Both focused cases, all 122 frontend
unit tests, build, and all 33 browser tests (3.7m) passed. Ruff lint/format and
pip check passed; all 2,321 Python tests passed with 93.41% branch-aware
coverage in 443.08s. The 102 focused packaging/workflow/docs/tracker checks
also passed. Full local gates are green before the separate fix commit/push
and new workflow dispatch.
Do not claim the alpha is ready until all three native jobs and artifact/license
acceptance pass.

### UI-040 validation commands

Commands use Node 24.22.1 via
`PATH=/Users/rtulloh/.nvm/versions/node/v24.22.1/bin:$PATH` for npm.
Browser commands run in `frontend/` with `BB_E2E_CHANNEL=chrome` and
`BB_E2E_SEASONS` set to a fresh synthetic library under the approved
OpenCode temporary directory.

- `npm run test:e2e -- --grep "optional modifiers fit"`: red 1 passed/1 failed
  (88px); after the production fix and rebuild, 2 passed.
- `npm run test:e2e`: 33 passed in 3.7m.
- `npm --prefix frontend test`: 122 passed.
- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend audit`: 0 vulnerabilities.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: 368 files formatted.
- `.venv/bin/python -m pip check`: no broken requirements.
- `.venv/bin/python scripts/build_issue_index.py`: regenerated index.
- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: 2,321 passed
  in 443.08s, 93.41% branch-aware coverage; no skips or warnings reported.
- `.venv/bin/python -m pytest -q tests/test_issue_tracker.py tests/test_create_issue.py tests/test_release_player_docs.py tests/test_build_workflow.py tests/test_release_package.py tests/test_standalone_build.py tests/test_standalone_smoke.py tests/test_windows_installer.py`:
  102 passed in 1.29s.

Final implementation review: only modifier-panel button padding changes; the
main selector size and engine/API behavior are untouched. Browser coverage
retains the original limits and adds a reproducible wider-font case. Player
guidance now describes wrapping; issue UI-040 remains open pending a tested
commit reference and Linux CI confirmation. Local `opencode.json` is ignored
and must not be staged. No new push, dispatch, tag or release in this fix yet.

## Second GitHub run and DEV-038 checkout follow-up — 2026-10-29

Owner approved pushing a8346b0 and rerunning the workflow. Run 40864663857
passed the full Ubuntu test gate, including all 33 browser cases, confirming
UI-040 on Linux. Both native macOS 26 jobs (arm64 and Intel x86_64) built
with Python 3.13.17 and passed extracted-app smoke/upload. Windows stopped
during staging: `Public sample hash mismatch: seasons/SAMPLE-LICENSE.md`;
no Windows executable, installer or smoke result exists. Native-library
license review and fresh-machine acceptance still remain; no release/tag.

Consulted local Paydirt `.github/workflows/release.yml` before this follow-up:
it uses ordinary native checkout, with no byte-pinned sample inventory or
line-ending safeguards. Search found no relevant autocrlf/eol policy to reuse.
Do not copy its best-effort installer steps or automatic release behavior.

DEV-038 adds a real Git checkout regression with all approved public sample
paths but entirely synthetic bytes; it never reads historical chart content.
Reviewed before red: with `core.autocrlf=true`, staging rejects the changed
sample bytes; `input` and `false` pass. Reproduction: 1 failed/2 passed, same
hash-mismatch error class as Windows CI. The test also checks all selected
input bytes and preserves rejection of tampered content after staging.

Fix is repository metadata only: `* text=auto eol=lf` in `.gitattributes`.
Git checks out tracked text consistently; binary detection preserves binaries.
No manifest hash, chart, engine, verifier, dependency, workflow target or
installer code changes. Ignored private files are not rewritten. No need to
renormalize or bulk-stage the existing worktree. Native Windows CI remains
required to validate the rest of the packaging/installer path.

### DEV-038 verification checkpoint

- `.venv/bin/python -m pytest -q tests/test_release_package.py -k git_checkout`:
  before policy: 1 failed/2 passed; after policy: 3 passed.
- `.venv/bin/python -m ruff format tests/test_release_package.py`: formatted.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: 369 files formatted.
- `.venv/bin/python -m pip check`: passed.
- Node 24.22.1 `npm --prefix frontend test`: 122 passed.
- Node 24.22.1 `npm --prefix frontend run build`: passed.
- Node 24.22.1 `npm --prefix frontend audit`: 0 vulnerabilities.
- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: 2,324 passed
  in 445.72s, 93.41% branch-aware coverage; no skips/warnings reported.
- Node 24.22.1, `BB_E2E_CHANNEL=chrome`, fresh temporary synthetic library,
  `npm run test:e2e` in frontend/: 33 passed in 3.7m.

Both macOS artifacts downloaded from run 40864663857 were verified locally
using extract_verified: ZIP sidecars, every file hash/path and exact
internal/external manifest equality, 176 files and all 11 pinned sample files
per target. Both checksums are recorded in DEV-036. Downloaded ARM artifact
passed local smoke with `TMPDIR` set to the approved OpenCode directory:
`.venv/bin/python -m scripts.smoke_standalone <downloaded-arm-artifact-dir>`.
Native Intel smoke passed in CI; no local Intel-machine claim. This is artifact
integrity/runtime evidence, not full bundled-library licensing or fresh-machine
acceptance. There is still no Windows artifact or release/tag.

## Third GitHub run and DEV-039 freezer follow-up — 2026-10-29

Run 40882820635 at fbf2fd3 passed the complete Ubuntu gate and both native
macOS builds/smokes/uploads. Windows passed exact sample verification and
built BowlBound.exe, confirming the DEV-038 checkout fix, then failed
post-freeze runtime inventory verification: Unexpected or missing runtime files.
No Windows portable/installer smoke or upload occurred. Optional hidden-import
tzdata warning and whatwg-encoding deprecation remain visible, not suppressed.

Reconsulted Paydirt freezer specs and searched for bytecode-write safeguards;
no equivalent pristine-input/hash inventory or PYTHONDONTWRITEBYTECODE policy
was found. Do not reuse broad data selection or bypass inventory checks.
Examined installed pinned PyInstaller 6.22.3 isolated/_parent.py and compat.py:
hook children inherit environment but do not propagate parent -I/-B flags.
Python -I ignores PYTHONDONTWRITEBYTECODE in the analysis parent.

Reviewed new synthetic regressions before red. A substituted freezer runs real
Python using the production launch flags/env and imports an invented staged
package either directly or through a hook-like child. Both imports create
cache files and reproduce the same post-freeze inventory error. Separate
extra-cache and missing-license cases demonstrate the lack of path diagnostics.
Focused red: all 4 failed as intended. This reproduces a mechanism matching
Windows, not proof of its unreported extra file names; the real rerun remains
necessary, and improved diagnostics will expose any different cause.

Smallest fix: keep -I, add -B for analysis and PYTHONDONTWRITEBYTECODE=1 for
children. Keep optimize=0, exact hashes, inventory guards and build isolation.
Report sorted extra/missing relative inventory paths without host paths or
file contents. No deleting caches, forgiving extras or widening sample rules.
Reviewed implementation before green: all 4 focused cases now pass. No engine,
chart, difficulty, dice, save, runtime dependency or platform target changes.

### DEV-039 validation checkpoint

- `.venv/bin/python -m pytest -q tests/test_standalone_build.py tests/test_release_archive.py -k "freezer_imports or inventory_mismatch"`:
  4 expected failures before implementation; 4 passed after.
- `.venv/bin/python -m pytest -q tests/test_issue_tracker.py tests/test_create_issue.py tests/test_release_player_docs.py tests/test_build_workflow.py tests/test_release_package.py tests/test_release_archive.py tests/test_standalone_build.py tests/test_standalone_smoke.py tests/test_windows_installer.py`:
  113 passed in 1.84s.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: 370 files formatted.
- `.venv/bin/python -m pip check`: passed.
- Node 24.22.1 `npm --prefix frontend test`: 122 passed; Vitest performance
  advice remains visible.
- Node 24.22.1 `npm --prefix frontend run build`: passed.
- Node 24.22.1 `npm --prefix frontend audit`: 0 vulnerabilities.
- `.venv/bin/python scripts/build_issue_index.py`: regenerated.
- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: 2,328 passed
  in 442.55s with 93.41% branch-aware application coverage; no skips/warnings.
- Node 24.22.1, Chrome, fresh temporary synthetic library, frontend/
  `npm run test:e2e`: 33 passed in 3.7m.
- Isolated local native-build environment `python -m scripts.build_standalone
  --target macos-arm64 --output <approved-temporary-artifacts-directory>`:
  passed; local Python 3.12.8 engineering evidence only, not a shipped build.
- `TMPDIR=<approved-temp-dir> .venv/bin/python -m scripts.smoke_standalone
  <DEV-039-local-artifact-directory>`: passed version/UI/assets/two samples/
  snap/save-load/graceful shutdown. Build showed existing whatwg-encoding
  deprecation; it remains unsuppressed.

No source/module privacy guard, expectation or supported target relaxed.
Actual Windows CI and installer/runtime acceptance still pending.

## Fourth GitHub run and DEV-040 NSIS quoting — 2026-10-29

Run 40889867822 at 7101e6f passed the full Ubuntu test gate and both native
macOS build/smoke/upload jobs. Windows passed portable assembly, exact runtime
inventory and extracted-executable version/UI/assets/sample/snap/save/shutdown
smoke. This confirms the DEV-039 fix on Windows. NSIS 3.11 then rejected the
generated install-files.nsh line 2 because /oname="value" begins its output
name with a quote. No installer or installed-app/uninstall acceptance yet;
Windows artifact upload did not run.

Reconsulted Paydirt packaging/windows/installer.nsi: plain File commands, no
generated /oname reference to adapt. Retain Bowl Bound per-user/HKCU and exact
nonrecursive uninstall; do not inherit elevation or broad recursive selection.
NSIS official File reference explicitly requires quoting the whole /oname=
parameter for spaced names (https://nsis.sourceforge.io/Docs/Chapter4.html#file).
Reviewed pinned v311 Source/script.cpp rejection of an initial quote in the
output name. Local makensis is unavailable, so native compiler acceptance
remains required rather than inferred from string tests.

Reviewed tests before red: corrected two old expectations that encoded invalid
compiler syntax and added synthetic ordinary/spaced/literal-dollar filenames
with a spaced/dollar source path. Preserve exact File count, dollar escaping
and exact nonrecursive uninstall assertions. Unchanged implementation: 4 failed,
8 passed. One-line generator fix quotes the whole /oname= option, preserving
source quoting and escaping. Reviewed implementation before green: 12 passed.
No application, chart, save, difficulty, dice, dependency, target, verifier or
installer destination/uninstall policy changed.

### DEV-040 validation checkpoint

- `.venv/bin/python -m pytest -q tests/test_windows_installer.py`: red 4
  failed/8 passed; green 12 passed in 0.32s.
- `.venv/bin/python -m pytest -q tests/test_issue_tracker.py tests/test_create_issue.py tests/test_release_player_docs.py tests/test_build_workflow.py tests/test_release_package.py tests/test_release_archive.py tests/test_standalone_build.py tests/test_standalone_smoke.py tests/test_windows_installer.py`:
  116 passed in 2.28s.
- `.venv/bin/python -m ruff check .`: passed after formatting the new
  overlong test decorator; no behavior/assertion change.
- `.venv/bin/python -m ruff format --check .`: 371 files formatted.
- `.venv/bin/python -m pip check`: passed.
- Node 24.22.1 `npm --prefix frontend test`: 122 passed; existing Vitest
  performance advice remains visible.
- Node 24.22.1 `npm --prefix frontend run build`: passed.
- Node 24.22.1 `npm --prefix frontend audit`: 0 vulnerabilities.
- `.venv/bin/python scripts/build_issue_index.py`: regenerated.
- `.venv/bin/python -m pytest --cov --cov-report=term-missing -q`: 2,331 passed
  in 446.64s with 93.41% branch-aware application coverage; no skips/warnings.
- In frontend/, Node 24.22.1, `BB_E2E_CHANNEL=chrome`, fresh temporary
  synthetic library: `npm run test:e2e`: 33 passed in 3.7m.

No local compiler installed and no Windows acceptance claimed. A separate
reviewed commit and approved push/rerun are needed for actual NSIS evidence.

## Fully green native workflow — 2026-10-29

Run https://github.com/rtulloh/bowl_bound/actions/runs/40909408275 tested
e08542a and passed the Ubuntu source gate plus all three native jobs.
Windows compiled with NSIS 3.11 and passed silent install, registry/version,
installed-game/save, uninstall and unrelated-user-file preservation checks.
All three jobs uploaded inspected artifacts, not a release. Workflow Python
3.13.17 / Node 24.22.1 pins remain unchanged.

CI source evidence: 2,331 Python tests passed in 879.42s with 93.39% coverage;
122 frontend tests/build/audit (0 vulnerabilities) and full browser gate passed.
CI React act(...) warnings remain visible, as do whatwg-encoding deprecation,
optional Windows tzdata hidden-import warning and runner capacity annotation.
No tests skipped to achieve this result; macOS correctly skips Windows-only
installer steps. Local source coverage was 93.41%; CI coverage is 93.39%.

Downloaded with `gh run download 40909408275 --repo rtulloh/bowl_bound --dir
<approved-temporary-directory>`; local Python verification used extract_verified
on each ZIP, compared internal/external manifests, required exactly the 11
release/manifest.json sample paths/hashes and rejected private development path
components. Both macOS inventories have 176 files; Windows has 177. Verified
the installer SHA256 sidecar and 14,185,998-byte size. See DEV-036 for all four
SHA256 values. These checks verify inventoried application/data selection, not
a completed audit of every bundled binary or installer byte.

`TMPDIR=<approved-temp-dir> .venv/bin/python -m scripts.smoke_standalone
<downloaded-ARM-artifact-directory>` passed version/UI/assets/two fictional
samples/snap/save-load/shutdown. Intel and Windows runtime execution evidence
is native CI, not local machine acceptance. No private charts were exported.

DEV-038 (fbf2fd3), DEV-039 (7101e6f) and DEV-040 (e08542a) now have committed
fixes and native portable/installer evidence and are resolved, pending owner
play-test closure. DEV-036/037 remain open for full native-library licensing/
privacy and fresh-machine acceptance. No tag, release or final publication
approval is inferred from green CI.

Documentation-only acceptance recording: `.venv/bin/python
scripts/build_issue_index.py` regenerated the index; `.venv/bin/python -m
pytest -q tests/test_issue_tracker.py tests/test_create_issue.py
tests/test_release_player_docs.py tests/test_build_workflow.py` passed all
38 checks in 0.43s. No new behavioral tests needed: only evidence and ticket
status changed after the fully green tested commit. Reviewed evidence against
actual runner logs/downloaded artifacts before committing it separately.

## Owner alpha release request and publication hold — 2026-10-29

Owner explicitly requested creating the alpha release. Reconsulted local
Paydirt .github/workflows/release.yml for release orchestration; retain the
Bowl Bound manual approval and exact three-target privacy selection, not its
automatic tag-release mechanism or broader artifact selection. No existing
GitHub release was listed. Build artifacts remain those tested at e08542a;
36f5ede records subsequent documentation-only acceptance locally.

Final native-notice inventory review found a concrete DEV-041 blocker:
both macOS artifacts contain libssl.3.dylib, libcrypto.3.dylib and
libncurses.6.dylib, but none of the collected THIRD_PARTY texts mention
OpenSSL or ncurses. Windows contains libssl-3.dll/libcrypto-3.dll and no
OpenSSL notice in collected texts. Python LICENSE is not a substitute for
all bundled native-library notices. Package-level notice collection remains
incomplete; do not treat previous passing smoke as redistribution clearance.
No packaging behavior changed and no native notice was guessed or fabricated.

Created an unpublished draft prerelease via `gh release create
v0.1.0-alpha.1 --repo rtulloh/bowl_bound --target <full-e08542a-sha>
--title "Bowl Bound 0.1.0-alpha.1" --draft --prerelease --notes <player-safe-text>`.
The draft describes features/three intended downloads, unsigned security
caveats, fictional-only teams, support email and explicit publication hold.
No binaries attached. `gh release view ... --json
url,isDraft,isPrerelease,tagName,targetCommitish,assets` confirmed draft=true,
prerelease=true, assets=[], and the e08542a target. The target must be updated
to the corrected tested build before publishing; do not publish this draft as-is.

Draft URL: https://github.com/rtulloh/bowl_bound/releases/tag/untagged-cdccb231ddd35820099c

DEV-041 tracks missing native notices and complete inventory/redistribution
review. DEV-036/037 remain open; fresh-machine acceptance is still pending.
Public alpha publication is held, not silently waived by the release request.

## DEV-041 native-notice implementation candidate — 2026-10-29

### Design input and scope

Consulted local Paydirt licensing/notice searches and `paydirt.spec:5-73`,
plus its release workflow previously reviewed for this milestone. Its spec
copies the project LICENSE and uses broad dependency collection, season/docs
selection and onefile bundling, but has no native notice inventory to adapt.
Retain the principle of shipping notices beside the app; deliberately do not
reuse its broad data collection, runtime code, or implied licensing coverage.
No Paydirt team material was copied, and it remains no runtime dependency.

This change addresses missing bundled-dependency notices, not the original
project MIT LICENSE (unchanged). Exactly the same three native targets,
Windows BowlBound.exe, Node 24.22.1, difficulty defaults/odds, sample bytes,
engine profile and save format are retained. No gameplay/frontend behavior
changed. Player notice guidance and maintainer audit instructions change
with the packaging behavior.

### Red / review / green evidence

Reviewed self-contained synthetic tests before each red run. The initial
`tests/test_native_notices.py` run failed collection because the new helper
did not exist. After adding the helper, 15 tests passed. More importantly,
`pytest -q tests/test_standalone_build.py -k
"without_notices or vendor_licenses"` demonstrated four meaningful failures
against unchanged archive/package collection: all three targets allowed
unnoticed native payloads and setuptools/packaging notices were absent.
`pytest -q tests/test_native_notices.py -k version_or_compiler` demonstrated
three further failures before provenance-marker enforcement. Reviewed the
implementation before focused green runs; no assertions weakened or skips
added. The isolated-import synthetic-freezer regression mocks only the new
notice-collection side effect, retaining all its import/cache assertions.

The offline catalog records 19 hash-pinned upstream notice/inventory texts,
versions and source references. CPython v3.13.17 Mac build recipes and Windows
get_externals.bat establish relevant dependency versions. ncurses COPYING
and mpdecimal 4.0.1 COPYRIGHT.txt were extracted in memory from archives whose
SHA256 matched the upstream recipe. Header excerpts preserve the complete
leading upstream copyright/license comment for Expat/OpenSSL. No runtime
network license download is added. Exact-byte checkout policy is unchanged.

The Rust collection comes from the PyPI pydantic-core 2.50.1 sdist verified
against SHA256 e50d7b94baac6c7d09927fa5ca5800a0c7ee5015c7fcff65beb3a1931b5a6e09,
and the observed compiler commit library/Cargo.lock. All 127 unique registry
crate archives were verified against their lock checksums. Identical notice
texts are deduplicated with original filename references retained. Compiler
builtins licensing is separately preserved. This is a conservative notice
superset, NOT proof of the selected static-link graph. Seven upstream archives
provide no license files; they are explicitly identified for applicability
review, not silently assigned generic permission.

The collector validates the entire notice set before copying, rejects unknown
native families, and writes per-native-file hashes/component references.
Both top-level and internal notice copies are revalidated before archiving.
Synthetic positive archive/extraction and Windows exact install/uninstall
list checks retain the notice bytes; native installer execution awaits CI.

### Local validation and limitations

- Focused packaging/native/installer/workflow/player-doc command:
  `.venv/bin/python -m pytest -q tests/test_native_notices.py
  tests/test_standalone_build.py tests/test_windows_installer.py
  tests/test_release_package.py tests/test_build_workflow.py
  tests/test_release_player_docs.py`: **104 passed in 1.40s**.
- Earlier cumulative `.venv/bin/python -m pytest --cov`: **2,350 passed
  in 448.83s; 93.41% branch-inclusive coverage**. Further provenance/positive
  archive tests were then added; final cumulative rerun recorded below.
- `.venv/bin/python -m ruff check .`: passed.
- `.venv/bin/python -m ruff format --check .`: 374 files formatted.
- `.venv/bin/python -m pip check`: passed.
- With `PATH=/Users/rtulloh/.nvm/versions/node/v24.22.1/bin:$PATH`,
  `npm test`, `npm run build`, `npm audit` from frontend: **122 tests
  passed**, production build passed, **0 vulnerabilities**. npm printed an
  update-available notice; Node/npm pins were not changed.
- Browser gate initially failed all 33 before execution because the local
  Playwright Chromium headless executable was absent. Installed it with
  `env PATH=<Node24.22.1>:$PATH npx playwright install chromium`; repeated
  `env PATH=<Node24.22.1>:$PATH BB_E2E_SEASONS=<approved-temp-sample-path>
  npm run test:e2e`: **33 passed in 3.0m**, no skips/expectation changes.
- Reverified downloaded run 40909408275 ZIPs, extracted only temporary copies,
  applied the new notices, and passed final marker/inventory guards for **65
  native files per macOS target and 69 Windows files**. All three expose
  OpenSSL 3.5.9/Rust b940084d7eb6a299eb4bfeb8e34901bc051e7ac4; macOS
  exposes ncurses 6.5.20240427. ARM temporary-copy smoke passed version,
  UI/assets, exact samples, snap, save/load and shutdown. Original ZIP bytes
  and sidecars unchanged: these are NOT newly rebuilt release deliverables.

DEV-041 remains open pending corrected native builds/artifact acceptance and
completion of static dependency/target applicability and Microsoft runtime
redistribution review. DEV-037 fresh-machine/owner publication gates remain.
The draft remains unpublished with zero assets; no push or workflow dispatch
was performed for this candidate without separate approval. Local ignored
OpenCode command allowances were updated only as explicitly requested and
retain push approval rules; that configuration is not part of this commit.

### DEV-041 final local regression and commit checkpoint

Final `.venv/bin/python -m pytest --cov -q`: **2,374 passed in
443.42s**, **93.41% branch-inclusive coverage** (75% required); no skips
or warnings reported. Expanded focused packaging/documentation/issue command
(`tests/test_native_notices.py`, `test_standalone_build.py`,
`test_standalone_smoke.py`, `test_windows_installer.py`,
`test_release_package.py`, `test_release_archive.py`,
`test_release_metadata.py`, `test_build_workflow.py`,
`test_release_player_docs.py`, `test_issue_tracker.py`,
`test_create_issue.py`): **161 passed in 2.97s**.

Owner subsequently requested committing all pending work before implementing
CLI-046. Keep the native-notice candidate and owner-feedback ticket changes
in separate local commits. DEV-041 remains open for the documented native
build/licensing gates; committing this candidate does not declare release
acceptance complete. No push, workflow dispatch or publication authorized.

## CLI-046 announcer-style commentary — implementation scope

Owner authorized CLI-046 after observing dry alpha narration in CLI and web,
and explicitly required committing pending work first. Clean checkpoints:
61a2dc9 (native notices) and 6a04ed6 (feedback tickets). Release push/build/
publication stays paused; CLI-047 helper behavior is out of scope.

Consulted local Paydirt `paydirt/commentary.py:150-250` again before this
work, alongside prior full-file review recorded in CLI-046. Adapt phrase
families for no gain/loss/short-big gain/completion/incompletion/scoring,
not NFL result types, private roster data, random selection or embellishments
claiming routes, tackle breaks, dropped passes or named defenders. No runtime
Paydirt dependency. Bowl Bound structured reports remain authoritative.

Reviewed synthetic test matrices before running unchanged production code:
`pytest -q tests/test_commentary_announcer.py` demonstrated **31 failures,
6 passes**; the added kick matrix separately demonstrated **10 failures**.
Then implemented engine-only phrase selection and reviewed the implementation
before focused green runs. Same report number selects the same phrase/name;
no random stream or mutable narration state is used. Names/disclosure move
from every result prefix to the existing player/roster/API guidance. Both
named and missing-roster games get natural narration.

Changed expectations: old actor-prefix assertions now require integrated names
and exclude uncredited/opposing names; missing-roster assertions require
generic-role sentences rather than raw statistical descriptions. Fixtures
use negative sack credit and interception outcomes consistent with their stat
kind. A broad opposing-prefix check (`A `) now checks actual fictional names,
so the article in `A loss` is not mistaken for an opponent. CLI transport tests
compare `SavedGame.commentary` instead of legacy descriptions; the isolated
report-dedup test stubs narration only. All trace, save, RNG, attribution,
pending/ambiguous fallback and semantic-digest assertions remain.

Penalty reports (including no-foul return rerolls) retain **all** original
enforcement wording instead of actor prefixes that might lose context. The
return-reroll regression now explicitly verifies the complete factual text,
penalty flag, trace count and report immutability. No skip or loosened
football assertion. Special-team distances remain unspoken where no structured
distance exists, rather than parsing chart strings or deriving a return.

### Broader regression findings and corrections

First cumulative pass: **2,435 passed, 1 failed in 457.87s**, 93.40%
coverage. The failure correctly caught a new link from packaged playing.md
to unpackaged rosters.md; removed that link and retained the disclosure in
the packaged page itself. Do not broaden the release allowlist for this fix.

First full browser pass: **30 passed, 3 failed**. Two failures exposed real
narration omissions: kick calls had dropped exact engine distance details,
and automatic kneels were described as defended running plays. Added real
engine regressions for kicks and both kneel/spike actions, demonstrating
**3 failures** before correcting production behavior. Automatic clock plays
now retain their full factual wording and intent. Kick calls integrate names
and preserve the engine's entire factual text afterward, including distances
and final spot; this supersedes the initial unspoken-distance approach above.
No prose/chart-token parsing or field-position inference was introduced.

The third browser failure expected the old statistical play/formation string
in the spoken call. Updated it to require the exact natural sentence while
additionally verifying the called play and formation remain in the chart audit.
All state/clock/yardage/trace/visibility assertions remain; no retries/skips
were added to mask failures. Capitalized generic returner sentences correctly.

Reviewed corrections before green: focused engine/lifecycle/replay/CLI/API/
player-doc/issue command **232 passed in 14.66s**. Final cumulative Python
and unchanged-size 33-test browser gates restarted against the corrected code.
Frontend unit gate already passed **122 tests**; production build passed
using Node 24.22.1. Initial Ruff check found only import ordering in the new
test file; corrected it without changing test behavior.

Corrected full browser gate: `env
PATH=/Users/rtulloh/.nvm/versions/node/v24.22.1/bin:$PATH
BB_E2E_SEASONS=/private/var/folders/rl/kscrrjc578x2zgpkntgg8v9m0000gp/T/opencode/bowl-bound-dev041-browser-samples
npm run test:e2e` from frontend: **33 passed in 3.1m**. This includes
named/reversed/missing-roster mobile narration, exact engine-text transport,
save/load stability, kick details, kneel/spike, full regulation games and
overtime. No skips/retries. Final cumulative Python result pending.

Final corrected `.venv/bin/python -m pytest --cov -q`: **2,439 passed in
447.92s**, **93.41% branch-inclusive coverage**. Full browser **33 passed
in 3.1m**; frontend **122 passed**, build passed, Ruff/pip checks passed.
No skips or warnings reported in Python/browser output.

Owner web sanity-check initially used generic role fallbacks because the
public checkout lacked the original checkout's ignored fictional rosters.
Verified both teams' ten chart/metadata/provenance files are byte-identical
to `/Users/rtulloh/work/bowl_bound`; reused the existing CC0 fictional rosters
and provenance locally at owner request. No new team versions or names, no
chart changes, and no release allowlist changes. Roster installation is
local ignored data, not a change in Python behavior. Live games snapshot names
at creation/load; owner must new/load to pick up the installed rosters.

### CLI-046 owner acceptance and release request

Owner confirmed the web commentary looks good after local roster installation
and requested a release for outside alpha play-testing. CLI/API use the same
engine narration validated by focused transport and replay tests. Commentary
acceptance is satisfied; no gameplay, save, difficulty or dependency pins changed.
The existing release currently excludes optional rosters, including these
fictional samples: address that explicit packaging scope decision before
promising that released downloads match the owner's named-commentary game.
Release request authorizes proceeding with the push/build/release preparation,
not silently declaring open dependency-license gates satisfied.
