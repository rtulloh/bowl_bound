# Bowl Bound 1.1.2 release notes

Release notes for the immutable `v1.1.2` tag. An earlier packaging candidate
failed as tracked in [#347](https://github.com/rtulloh/bowl_bound/issues/347);
the published tag shows only bytes that passed the final gates.

## What's new

- The release adds eight generated 1972 Big Eight teams with commentary
  rosters, for 179 generated teams across 1972, 2002 and 2007 plus the two
  original fictional samples, for 181 playable teams. It
  also incorporates recalibrated 2002 and 2007 charts.
  The 1972 charts passed the matched playtest comparison against their
  predecessor across all eight teams. Historical fit remains incomplete.
  [1972 charts and sources](../generated-charts-1972.md)
- The hosted browser edition becomes the recommended way to play. It runs the
  Python engine in a browser worker, supports saving, resuming and transferring
  games by file, and includes the full release catalog when staged with
  `--include-release-teams`. The season playtest is published at
  https://rtulloh.github.io/bowl_bound/season-playtest/. The native build
  workflow does not produce a static-site artifact.
  [Browser build and save instructions](../web-game.md)
- The macOS installer can launch the app directly. The packaged app uses a
  native entry point and a completed ad-hoc bundle seal. First launch from a
  fresh browser download is tracked separately from automated validation.
  [macOS repair history](release-1.1.1-macos-repair.md)

## Build and validation status

- The full upstream regression, including the real-engine browser job, passed
  for `3a00fc1531059b3ddec1272b95264a56011311e9`.
  [Upstream regression](https://github.com/rtulloh/bowl_bound/actions/runs/44984997318)
- Vite built the native app's frontend on Intel macOS, Apple Silicon macOS,
  and Windows. Packaging stopped on all three targets when the asset validator
  rejected the generated engine worker filename.
  [Release build](https://github.com/rtulloh/bowl_bound/actions/runs/44987079254)
- The packaging fix isolates the browser worker from the native build. Release
  qualification requires a fresh source regression and native build.
  [Packaging issue](https://github.com/rtulloh/bowl_bound/issues/347)
- Published-download smoke tests and first-launch checks remain pending.
  [Release validation requirements](release-builds.md)

For release documentation, Paydirt's
`docs/dev-notes/release-1.12.2-readiness.md` provided the pattern of tying
validation to a source commit and recording first-launch status separately.
Bowl Bound uses its own browser catalog, deployment instructions, and native
validation results. For the packaging fix, Paydirt’s
`scripts/audit_browser_spike_runtime.mjs` also demonstrated a dedicated browser
output directory. Bowl Bound keeps the existing native asset validation and
limits worker compilation to browser mode.
