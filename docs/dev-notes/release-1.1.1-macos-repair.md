# v1.1.1 macOS packaging repair and publication

Milestone 42 follow-up, tracked as [DEV-093](issues/DEV/DEV-093.md).
The release is published; all six hosted published-download checks passed.
Fresh browser-download first-launch acceptance and Intel macOS 26 validation
remain gaps. The final publication closeout below supersedes prospective status
in the chronological candidate notes. The v1.1.0 tag/assets remain unchanged.

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

Publication workflow default correction: post-release verification now defaults
`include_dmg=true`, so normal dispatch checks the primary Mac downloads.
Legacy ZIP-only releases such as v1.1.0 can explicitly opt out; v1.1.1 requires
all six native checks. Regression first failed against false, then passed.
This adapts Paydirt published-artifact evidence separation reviewed above; no
legacy release exception is reused.

Exact-head hosted Tests `44647019043` at `48fb587` failed after 7092 passed,
one failed and four warnings in 8440.78s; branch coverage90.53%. The sole
failure was an unchanged workflow test asserting that Tests has only one job.
The new mandatory Windows dialog job was omitted from that test update and the
focused selection. Correct the explicit two-job expectation and separately
assert the Windows native pin, mandatory parallel execution, source identity,
probe arguments and always-retained evidence. Existing full Ubuntu regression
assertions remain intact. No engine failure occurred; this run did not reach
frontend/browser checks and does not qualify the candidate. New exact-head
full Tests and Audit remain required; no main/tag/release mutation occurred.

For this tests/docs-only delta, the owner accepted identity-scoped validation:
previous full7093-case execution plus corrected38 focused checks, unchanged
production/runtime/workflow bytes, local frontend200 tests and productionbuild,
and mandatory fresh exact-head hosted full Tests/Audit. No new-head whole-gate
pass is claimed before that run. Local npm initially used Node18 and failed at
startup; rerun with reviewed Node24.22.1 passed200 tests/22files and build.
Ruff check/format passed; pip check found no broken requirements.


### 2026-11-20 — Intel Finder failure diagnostic checkpoint

Exact source `443d825` passed branch and main full hosted Tests and Audit,
including 7,094 Python tests, 200 frontend tests and 72 browser tests. Native
build runs `44689834726` and `44690919058` both failed Intel Finder-to-Terminal
startup: the initial ZIP payload passed, and the image verified/mounted/copied,
but no owned server appeared in 60 seconds. The copied-image payload check was
not reached. Apple Silicon and Windows native checks passed both attempts;
this does not qualify Intel or permit publication. Preserve both failed runs.

The failure resource folder was retained on the runner but omitted from the
upload glob. A diagnostic workflow branch now captures that folder separately,
including the app inventory, file modes/sizes/architectures, plist, quarantine
attributes, process/session facts and bounded native logs. Commands do not
launch applications, request Automation consent, alter permissions or stop
processes. Every receipt is explicitly unqualified. Each command has a ten-second
timeout. The failed app copy and original failure receipt remain separate from
player artifacts. No local GUI or browser probe is run.

The workflow definition and diagnostic helper have their own identity; the
compiled payload stays pinned to qualified main source `443d825`, with the exact
main-push source guard unchanged. This is a diagnostic experiment after two
reproduced failures, not a third unchanged qualification attempt. Root review
precedes dispatch. No v1.1.1 tag or release exists at this checkpoint.

Paydirt consulted for this phase: `scripts/smoke_published_app.py:117-150` and
`docs/dev-notes/release-1.10.3-validation.md`. Adapt retained external failure
evidence and candidate/publication separation only. No runtime dependency,
private data, launch substitution or old release exception is reused.

Synthetic tests first rejected absent diagnostic steps; the initial helper
failed on its missing module. A later regression proved that even querying an
existing Terminal using AppleScript could start it after a race; all Automation
requests were removed. Focused diagnostic/workflow/DMG/docs/issue checks: 53
passed. This checkpoint adds diagnostic tooling only; release payloads, football
rules, charts, runtime manifest and source guard are unchanged.


### 2026-11-20 — bounded diagnostic evidence correction

