# Prospective v1.1.1 macOS packaging repair

Milestone 42 follow-up, tracked as [DEV-093](issues/DEV/DEV-093.md). This is a
reviewable local candidate, not completed milestone or release acceptance.
The immutable v1.1.0 tag and published assets remain unchanged. The version is prepared as 1.1.1 for frozen qualification; no new release is
published. Earlier local test images retain their 1.1.0 payload identity.

Consulted local Paydirt packaging/macos/create_app.sh, release workflow and
docs/release-testing.md. Adapt app-bundle composition, Applications drop link
and mounted-copy verification. Do not reuse its one-file assumption, NFL
content, runtime or Homebrew build dependency. Bowl Bound uses its verified ZIP
inventory and native system hdiutil.

## Findings and change

The downloaded ZIP matches its GitHub asset digest. A browser-extracted nested
Python retains quarantine; dlopen fails by system policy despite its valid
ad-hoc signature. A copied payload passes complete native smoke after removing
only its quarantine recursively. The installation example named the wrong
folder: the ZIP extracts to BowlBound. Correct that example and explain nested
attributes. Never remove security markers automatically.

The build workflow had no DMG step. The new image builder verifies the ZIP,
wraps its exact resources in Bowl Bound.app, and uses Finder/LaunchServices to
open a bundled command in Terminal. This keeps the existing browser/server and
Ctrl+C lifecycle visible. Both Mac matrix targets require mounted-copy Finder
startup, owned-listener health/version and shutdown, then the complete native
payload smoke. Existing receipt collisions fail before image creation, and
failed temporary images cannot block retry at the final output path.

Published-artifact verification supports mounted DMGs and adds both native Mac
jobs with `include_dmg=true`; older immutable ZIP-only releases keep their
existing default. A prospective v1.1.1 requires the DMG profile. These checks do
not establish fresh browser-download quarantine/Gatekeeper acceptance, Developer
ID signing or notarization; wrappers remain unsigned and not notarized.

## Verification checkpoint

Synthetic DMG validation fails before implementation. Tests cover bundle
composition, shell syntax, Finder launch intent, owned process shutdown, rejection
of another listener, receipt collisions and retry after partial image creation.
The published-workflow target expectation expands from four to six; every
selected job still uploads success/failure evidence unconditionally.

222 focused cumulative tests pass. Repository-wide Ruff lint, 910-file format
check, pip check and whitespace checks pass. The actual bundled start.command
forwards --version successfully from an app path containing spaces. The copied
published payload passes exact 173-team discovery, every-team snap/save/load,
version/health/assets and graceful shutdown.

The full local regression was invoked with `.venv/bin/python
scripts/run_full_regression.py --report <private-report>`; serial Python tests
remain running at this checkpoint. Frontend/audit/browser groups were also run
with pinned Node 24.22.1/npm 11.19.1 and `--skip-python`, preserving explicit
skips in a separate receipt. All 197 frontend tests, production build, dependency
install (zero vulnerabilities), 171-generated-team structural audit and browser
installation pass. All 72 browser cases fail before page creation because
Chromium MachPortRendezvous bootstrap_check_in is denied (1100); this is not
browser acceptance.

Local hdiutil creation fails with Device not configured, including tiny HFS+/UDZO
and APFS/UDRO control inputs. The agent environment also denies process
inspection. Mounted DMG, actual Finder startup, Intel-native behavior and fresh
download first launch remain unverified. No complete regression pass or release
qualification is claimed. Detailed reproduction receipts remain private.

## Remaining native commands

From a desktop-capable Mac Terminal in this checkout, with the verified ZIP and
matching checksum sidecar together:

```sh
.venv/bin/python -m scripts.macos_dmg /absolute/path/BowlBound-1.1.0-macos-arm64.zip --smoke
```

This creates local test image bytes from the immutable v1.1.0 payload; it does
not publish or replace any asset. Use fresh output paths if successful evidence
already exists. Port 8001 must be free; the smoke never stops an unrelated
listener. Repeat on an Intel Mac using its matching ZIP.

The frontend has already been built. Rerun browser acceptance without repeating
the long Python suite:

