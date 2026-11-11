# Bowl Bound 1.0.1 release preparation

Owner approved publication and the immutable target `v1.0.1` on 2026-11-10.
Track [DEV-084](issues/DEV/DEV-084.md), assigned to Milestone 23 validation.
This is a maintenance release for install validation. Preserve 1.0.0 chart
bytes, engine/save profiles, approved 116 generated teams, two fictional teams
and default port 8001. No new season or historical-import distribution is added.

## Design input and integration

Consulted local Paydirt `AGENTS.md:565-587`,
`scripts/smoke_published_app.py` and
`.github/workflows/post-release-smoke.yml` before this release phase. Adapt
published asset size/digest checks, native runs, rendered UI selection and
persistent receipts/logs. Do not reuse its NFL rules, team data, API, default-port
assumptions, AppImage/DMG formats or runtime dependencies.

The original prototype was created on an older M33 checkout. Its local issue ID
DEV-068 conflicts with an already published Alpha 5 ticket on current main;
preserve that published ticket and track this integration as DEV-084. Integrate
only the validation concept into a fresh release branch based on current main
`dcbdff2`; do not merge obsolete source, roadmap or issue history.

An actual downloaded 1.0.0 arm64 ZIP matched release digest
`d5af67808e0e7219f814fb3dd08f94e2c4d7f1fbb7f3d348ec5b14300aa09cf8`
and launched successfully. The old prototype failed its two-team catalog
assertion because 1.0.0 intentionally includes 118 teams. That is a harness
integration defect, not evidence of missing teams in 1.0.0. Current main already
has complete-inventory and every-team snap/save/load smoke; preserve it. Compare
packaged/API/browser catalogs against the exact approved source manifest for
the released tag, rather than weakening assertions or trusting observed API data.

## Acceptance gates

- Synthetic tests first reproduce identity, catalog, UI and evidence failures.
- Full source gate: Python coverage, lint/format, dependency check, frontend
  unit/build/audit, actual generated-chart audit and real-engine browser tests.
- Inspect the publication diff/history for private charts/PDFs/logs/saves; preserve
  the exact generated/sample allowlist and source attribution.
- Push approved immutable source without force, build on all three native
  platforms, inspect artifacts and installer lifecycle before publication.
- Publish 1.0.1 with checksums under a new immutable tag; download those actual
  bytes and require all four native distribution checks to pass on runners.
- Retain receipts/logs/screenshots and disclose unsigned fresh-download
  Gatekeeper/SmartScreen and automatic-browser first-launch limitations.

## Verification

Metadata expectations first failed twice against unchanged 1.0.0 identity; after
coordinating package/API/frontend/launcher metadata, all three focused identity
checks passed. Dependency installation used Node 24.22.1 and reports the existing
`whatwg-encoding` deprecation warning, zero vulnerabilities.

The integrated validator passed against the actual published 1.0.0 arm64 ZIP:
all 118 teams matched the independent released source catalog, every team passed
snap/save/load, Chromium rendered the exact catalog, and both fictional and
generated matchups started successfully. Receipt, server log and screenshot are
retained under ignored `private-data/install-validation-v1.0.0/`.

Focused validator/workflow/metadata/launcher checks passed: 61 tests. The
immutable-tag checkout regression first failed against the ambiguous workflow
ref, then passed after explicitly checking out `refs/tags/<release_tag>`.
An initial full Python run was interrupted to make this final workflow correction;
it is not counted as passing. A fresh full coverage run is in progress.

Frontend unit checks passed all 158 tests in 19 files, production build passed,
`npm audit` reported zero vulnerabilities, Ruff lint/format passed, dependency
check passed, and the generated-chart audit passed all 116 teams. Source manifest
sample/generated hash maps remain identical to 1.0.0.

Remaining full-suite, browser, native-build and publication evidence will be
appended here. No native 1.0.1 release result is claimed yet.

Real-engine Chromium regressions passed all 64 cases in 4.2 minutes using
`PLAYWRIGHT_BROWSERS_PATH=/private/tmp/bb-release101-browsers` and synthetic
`BB_E2E_SEASONS=/private/tmp/bb-release101-e2e-seasons`, with Node 24.22.1.
The run emitted Node's `NO_COLOR`/`FORCE_COLOR` precedence warning; no cases were
skipped. Complete regulation/overtime games, save/load, statistics and desktop/mobile
flows passed. Independent subagent publication review found no private content or
new chart rights scope in the candidate and confirmed the bare-runner import and
workflow YAML/Bash syntax. The untracked local `.venv` symlink is excluded from
publication staging.

Commands for the source acceptance gate (run from the release worktree; frontend
commands from `frontend/` with Node 24.22.1 on PATH):

```sh
.venv/bin/python -m pytest --cov --cov-report=term-missing -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pip check
.venv/bin/python -m scripts.audit_generated_charts --report /Users/rtulloh/work/bowl_bound/private-data/install-validation-v1.0.1-chart-audit.json
npm test
npm run build
npm audit
PLAYWRIGHT_BROWSERS_PATH=/private/tmp/bb-release101-browsers BB_E2E_SEASONS=/private/tmp/bb-release101-e2e-seasons npm run test:e2e
```

