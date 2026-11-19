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
