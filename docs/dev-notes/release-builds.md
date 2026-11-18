# Release preparation and artifact selection

This is maintainer guidance, not player release notes. No command below creates
a GitHub remote, tag or public release. The current target is standalone apps;
the ZIP below is a verified native-builder input, **not** a finished player app.

## Running the full regression locally

Create the project environment once, then run the gate from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,web,pdf]'
.venv/bin/python scripts/run_full_regression.py
# Alternative module invocation:
.venv/bin/python -m scripts.run_full_regression
```

Before the expensive hosted Python regression, CI verifies the reviewed generator
runtime identity. Version bumps also change a pinned engine metadata file;
review and update its immutable source contract explicitly, following
[runtime identity guidance](#reviewed-chart-generator-identity).
Failure is not waived or treated as successful qualification.

The runner performs the same checks as `.github/workflows/tests.yml`: Python tests/lint/
format/dependency checks, frontend install/tests/build, generated chart
audit, and real-engine Playwright tests. It prints each command, elapsed time,
and a final pass/fail/skipped table. It stops at the first failure by default;
use `--keep-going` to collect all failures. `--report PATH` writes a JSON
summary, and `--skip-frontend`, `--skip-e2e`, `--skip-chart-audit`,
`--skip-python` and `--no-install` provide intentional partial runs.

Dependency vulnerability auditing runs separately in
`.github/workflows/dependency-audit.yml` (**Dependency audit**). It retains the
complete npm JSON for 14 days and uses `scripts.check_frontend_audit.py` to apply
the exact DEV-087 picomatch waiver through December 17, 2026 UTC. All unrelated
findings, critical package entries, expired waivers and audit errors fail.
The local full-regression runner excludes this separate check; run
`.venv/bin/python -m scripts.check_frontend_audit --report /tmp/bowl-bound-npm-audit.json`
independently. Require its successful exact-commit hosted result before publishing
this release. Policy acceptance does not mean the vulnerability is fixed; see
[dependency security](dependency-security.md) for scope and removal conditions.
Local Python tests run without coverage for speed. Run `pytest --cov` as part
of individual changes; the upstream CI gate enforces the 75% `fail_under`
threshold.

The hosted Python command uses four `pytest-xdist==3.8.0` workers with
`--dist=loadgroup` and retains combined branch coverage and the same 75% floor.
Only the wheel-building tests share the `checkout_wheel` group, because they
write shared checkout build state. Independent generator cases run across workers.
The development pins are pytest 9.1.1 and xdist 3.8.0: pytest 9.2.0 currently
breaks group scheduling ([upstream report](https://github.com/pytest-dev/pytest-xdist/issues/1407)).
Native requirements remain separate. The source job retains its 240-minute bound
and prints its 25 slowest tests; that bound is not a performance acceptance target.
Run the same Python coverage command locally:

```sh
.venv/bin/python -m pytest --cov --cov-report=term-missing -n 4 --dist=loadgroup --durations=25 -q
```

The local runner above keeps its serial, no-coverage default. To diagnose slow
Python cases without rerunning other groups, use the explicit command above;
that diagnostic alone does not replace the complete regression gate. See the
[xdist scheduler](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)
and [combined coverage](https://pytest-cov.readthedocs.io/en/latest/xdist.html)
documentation for the upstream execution model.

`--python PATH` selects the project interpreter (default `.venv/bin/python`).
`npm ci` and `npx playwright install --with-deps chromium` need network access
on a cold machine; the remaining checks run against local dependencies. The
generated chart audit and browser fixtures are written under temporary
directories and are removed when the run ends.

## Stage, build and inspect

Use Python3.10+ and the project web dependencies. Select Node24.22.1/npm11.19.1
on PATH before the frontend step. Outputs must not exist, must have existing
parents, and must be outside their input tree. Paths and parent directories must
not be symlinks. Use an approved temporary/release workspace, not a team folder.
Example with environment variables set to absolute paths:

```sh
python scripts/release_package.py stage "$SOURCE" "$STAGE"
python scripts/release_package.py frontend "$STAGE"
python scripts/release_package.py runtime "$STAGE" "$RUNTIME"
python scripts/release_package.py archive "$RUNTIME" "$ARCHIVE"
```

`release/manifest.json` is the reviewed inventory, not a glob or a Git ignore
filter. Only its exact runtime and frontend input files are copied to a new
transactional stage. Every selected fictional chart/roster/provenance/license
file has a pinned SHA256; changing samples requires deliberate manifest review.
The current public selection includes exactly the two original 2007 sample
rosters and their CC0 source notes with owner approval (DEV-042). An optional
`roster_sha256` map can separately select reviewed historical roster/source-note
pairs for exactly selected generated teams; the capability does not grant
publication approval or expand the sample allowlist. Each selected pair needs
its own exact hashes, ordinary nonempty roster validation and matching runtime
entries. The native archive reuses that assembled inventory, requiring the exact
season/team roster path and unchanged bytes; the extractor and Windows installer
retain both files. Unselected historical rosters remain excluded.
Unknown file categories, traversal, duplicate entries, missing inputs and
symlinked files/ancestors fail before output creation.

Alpha 6 also selects the owner-approved generated statistical cohort through an
exact `generated_sha256` map: each complete four-file chart bundle and matching
generated virtual-cell provenance CSV is hash-pinned. The two original fictional
samples retain their original hashes and rosters. Historical roster pairs require
the separate exact selection above; private imported benchmarks remain excluded.
See [generated-content scope](../generated-charts.md).

Native smoke allows 30 seconds for complete catalog discovery because listing
validates every chart and provenance bundle. It records elapsed discovery time,
reconciles the exact expected catalog and exercises every team's snap/save/load.
Ordinary health, version, game/save/load and static-asset requests retain their
five-second deadlines.

When adding or moving application modules, update the runtime selection for their
imports, including dependencies loaded only when a game is created. Source tests
can find modules that an exact staged runtime lacks; successful freezing alone
does not prove those imports resolve. The release regression imports the staged
web/CLI entry points and creates a default game with only the original fictional
samples while blocking checkout/editable application fallbacks. Keep the frozen
executable smoke required as well: it exercises packaging and third-party dynamic
imports that a source-level probe cannot certify.

Frontend imports need the same selection review. The release regression checks
local imports inside the staged JS/JSX sources; a full-checkout Vite build can
otherwise hide a missing allowlisted component. Retain the clean staged Vite
build as the authoritative bundler check, including any future asset/import forms.

Keep the repository `.gitattributes` policy when checking out release inputs:
tracked text uses LF even when Windows Git has `core.autocrlf=true`; binary
files retain their bytes. This preserves pinned sample hashes and version
metadata across hosts. Do not rewrite samples, update approved hashes, or
normalize bytes inside the verifier to work around a checkout mismatch.

The frontend step checks exact Node/npm versions, runs `npm ci --ignore-scripts`
and `npm run build` from selected staged sources. It never copies the worktree
dist or node_modules. A pre-existing dist/receipt is refused. Failed builds do
not issue a receipt; retry from a fresh stage. Receipts hash selected inputs and
built outputs. Changed source, missing/unexpected/symlinked assets, unreferenced
assets or stale hashes prevent runtime assembly. All HTML references must point
to local hashed JS/CSS assets. Future images/fonts/code splitting need a reviewed
extension of this contract; do not relax it with recursive directory copying.

Runtime assembly omits build sources, developer docs/config, tests, importers,
audit tooling, node_modules, private data and unselected team files. VERSION and
MANIFEST.json contain public version and file hashes, not developer paths. The
ZIP step re-inspects exact contents/hashes and uses fixed timestamps/permissions
for reproducible same-input bytes on a given compression implementation. It
refuses extra files, stale contents or existing outputs. Keep runtime inputs
pristine: smoke tests should set PYTHONDONTWRITEBYTECODE=1, or use a separate copy,
so Python caches do not become unexpected input files.

Build scripts/manifests and dependency downloads remain trusted build inputs,
not a sandbox against a malicious contributor with write access. Review them
and build from a clean approved commit before publication. Hash receipts prevent
accidental stale/mixed inputs, not deliberate forgery by a local attacker.

## Remaining publication gates

DEV-034 launcher, DEV-035 player documentation/notices, DEV-036 pinned native
PyInstaller builds/checksums and DEV-037 Git/history/privacy/clean-machine audit
remain required. Extend the exact runtime manifest with approved player files
as those tickets land. Do not ship this intermediate ZIP as a standalone app.
Native platform testing/signing caveats, transitive dependency license inventory,
artifact inspection and explicit owner go/no-go cannot be inferred from a clean
manifest or npm audit. Preserve historical files locally; never delete them to
make a build pass. Do not publish developer notes or local audit evidence as
player release notes.

## Verify public release visibility

After publishing, verify both the direct release URL and the rendered repository
Releases panel. When the owner expects the new alpha featured there, check that
`gh api repos/rtulloh/bowl_bound/releases/latest --jq .tag_name` returns its tag.
GitHub prereleases cannot be designated Latest; Alpha 3/4/5 use ordinary GitHub
release metadata for that panel while retaining their alpha names and caveats.
See [GitHub release metadata](https://docs.github.com/en/rest/releases/releases#update-a-release).
Keep the build/tag and verified asset inventory immutable when correcting these
visibility flags. DEV-068 records the Alpha 5 correction and actual browser check.

## Manual native workflow and Windows installer

`.github/workflows/tests.yml` is named **Tests** and runs automatically on
branch pushes (including main and isolated workstreams) and pull requests. Its
run is associated with the pushed/PR commit. The Ubuntu regression job runs coverage,
lint/format, pip check, frontend unit/build and real-engine Chromium tests.
Dependency auditing runs in the separate policy workflow described above.
It neither builds native executables nor publishes releases.

`.github/workflows/build.yml` is manually dispatched from GitHub Actions →
**Build and Release Standalone Executables** → **Run workflow** after the
workflow is approved and pushed. The name describes the release-build purpose;
its existing controls remain artifact-only. It creates no tags or GitHub
releases and has no automatic tag/build/publication trigger. `contents: read`,
exact action SHAs and disabled checkout credentials remain required.

The manual workflow requires a successful **Tests** main-push run for the exact
requested commit; it does not rerun full coverage. Its small verification job has
only repository/actions read permissions. Missing, pending, failed, canceled,
foreign-repository or mismatched workflow evidence fails closed, and a newer
failed run cannot reuse an older success. Finish the push gate before dispatching.
The three native targets share this prerequisite and retain their own platform
build/smoke checks.

Optional `source_ref` must be a full 40-character lowercase commit SHA; leaving it
blank uses the dispatch commit SHA. The verifier runs from the dispatch checkout,
and native jobs check out only its verified output. No branch, tag, cached build
result or unrelated green run substitutes for exact-commit evidence. For example,
after successful source validation and workflow publication:

```sh
gh workflow run build.yml --ref main -f source_ref=<reviewed-full-main-commit-SHA>
```

Run the standalone workflow only when native artifacts are needed; ordinary
regression status comes from **Tests**. A passing source test run does not replace
native executable/installer acceptance or authorize publication. Native builds
run on macOS 26
arm64, Windows Server 2025 x64 and macOS 26 Intel x86_64. These runner labels
were checked against actions/runner-images; availability is still exercised
by the first actual run. Linux is a test host, not an artifact target.

Linux source qualification uses Python **3.12.16**. Native builds and published-
artifact harnesses use **3.12.10**, the latest Python 3.12 binary published for
all selected macOS/Windows targets in the actions/python-versions manifest.
Later 3.12 security releases are source-only upstream and lack those setup-python
artifacts; this pin does not claim the security fixes from 3.12.16. The native
notice catalog is pinned to the actual 3.12.10 distribution. Node is **24.22.1**. Each native job
creates a separate environment, installs only the exact graph in
`release/requirements-native.txt` with `--only-binary=:all: --no-deps`, and runs
`pip check`. Do not install Bowl Bound into that environment, including
editably. The orchestrator runs from the checkout, but PyInstaller runs with
isolated imports from a temporary directory and analyzes only the assembled
allowlisted runtime. Analysis runs with `-I -B` and passes
`PYTHONDONTWRITEBYTECODE=1` to hook children so imports cannot add caches to
verified inputs (`-I` ignores Python environment settings in the parent).
Unexpected/missing inventory errors list relative paths; investigate them
rather than deleting or ignoring files in the verifier. Application modules
and selected resources are inspected.
This is exact application/data selection, not an exact allowlist of every
third-party binary. Build logs and the native dependency/license inventory
need review before publication.

Equivalent native commands (use the matching platform interpreter and target):

```sh
python -m venv "$BUILD_ENV"
"$BUILD_PYTHON" -m pip install --only-binary=:all: --no-deps -r release/requirements-native.txt
"$BUILD_PYTHON" -m pip check
"$BUILD_PYTHON" -m scripts.build_standalone --target macos-arm64 --output "$OUTPUT"
"$BUILD_PYTHON" -m scripts.smoke_standalone "$OUTPUT"
```

Set `BUILD_PYTHON` to the new environment executable (`bin/python` on macOS;
`Scripts/python.exe` on Windows). Use `macos-x86_64` or `windows-x64` for the
other native targets; cross-builds are refused. The output must be absent
and outside the source checkout, under an existing nonsymlink parent. ZIPs
include an exact `ARTIFACT-MANIFEST.json`, an external matching manifest and a
SHA256 sidecar. Chart-audit metadata uses an explicit list of public aggregate
fields for the overall report and each season, plus the full private report
digest. Per-team audit details and unknown future fields are excluded at both
levels (DEV-091); retain detailed reports separately under ignored evidence paths.
Extracted executables must serve the UI/assets, match the exact reviewed release
catalog (173 teams for 1.1.0), play a snap, round-trip a save and shut down
gracefully.
The local macOS prototype may use the installed interpreter for engineering
validation; it is not a substitute for the workflow-pinned shipped runtime.

The Windows job additionally installs pinned **NSIS 3.11**, compiles
`release/windows/installer.nsi` via `scripts.windows_installer --smoke` and
requires successful silent installation, registry/version inspection, installed
app/game/save smoke, and uninstall preserving an unrelated user file. Compiler
or smoke failures fail the job; installers are not an optional best-effort step.
The installer is per-user (`LocalAppData/Programs/BowlBound`, HKCU), installs
`BowlBound.exe` with Start menu/desktop shortcuts and uses exact generated
uninstall lists, never recursive installation-directory deletion. It requires
an empty destination; uninstall the prior version first. Generated `File`
commands quote the entire `/oname=filename` option, not just its value; this
is required by NSIS for names with spaces. Keep literal-dollar escaping and
exact file selection when changing generated lists.

Successful jobs upload the portable ZIP/checksum/manifest plus the Windows
`BowlBoundSetup-VERSION-windows-x64.exe` and checksum, retained for 14 days.
These are unsigned workflow artifacts, not a public release or platform
support certification. Publication still requires three-platform native
acceptance, bundled native-library license review, fresh-machine testing and
explicit owner approval. Never publish the temporary local prototype builds.

## Native notices and provenance guard (DEV-041)

`release/native-notices/manifest.json` is the offline notice catalog. Entries
reference reviewed upstream URLs, exact SHA256 notice bytes, dependency
versions and Python build recipes. `acquisition.json` preserves direct source
URLs; extracted archive/header provenance is described by the manifest and
milestone notes. Build-time network retrieval or substituting a generic license
for a missing copyright/NOTICE file is not allowed. The Windows LF checkout
policy applies to these pinned texts as well as to the fictional samples.

After materializing the freezer output, `scripts.native_notices` validates
every selected notice before copying it to both `THIRD_PARTY/NATIVE/` and
`_internal/THIRD_PARTY/NATIVE/`. It scans native suffixes and Mach-O/PE/ELF
magic (including extensionless framework/bootloader files), requires reviewed
component families, and writes matching `NATIVE-LIBRARIES.json` reports with
relative paths and binary/notice hashes. OpenSSL, ncurses and pydantic-core
compiler markers must match the reviewed provenance, not just the filenames.
The archive step revalidates notices and the complete native-file inventory
before writing a ZIP. The installer consumes that exact verified inventory,
so it cannot silently drop the notices. Package notice collection also includes
setuptools/vendor and packaging code captured during analysis.

An unknown library, missing/changed text, unreviewed Python version or changed
version/compiler marker requires investigation and catalog/test updates, not
a wildcard exception. Read the native manifest alongside dependency versions
and source recipes whenever upgrading Python, wheels or PyInstaller. Binary
hashes and markers are engineering consistency checks, not legal clearance or
a cryptographic attestation of static dependency provenance.

The catalog tracks the reviewed Python runtime: 2026-11-15 moved from CPython
3.13.17 to 3.12.16 to match Paydirt and the tested local baseline. That update
re-pinned the CPython license text, the bundled OpenSSL notices (now 3.0.16),
the vendored expat header, and the vendored libmpdec 2.5.1 notice, which is now
retained through the CPython license file rather than a separate mpdecimal file.
Native filename guards match `cpython-312`/`python3.12`. When changing the
Python runtime again, re-acquire and review these bytes rather than only editing
version strings.

The Rust collection records a conservative superset from the checksum-verified
pydantic-core 2.50.1 sdist Cargo.lock and the observed compiler commit
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4` library/Cargo.lock. It retains
upstream texts with per-archive provenance and explicitly identifies entries
without license files. Do not interpret this superset as the selected target
graph, or its gaps as silently waived. Complete target-applicability/static
linkage review and Windows runtime redistribution authority remain open in
DEV-041/DEV-037. A verification build may exercise these guards, but must not
be published until the outstanding audit and fresh-machine gates are met.