Full Python coverage completed successfully: **5,585 passed** in 2,783.32 seconds
(46m23s of reported test runtime), **92.25% branch-aware total coverage**, above
the enforced 75% threshold. No failures, skips or warnings were reported by this
final run. The original process survived the owner's commute/sleep and was
observed continuing before completion; it was not restarted. Full output is kept
in ignored `private-data/install-validation-v1.0.1-full-python-final.log`.

All required local source gates now pass. Native builds and actual published
1.0.1 download verification remain required before marking DEV-084 resolved.

Reviewed source committed and pushed without force as
`3af84de4b5992043180b07ead07c389929650804` (`v1.0.1: validate published install
artifacts`), based directly on 1.0.0 main. The unrelated original checkout remains
untouched. Dispatched native build run
[43066061540](https://github.com/rtulloh/bowl_bound/actions/runs/43066061540)
with that full source SHA. Also dispatched the four-platform downloaded-release
workflow against existing v1.0.0 as an initial hosted harness check:
[43066060876](https://github.com/rtulloh/bowl_bound/actions/runs/43066060876).
Both results are pending; no v1.0.1 tag or release has been published yet.

## Native build and publication evidence

Build run 43066061540 completed successfully for all three native platforms,
including Windows installer install/application/uninstall checks. Its hosted
full source gate passed 5,585 tests with 92.25% coverage, 158 frontend tests and
64 browser cases. macOS jobs correctly skipped Windows-only compiler/installer
steps. The Windows PyInstaller build emitted the nonfatal existing warning
`Hidden import "tzdata" not found!`; its packaged API/game/save smoke still
passed. The dependency installation retained the documented `whatwg-encoding`
deprecation warning. Functional results do not certify fresh-download signing,
Gatekeeper/SmartScreen or automatic default-browser first launch.

Initial hosted validation of actual v1.0.0 downloads passed all four distributions
in run 43066060876. Downloaded receipts explicitly report success, exact 118-team
catalogs, fictional/generated UI starts, retained logs/screenshots, and Windows
installer uninstall verification.

Downloaded native build assets were independently inspected before publication:
all portable inventories and file digests verify; source and embedded sidecar
manifests match; each includes exactly the approved 595 team/provenance files for
118 teams, plus the approved generated-license document and runtime/legal files.
No private PDFs or saves are included. The initial ad hoc inspection rejected the
public generated-license document because it treated every seasons-path file as
a team file; correcting that inspection to explicitly allow its source-matching
hash produced a pass, without changing packaging or widening team data scope.
Exactly 11 assets were staged; generated-chart diagnostic workflow artifacts were
excluded from publication.

Published [v1.0.1](https://github.com/rtulloh/bowl_bound/releases/tag/v1.0.1) at
2026-11-11T22:08:31Z, regular/latest release, immutable tag targeting the built
source `3af84de4b5992043180b07ead07c389929650804`. All 11 downloaded published
files match the inspected build bytes, published GitHub digests and sizes.
Portable SHA-256 values: arm64 `10a0f039a6b905a5d6092728c09d6e62df6ebb57372ab61cfa0e0b558b982b05`;
Intel `18ff713a0e06c33ecb2ea65e82d720f9d398ae6a6849b4ce8f1d688e8b793c30`;
Windows `634d4766eee1d263e0aff24b9ec1ebe17b05b42cb7265c02853493ac70d7cd5c`.
Installer SHA-256:
`362cc4ef62afa5b980ef9ec710ecb6062d51d3cd64dc1ac9b88920b8466d48eb`.

Actual v1.0.1 downloaded-install workflow
[43109240481](https://github.com/rtulloh/bowl_bound/actions/runs/43109240481)
is running. Its four successful receipts remain the final functional gate.

## Final acceptance

Run 43109240481 completed successfully for **all four actual published v1.0.1
distributions**: macOS arm64, macOS Intel, Windows portable and Windows installer.
All four downloaded receipts report `passed: true`, version/tag 1.0.1, the exact
118-team source-approved catalog, rendered selectors, fictional and generated
new-game creation, and matching published asset/source-manifest digests.
Existing every-team API snap/save/load checks and clean shutdown also passed;
the installer receipt confirms uninstall verification. Receipts, server logs,
screenshots, published release JSON and complete workflow logs are retained in
ignored `private-data/release-1.0.1/` and
`private-data/install-validation-v1.0.1-published-validation.log`; hosted evidence
has 14-day retention. The artifact upload preserves separate `install-validation/`
and `published-download/` directories under each native artifact.

Independent subagent review confirmed the immutable tag/source, 11 exact assets,
byte/digest matches, complete ZIP inventories, unchanged 2007-only catalog and
absence of private source material. All release acceptance gates are satisfied.
DEV-084 is resolved against tested commit `3af84de4`; leave it awaiting owner
play-test confirmation before closing. Unsigned fresh-machine security acceptance
and automatic default-browser opening remain explicitly outside these automated
functional checks. No new season was added. This final evidence update changes
only documentation/ticket metadata; the published tag and application bytes are
unchanged. The full local and hosted gates above cover those exact bytes.

Final documentation/ticket checks passed:
`.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_release_metadata.py -q -o addopts=`
(**20 passed**), regenerated issue index, and `git diff --check`. A second
independent final audit inspected all four retained receipts, clean logs and
valid screenshots and found no blockers. Only the three evidence/ticket/index
files differ from the fully tested built source; unrelated original-checkout
changes and the untracked environment symlink remain untouched.
