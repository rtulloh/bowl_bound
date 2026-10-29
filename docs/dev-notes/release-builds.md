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
transactional stage. Every selected fictional chart/provenance/license file has
a pinned SHA256; changing samples requires deliberate manifest review. No roster
is selected. Unknown file categories, traversal, duplicate entries, missing
inputs and symlinked files/ancestors fail before output creation.

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

`.github/workflows/build.yml` is manually dispatched from GitHub Actions →
**Build standalone apps** → **Run workflow** after the workflow is approved and
pushed. It does not create tags or GitHub releases. `contents: read`, pinned
action SHAs and disabled checkout credentials limit the workflow permissions.
The Ubuntu gate runs coverage, lint/format, frontend unit/build/audit and real
engine Chromium tests. Native builds depend on that gate and run on macOS 26
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