```sh
PATH="$HOME/.nvm/versions/node/v24.22.1/bin:$PATH" npm --prefix frontend run test:e2e
```

After successful new-release publication, download actual assets and run all
published native checks with `include_dmg=true`, then separately verify a fresh
browser-downloaded DMG's normal first launch and browser behavior. Preserve
failed receipts and disclose unavailable platforms. No push or publication has
been performed for this candidate.

Parent review follow-up: listener ownership resolves filesystem aliases on both
sides before comparison, covering macOS /var → /private/var temporary paths.
The synthetic alias regression fails first; unrelated-listener rejection remains
required. This is a smoke harness correction, not fresh native qualification.

DEV-094 follow-up: an ownership-check failure left the native process running
while automatic temporary-directory cleanup removed its resources, causing
unavailable folders and then an empty catalog. The failed smoke now retains the
copy with failure.json and prints its location. A synthetic regression first
reproduces disappearance; cleanup occurs only after successful bounded shutdown.
Stop an old failed helper Terminal before rerunning. The user reports image
creation/mount and Terminal/browser launch succeeded; ownership validation failed,
so this remains a partial native result, not smoke acceptance.

Owner steering: the DMG is the primary Mac player download, matching the desired
mount/copy-app/manual recursive xattr workflow. ZIPs remain secondary portable
outputs and exact native-builder inputs. Player installation and next-patch
release notes now lead with DMG architecture selection and manual unquarantine
of the copied app. No notarization request or signing claim is introduced.

## Native Apple Silicon rerun

The owner reran the helper in a desktop Terminal after alias and retention fixes.
The persistent local DMG receipt records mounted_payload_smoke and
finder_terminal_launch_smoke true. Its digest and 29,597,428-byte size match
independent inspection. Image creation/verification, mount/copy, actual Finder
startup, exact 173-team catalog with no problems, every-team snap/save/load and
graceful shutdown pass. Later browser connection refusal is expected because
smoke stops its server. The image remains available for normal app installation.

This supersedes the agent-environment inability to perform those native steps
on Apple Silicon, preserving the original failures. Intel execution, browser
download first launch, headless browser regression and complete source gate are
still pending. The image wraps existing v1.1.0 published bytes and is unpublished.

Owner explicitly directs the upstream default Mac distribution to DMGs for both
architectures, with Applications copy and manual app quarantine removal. Upstream
branch/PR publication is authorized after the required gates. Actual patch
release publication remains coordinated separately; never overwrite v1.1.0.

## Frozen patch identity preparation

Owner directs version 1.1.1 metadata before final qualification. Two metadata
checks fail first against 1.1.0. Update package/API/display/frontend versions
and release installation names; keep dependency versions, save/engine profile,
all historical chart/roster selections and payload hashes unchanged. The engine
package init diff contains only the two version strings. Review every other
pinned engine/runtime byte against the earlier immutable source contract before
issuing its new explicit metadata-only authority pin. Earlier v1.1.0 payload
native receipts remain under their original identity and do not qualify the
rebuilt v1.1.1 app.

Metadata authority review: compared every engine_files and runtime_files pin
with immutable 2dd6b92594397377a3e0c5c9b7ac9daae3e5aef1. All earlier hashes match that source. The only candidate
change is bowl_bound/__init__.py's two 1.1.0→1.1.1 strings; all other pinned
engine/runtime files are byte-identical. New immutable metadata source commit:
59a9975f4ee59930f27f477aede13c66d7353ade. New canonical contract SHA256:
446ca83bd98ac251c9deb3c0395bd64abdcd92fb4f660dc63df8726adb8609e6. Update both explicit current-runtime authority constants. This
metadata-only reanchor establishes no fresh calibration or new historical fit.


## Source qualification checkpoint

The covered full Python invocation started at 27c9b63 and finished while the
checkout was at 33b5203: 7,006 tests pass in 3,378.46 seconds, with 90.77% branch
coverage against the 75% requirement. Every tracked regular file under
bowl_bound/, backend/, tools/, scripts/, tests/, release/ and pyproject.toml
(478 files) is byte-identical between those commits. The later change is the
synthetic browser-fixture root repair and its frontend regression, documented
in DEV-095. Preserve the exact invocation identity; this is not a claim that a
single frozen-33b5203 full gate ran.