## Published-download validation (DEV-084)

After publication, dispatch **Validate Published Install Artifacts** with the
existing immutable release tag. The workflow downloads release metadata, ZIPs
and the Windows installer with their checksums; it never rebuilds those assets.
Its four native jobs cover Apple Silicon, Intel Mac, Windows ZIP and Windows
installer. The harness uses the reviewed source manifest from the released tag
to check the complete catalog, independent of the observed API.

Require verified published size/digest and checksum before execution, matching
platform/version, exact API and rendered selectors, sample/generated game
startup, every-team snap/save/load, frontend assets, logs and graceful shutdown.
The Windows installer check also verifies install registration and uninstall.
Use fresh output paths so receipts/logs/screenshots cannot overwrite evidence.
Preserve CI artifacts before their retention period expires.

Automated runs use an isolated port and `--no-browser`. Separately record normal
entry-point automatic-browser behavior on a fresh machine after downloading
through a browser. Signing/notarization, quarantine and SmartScreen acceptance
remain distinct from functional native-runner checks. A failed published asset
is a release defect; repair only through a new unused version/tag.

See [1.0.1 release evidence](release-1.0.1.md) for the source/gate/run references.

## Reviewed chart-generator identity

The generator pins exact reviewed engine source bytes, including
`bowl_bound/__init__.py`. A release version bump therefore needs an explicit
review of `tools/chartgen/research-runtime-contract.json` and its authority pins
in `tools/chartgen/current_runtime.py`. Compare every pinned engine and runtime
file with the immutable reviewed commit; do not automatically accept new hashes
or remove metadata files from verification to make a build pass. Record the
source diff and new contract digest in the release ticket. Preserve earlier
receipts under their original source identity.

Before a long calibration or release regression, run this quick integrity check:

```sh
.venv/bin/python -c "from tools.chartgen.refine import engine_identity; engine_identity()"
```

A version-only update does not establish fresh calibration or authorize reuse of
receipts under another identity. Any actual engine, simulation, source or fitting
change needs the affected validation described in the
[calibration workflow](../chart-calibration.md). GitHub checks the reviewed identity
before starting the expensive regression and still runs the complete suite.
