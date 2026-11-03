# Alpha 4 release record

## Scope and authorization

The owner requested starting the release on 2026-11-02 after standalone build
[41558282571](https://github.com/rtulloh/bowl_bound/actions/runs/41558282571)
passed on source commit `03d1992d3a3811cf89879bce985e23937e3a3dc0`.
Prepare a separate `release/alpha4` branch from that commit. Ongoing milestone 33
and college chart-generator work is excluded. Existing alpha 3 is immutable;
new binaries must identify as alpha 4 before release.

The owner explicitly directed skipping local tests solely to start this build.
The hosted workflow retains its full source/browser gate before native builds.
Changes here are version metadata, corresponding identity expectations, and
release documentation; no gameplay behavior or save profile changes.
Synthetic packaging fixtures intentionally retain their independent alpha 3
identity. Current application/API/launcher expectations advance to alpha 4.

## Paydirt consultation

Reviewed local Paydirt `.github/workflows/release.yml` before this release phase.
Adapt consistent version/tag identity and attaching verified native artifacts.
Do not reuse its automatic publication, unpinned dependencies, optional installer
failures, Linux target, runtime code, or team data. Bowl Bound retains its exact
public sample allowlist, pinned toolchain, required installer smoke, and separate
artifact review.

## Build and publication

Bowl Bound has only the manual `.github/workflows/build.yml` workflow; it builds
and uploads inspected artifacts but does not publish a GitHub release. Dispatch
it on this matching-version release commit. Verify all three native targets and
checksums before attaching artifacts to a release. DEV-037/DEV-041 still record
outstanding fresh-machine/native-license acceptance; a green build does not
silently close those tickets. This request starts the release build without
claiming final publication acceptance.