At 33b5203, frontend dependency installation, all 200 frontend tests in 22 files,
the production build and structural audit of 171 generated teams pass. Ruff,
format checking (914 files) and pip check also pass. The chart audit establishes
packaging structure, not fresh historical calibration.

The automatic full runner advanced from Python through its remaining source
checks and reached browser tests between monitoring polls. It was interrupted
with exit 130 after 61 unsuccessful browser attempts; no completed browser
result or complete gate pass is claimed. Earlier evidence records the macOS
agent browser launch restriction. No further local browser probes are planned.
Exact logs, phase receipts, coverage and byte-identity evidence stay private.

Actual v1.1.1 native artifacts remain pending hosted pinned builders. Local
Homebrew Python 3.12.16 and standalone 3.12.10 builds fail the existing reviewed
native-notice/layout guards; a privately expanded official Python 3.12.10 cannot
supply its absolute framework path to PyInstaller hook subprocesses. Preserve
those failures without weakening guards or installing into system directories.
Hosted browser and native checks, published-byte checks on all supported targets,
and fresh browser-download first launch remain release qualification gaps.
DEV-093, DEV-094 and DEV-095 remain open; v1.1.1 is unpublished.


## Upstream qualification phase

Reconsult Paydirt packaging/macos/create_app.sh before upstream progression. Its
Finder app, DMG and Applications-link approach remains relevant; retain Bowl
Bound's exact manifest, verified portable input and native ownership smoke. Do
not reuse Paydirt's whole-payload copy, installer dependency installation or NFL
resources. The packaged release-note entry now describes the prepared feature;
this developer checkpoint continues to record unqualified targets explicitly.

The owner authorizes the scoped branch push and draft PR after the disclosed
local full-gate attempt, to obtain exact-commit hosted browser validation. No
local browser retry is planned. Preserve the existing native source gate: native
compilation requires successful Tests on the exact main push commit, so branch
validation precedes review/merge, then main validation and native dispatch. Do
not weaken that guard or claim branch success qualifies a native release.


## Windows agreement phase

Owner directs retaining all supported platforms and adding the necessary Windows
agreement step. Reconsult Paydirt packaging/windows/installer.nsi: adapt its
standard NSIS license-page approach, but its MIT-only page does not establish
the Microsoft conditions needed here. Keep Bowl Bound's per-user install, exact
file allowlist and preservation of unrelated files; no Paydirt runtime dependency.

The canonical WINDOWS-RUNTIME-TERMS.txt combines the project MIT license and
verbatim pinned CPython Windows binary conditions. SHA256:
7fb48ece6c4ef5203b050d60225c83ee7c1d9a10f4fb8519dc05472988b059b2.
Runtime selection adds exactly this public file and backend/windows_terms.py;
all sample, generated-chart and roster selections/hashes remain unchanged. No
football engine or generator source pins change.

Frozen Windows startup requires an explicit native Yes or exact-hash command-line
agreement before importing the web app, opening a socket or a browser. A per-user
receipt is atomic and bound to these exact terms. No/default/invalid terms or
failed receipt persistence stops startup. The installer shows the combined terms
with an unchecked agreement box; silent install requires the exact hash and
rejects missing/wrong agreement before installation. First app launch records its
own receipt; installer agreement is not silently converted into launcher assent.

Meaningful tests fail first for omitted staged terms, missing hash verification,
missing installer checkbox/silent gate, missing compiler hash transport, missing
published-source hash, GUI invocation/evidence, overwritten receipts and deleted
failed-smoke resources. Native GUI helper unit checks cover owned PID/image, full
text, default No, screen/control/font-fit facts, No/Yes orchestration and cleanup.
These synthetic checks do not qualify the actual Windows interface.

A parallel Windows source-dialog probe uses Python 3.12.10 to catch layout issues
early; it makes no packaged-engine claim. Actual packaged Windows smoke must
exercise native No/Yes, receipt and health/version/shutdown, then the explicit
headless agreement route and complete catalog/game/save checks. Published tests
also require that GUI receipt against the released source terms hash. Preserve
receipts/logs on failure, retain extracted resources when qualification fails,
and never delete evidence to make a rerun pass. Fresh browser-download/default-
browser/security acceptance remains separate. None of these engineering checks
is a statement of legal clearance.

