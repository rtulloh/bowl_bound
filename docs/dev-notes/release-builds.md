# Release preparation and artifact selection

This is maintainer guidance, not player release notes. No command below creates
a GitHub remote, tag or public release. The current target is standalone apps;
the ZIP below is a verified native-builder input, **not** a finished player app.

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
Exactly the two original 2007 sample rosters and their CC0 source notes are
selected with owner approval (DEV-042); every other roster remains excluded.
Unknown file categories, traversal, duplicate entries, missing inputs and
symlinked files/ancestors fail before output creation.

When adding or moving application modules, update the runtime selection for their
imports, including dependencies loaded only when a game is created. Source tests
can find modules that an exact staged runtime lacks; successful freezing alone
does not prove those imports resolve. The release regression imports the staged
web/CLI entry points and creates a default game with only the original fictional
samples while blocking checkout/editable application fallbacks. Keep the frozen
executable smoke required as well: it exercises packaging and third-party dynamic
imports that a source-level probe cannot certify.

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

## Manual native workflow and Windows installer

`.github/workflows/tests.yml` is named **Tests** and runs automatically on
branch pushes (including main and isolated workstreams) and pull requests. Its
run is associated with the pushed/PR commit. The Ubuntu gate runs coverage,
lint/format, pip check, frontend unit/build/audit and real-engine Chromium tests.
It neither builds native executables nor publishes releases.

`.github/workflows/build.yml` is manually dispatched from GitHub Actions →
**Build and Release Standalone Executables** → **Run workflow** after the
workflow is approved and pushed. The name describes the release-build purpose;
its existing controls remain artifact-only. It creates no tags or GitHub
releases and has no automatic tag/build/publication trigger. `contents: read`,
exact action SHAs and disabled checkout credentials remain required.

The manual workflow calls the same **Tests** gate before native builds. Optional
`source_ref` must be a full 40-character lowercase commit SHA for an approved main
snapshot; a floating branch/tag is rejected before checkout. Leaving it blank
uses the dispatch commit SHA. Both test and native jobs check out that same
immutable source. For example, after review and workflow publication:

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

The workflow uses Python **3.13.17** and Node **24.22.1**. Each native job
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
SHA256 sidecar. Extracted executables must serve the UI/assets, list only the
two fictional teams, play a snap, round-trip a save and shut down gracefully.
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

The Rust collection records a conservative superset from the checksum-verified
pydantic-core 2.50.1 sdist Cargo.lock and the observed compiler commit
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4` library/Cargo.lock. It retains
upstream texts with per-archive provenance and explicitly identifies entries
without license files. Do not interpret this superset as the selected target
graph, or its gaps as silently waived. Complete target-applicability/static
linkage review and Windows runtime redistribution authority remain open in
DEV-041/DEV-037. A verification build may exercise these guards, but must not
be published until the outstanding audit and fresh-machine gates are met.
