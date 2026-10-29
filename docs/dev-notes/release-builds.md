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