Instrumented run `44703619086` reproduced the Intel Finder timeout while
Apple Silicon and Windows passed. Its retained copied payload matches all
1,228 ZIP files byte for byte; all four startup files are executable and the
binary is x86_64. No quarantine attribute is present. The console belongs to
the runner and Terminal has a login-shell descendant, but no payload process is
observed. These facts do not establish a cause or justify changing the launcher,
startup timeout, permissions, runner or release platforms.

The first collector truncated the mixed system log to its final 64 KiB,
discarding the initial startup interval. A bounded collector-only correction
queries Terminal and LaunchServices separately over five minutes, retains both
ends within a 1 MiB budget per stream, and records original/omitted lengths and
retained ranges. Immediately on entry it snapshots Terminal's observed process
chain, queries arguments only for those at most 64 PIDs, and requests a hosted
screen capture. Capture times, elapsed deltas and denied/error outcomes remain
explicit. The screenshot does not request Automation, alter permissions or
interact with the UI. It may be unavailable and is never a launch pass.

No payload or launcher trace overlay is added. Compiled source remains qualified
main `443d825`; diagnostic workflow/helper identity is recorded separately. A
materially improved instrumented investigation requires review and a fresh full
source regression before push. No new qualification retry or publication occurs
at this checkpoint. Root and an independent reader reviewed the first native
facts; the original failed evidence is preserved privately.

Paydirt reconsulted: `scripts/smoke_published_app.py:117-150` and
`docs/dev-notes/release-1.10.3-validation.md`. Adapt external screenshot/evidence
retention and separate publication claims, without reusing its prior exception.
Three new synthetic assertions failed first for separated logs, truncation and
bounded descendants; two further assertions failed for both-end retention and
entry-time capture. Focused collector/workflow checks then passed: 29 tests.
No local screen capture or native launch is exercised by these tests.


Root review added two evidence safeguards before freezing: targeted process
arguments use `ps -ww`, and command timeouts preserve decoded bounded partial
stdout/stderr with explicit incomplete/timed-out status. Both regressions failed
first, then passed; a successful mocked screenshot also verifies its saved path
and SHA-256. Final focused cumulative check: 60 passed; changed-file Ruff/format
and Pyright pass. The preceding diagnostic identity `2b099a4` independently
passed all ten full local stages (7,100 Python, 200 frontend, 72 browser tests,
171-team audit; 90.53% coverage), with npm deprecation and Node color warnings
preserved. Those results do not qualify this changed collector; run its own
fresh full gate before push. No local desktop snapshot or native launch.


### 2026-11-20 — retain Intel validation on a supported runner image

The improved collector run `44717807121` again failed the Intel Finder launch;
ARM and Windows passed. Its immediate screenshot shows a Finder desktop with
no Terminal window or permission dialog. Complete, untruncated logs show that
Terminal checks in but does not finish startup or create a shell descendant
before the existing bound. The wrapper's `open` process exits normally. No
payload defect or exact blocked stack is proven by these observations.