Earlier hosted branch 183f9ad passes Tests run44619660230 and dependency audit
44619660447: 7,006 Python tests, 90.77% branch coverage, 200 frontend tests,
72 real-engine browser cases and 171-team structural audit. Four Python
multithreaded-fork deprecation warnings are retained in the private logs. Those
results do not qualify this later Windows-flow candidate; require its exact-HEAD
hosted source gate before advancing main or compiling release artifacts.


Windows-flow local checkpoint: 430 focused launcher, agreement, notice,
packaging, installer, GUI-helper, validator, workflow and issue tests pass in
16.23 seconds. Repository Ruff and format checks pass (918 Python files).
Pyright on the new agreement/native helper modules, launcher and new helper
tests reports zero errors/warnings; a broader optional script scan also reports
existing object-typed JSON requests, missing local Playwright stubs and
platform-specific winreg attributes, so no repository-wide type-clean claim is
made. Reviewed runtime authority verification passes. No local native GUI or
browser is launched; exact new-source hosted qualification remains mandatory.


The first native Windows source-dialog job at 0526cae failed its combined
ownership/text/default/readability assertion. Its original failure receipt is
preserved; it did not identify which fact failed. Add individual Boolean
diagnostics before selecting a presentation repair; do not weaken readability.
Review also found that an aggregate report could use the reserved GUI receipt
filename and that installer failure cleanup still ran the uninstaller. New
synthetic regressions fail first for both edges. Reserve the GUI filename and
preserve failed installed resources, registration, logs and failure.json; do not
uninstall a potentially active failed app automatically. Successful bounded
smoke still uninstalls normally. Fresh native verification remains pending.


### Native readability correction (v1.1.1 candidate)

The exact-head Windows source-dialog probe at `f7f2214` failed: ownership,
full text and default No passed, but both monitor bounds and text fit failed.
The failed JSON is preserved privately; this is an actual failed native check,
not an unavailable-target exception. Replace the fixed MessageBox with a bounded
modal window containing the complete read-only, wrapping, vertically scrollable
terms. No remains the default; close/Escape declines. The independent helper
uses bounded cross-process text queries, checks styles and monitor/control bounds,
scrolls to the last line using its measured font height, then restores the top
before choosing No/Yes. Receipts distinguish scrolling from simultaneously
fitting all text. Native proof remains pending at this candidate.

Paydirt references reviewed: `scripts/smoke_published_app.py:117-150` and
`docs/dev-notes/release-1.10.3-validation.md`: adapt retained external evidence and
separate candidate/publication claims only. There is no reusable native agreement
dialog in the examined Paydirt launcher/release paths; no dependency is added.
Synthetic regression first: helper 2 expected failures (missing style/scroll
verification), then 82 terms/launcher/helper checks passed; targeted Pyright clean.
The dialog owner separately recorded 11 template/layout failures and six close/
action failures before the corresponding fixes. No local browser/native launch.

The probe also explicitly posts owned WM_CLOSE and requires a clean refusal,
no receipt and (for the packaged app) no server. Direct-close regression first
failed, then all 83 terms/launcher/helper tests passed. Full relevant packaging
regressions: 453 passed before the additional close scenario; final run follows.

Final focused cumulative check: 454 passed (native notices, package/archive,
standalone build/smoke, Windows installer, DMG, published validator, metadata/docs/
workflows, agreement/launcher and issue tooling). Ruff check and format passed
(918 files); targeted helper/backend/new-test Pyright: zero errors or warnings.
Microsoft primary documentation confirms cross-process EDIT text requires
WM_GETTEXT and documents the line/position messages used by the probe:
[GetWindowTextW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowtextw),
[EM_POSFROMCHAR](https://learn.microsoft.com/en-us/windows/win32/controls/em-posfromchar),
[EM_LINESCROLL](https://learn.microsoft.com/en-us/windows/win32/controls/em-linescroll).