The affected runner reports image `20260824.0517.1`, exactly the image described
in the primary runner reports [14773](https://github.com/actions/runner-images/issues/14773)
and [14751](https://github.com/actions/runner-images/issues/14751). They document
an Intel macOS 26 IconServices/Metal failure that blocks AppKit clients; the
latter report records macOS 15 Intel and macOS 26 ARM controls as unaffected.
This is a strongly matching environment hypothesis, not a stack/crash receipt
from this Bowl Bound run. Preserve every failed native check and its evidence.

Use the officially available `macos-15-intel` label for Intel builds and both
published Intel asset checks. Keep all three native targets, all six published
checks, Python 3.12.10, exact source guards, launch path, timeout, permissions,
services and catalog/game/save/browser assertions unchanged. No runtime file,
manifest, chart or wrapper changes. macOS 26 Intel remains an explicit failed
CI image gap, not a passing OS-specific qualification; there is no claim that
physical Intel Macs running that OS are defective or verified. Player guidance
had no OS-version support promise; maintainer runner documentation is updated.
The default-DMG prose erratum is corrected with this necessary workflow change.

GitHub's [hosted-runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
currently lists `macos-15-intel` for both public and private repositories.
Two synthetic workflow assertions failed first (build architecture mapping and
both published Intel asset runners); the matrix expectations retain every
existing target and all safety/validation steps. Fresh focused and full source
checks, review, and actual native qualification remain required before publication.

Paydirt consulted for this phase: `.github/workflows/post-release-smoke.yml:42-63`
still selects macOS 26 Intel; adapt its architecture-complete published-byte
matrix/evidence retention, not that unverified runner choice. The examined
`.github/workflows/build.yml` and `docs/dev-notes/release-testing.md` paths are
absent there. Prior Paydirt release exceptions are not reused.

Focused runner/workflow/collector/DMG/docs/issue regression: 67 passed; repository
Ruff/format (920 files), dependency check and whitespace checks passed. No new
native result is claimed; freeze and run the fresh full gate before push.


### 2026-11-20 — published v1.1.1 verification closeout

[v1.1.1](https://github.com/rtulloh/bowl_bound/releases/tag/v1.1.1) is published
as the regular latest release. Its immutable tag and compiled source are
`443d8255f4597f1fb24d5e61235b3bd09335c054`; source Tests `44676127824` and
Dependency audit `44676127826` passed that exact main-push commit. The build
workflow definition is `7ce9de69477288f138f4226ecb2446e590f82476`, separately
from the compiled source. [Native build 44732623182](https://github.com/rtulloh/bowl_bound/actions/runs/44732623182)
passed ARM macOS 26, Intel macOS 15 and Windows targets. No artifact is relabeled
as a build of the newer workflow commit. The v1.1.0 tag/assets remain unchanged.

[Published-download run 44735680143](https://github.com/rtulloh/bowl_bound/actions/runs/44735680143)
passed all six jobs: both Mac DMGs, both Mac ZIPs, Windows portable and Windows
installer, with no skipped targets. Each checked the published digest, exact
173-team API/rendered catalog, real-engine game/save behavior, error-free logs
and normal shutdown. Both Windows routes passed native scrollable terms
No/close/Yes checks. Both DMGs passed mounted/copied Finder/Terminal launch.
Independent fresh downloads of all 15 published assets matched the frozen
publication copies, original native artifacts and GitHub digests; private audit
SHA256 `d711bc8c8110200796792c084c09078cd5757c83b8e9e36cffa0e9b9ef985b4c`.
Six-receipt/log/browser-evidence summary SHA256 is
`91eaeea266266fd0f7e7a9c88c40de931fb7479271400488ff89f7c00df7c6da`.
Detailed receipts, screenshots, acquisition bytes and logs remain private.

Fresh browser-download first-launch/default-browser/security acceptance remains
pending. Intel macOS 26 CI-image checks failed and remain an explicit gap; the
Intel macOS 15 pass does not establish macOS 26 Intel compatibility. These are
unsigned, unnotarized Mac builds; Windows unknown-publisher/SmartScreen limits
remain. Keep the associated tickets open pending applicable owner play-test confirmation;
no signing, legal-clearance or fresh-machine acceptance is claimed.

For this documentation phase, consulted Paydirt
`docs/dev-notes/release-1.10.3-validation.md`: adapt its separation of earlier
candidate checks, publication verification and unresolved limits. Do not reuse
its urgent-release waiver, NFL behavior or private data. The owner explicitly
directed upstream fast-tracking and no further local regression/checks; this
closeout changes documentation only. Earlier local checks retain their original
commit identities, including the 72-browser-test pass recorded for `7ce9de6`.
No new local tests, launches, builds or calibration are claimed here.


### 2026-11-20 — owner first launch fails after publication

The owner's actual copied `/Applications/Bowl Bound.app` 1.1.1 launch silently
failed to open Terminal/browser or listen on port 8001. Recursive quarantine
attributes are absent; the installed launcher, command and start script are
executable. Process 27217 remains `/bin/bash .../Contents/MacOS/launch`, with no
child process, before the wrapper's `exec /usr/bin/open` Terminal hop. A bounded
read-only sample contains only Rosetta Runtime frames and a 204 KB footprint;
this does not prove a particular architecture/policy root cause. Installed bytes
are preserved and no GUI, installed-app modification or local test was performed
by this investigation. Direct command launch is awaiting owner evidence.

This is an actual failed owner first-launch check, superseding the earlier
"pending" designation. Preserve all six hosted published-download passes and
the independent 15-asset byte audit: they do not qualify this failed first launch.
DEV-093 remains open. No production fix or next patch is selected yet.

Consulted Paydirt `packaging/macos/create_app.sh`: its CFBundleExecutable is the
native frozen binary and its completed bundle is ad-hoc sealed, unlike this
Terminal shell wrapper. These are relevant design differences, not evidence of
the cause. Do not copy its one-file assumptions or change Bowl Bound packaging
until the actual failure mechanism is established. Owner-directed upstream-only
validation remains in effect; no local regression or launches are run.


### Prospective v1.1.2 — explicit shell-app architecture

Apple's [universal macOS binary guidance](https://developer.apple.com/documentation/apple-silicon/building-a-universal-macos-binary)
explains that script-only app launchers may default to Rosetta and recommends
`LSArchitecturePriority`. The installed app has no architecture preference and
its stalled interpreter sample is entirely Rosetta frames. This supports the
smallest packaging repair: set `LSArchitecturePriority` to exactly `arm64` for
the ARM payload or `x86_64` for Intel. Reject unsupported targets before copying.
Do not add `LSRequiresNativeExecution`, alter launcher/Terminal flow, sign the
wrapper, modify payload files or change the startup bound in this repair.

Synthetic architecture-priority and unsupported-target regressions were written
before implementation. Per the owner's explicit direction, they are not run
locally: upstream CI must establish their result, along with the full source
gate and all native/published checks. No red/green local result is claimed.
The new patch version is 1.1.2; immutable v1.1.1 tag/assets are not replaced.
Paydirt's native-binary entrypoint noted above avoids the script-only ambiguity;
reuse the explicit target-identity principle, not its one-file/runtime design.


### v1.1.2 native entrypoint and completed bundle seal candidate

The architecture preference alone is not a demonstrated repair: explicitly
native script launch stalled at the next script, and a direct ARM64 payload
probe stalled at `_dyld_start`. The security log also reports evaluations
waiting on an existing evaluation. Rosetta frames alone did not establish
causality. No security service, installed app or policy is modified.

Consulted Paydirt `packaging/macos/create_app.sh:15-17,39-40,53-57` and its
installed native app topology, alongside Bowl Bound `backend/launcher.py`.
Use a target-native C/Mach-O entrypoint that opens the existing command in
Terminal, preserving server output and Ctrl+C lifecycle. A native server as
the app entrypoint would hide the documented Terminal lifecycle. The shim
uses only macOS frameworks, resolves its own path, and displays an actionable
alert on failure to execute the Terminal opener. It does not interpret football
state or depend on Paydirt.

Ad-hoc seal the fully composed app and require `codesign --verify --deep
--strict` before image creation or any launch smoke. This is not Developer ID
signing or notarization and is not proof the owner's policy wait is repaired.
The earlier private static audit found strict framework-context failures in
flattened Python.framework copies on both ARM and Intel. Preserve that known
risk: this candidate must fail closed if encountered, without weakening the
check or silently rewriting frameworks. Any such failure needs a separate
evidence-based decision.

Compiler-target and signing/strict-failure synthetic tests are written before
the implementation; execution is upstream only per owner direction. No local
red/green result is claimed. Actual new artifact first launch remains required.

Paydirt `paydirt/__main__.py:39,183-210` also starts its frozen browser/server
mode from a native executable and keeps a main thread alive. Do not reuse its
server-thread lifecycle: Bowl Bound retains its own uvicorn signal/shutdown
behavior and visible Terminal ownership.

Upstream architecture-only run `44738510895` failed eight version-identity
checks (7,103 passed): the candidate initially missed the Python runtime/display
constants when bumping package/frontend metadata. Correct both constants and
the exact metadata expectations to 1.1.2; preserve the failed receipt. This
metadata correction changes no gameplay/save profile and claims no test pass.

Runtime authority follow-up: upstream `44759366649` refused the changed
version bytes before tests. Independent static review compared all 40 engine
and 12 runtime pins against immutable `59a9975f4ee59930f27f477aede13c66d7353ade`: only
`bowl_bound/__init__.py` differs, exactly the two 1.1.1-to-1.1.2 strings.
The other 51 files and engine path census are unchanged. Explicitly reanchor
that metadata-only source to `801bf6ab0cc018d1b3a5491d3f2ed7381ffef354`, with
canonical contract SHA256
`1d3d5f40e46ad2f75c9ce97025bc0ef72b9b581e6e6afa0f10dc2ffa5bff5ec5`.
The runtime guard remains enforced. This establishes no new chart calibration,
historical fit or native first-launch pass. No local tests are executed.
