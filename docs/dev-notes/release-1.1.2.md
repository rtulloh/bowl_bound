# Bowl Bound 1.1.2 release notes

Release record for the immutable `v1.1.2` tag. The earlier packaging candidate
failed as tracked in [#347](https://github.com/rtulloh/bowl_bound/issues/347);
the published tag shows only bytes that passed the final gates.

## What's new

- The release adds eight generated 1972 Big Eight teams with commentary
  rosters, for 179 generated teams across 1972, 2002 and 2007 plus the two
  original fictional samples, for 181 playable teams. It also incorporates
  recalibrated 2002 and 2007 charts, so generated saves have new chart
  identities.
  The 1972 charts passed the matched playtest comparison against their
  predecessor across all eight teams. Historical fit remains incomplete.
  [1972 charts and sources](../generated-charts-1972.md)
- The hosted browser edition becomes the recommended way to play. It runs the
  Python engine in a browser worker, supports saving, resuming and transferring
  individual games by file, and includes the full release catalog when staged
  with `--include-release-teams`. It adds season play: historical schedules or
  custom conference leagues, fixture resume, standings, rankings and team
  statistics. Campaigns and saves stay in the current browser profile and site
  origin. The season playtest is published at
  https://rtulloh.github.io/bowl_bound/season-playtest/. The native build
  workflow does not produce a static-site artifact.
  [Browser build and save instructions](../web-game.md)
- The macOS installer can launch the app directly. The packaged app uses a
  native entry point and a completed ad-hoc bundle seal. First launch from a
  fresh browser download is tracked separately from automated validation.
  [macOS repair history](release-1.1.1-macos-repair.md)

## Publication and validation status

- The immutable tag `v1.1.2` resolves to
  `e612ffdab405f80b70d271792b2935bf27586e7e`. Tests run
  [46110473484](https://github.com/rtulloh/bowl_bound/actions/runs/46110473484)
  passed all 12 Python shards, combined coverage, the real-engine browser job,
  the Windows source dialog and formatting/lint/dependency checks on that exact
  main-push commit. Dependency audit `46110473591` passed separately.
- Native build run
  [46112425675](https://github.com/rtulloh/bowl_bound/actions/runs/46112425675)
  passed the exact-SHA source verifier and all three targets. Downloaded
  artifact checksums, version/target manifests, the 181-team catalog
  (8 1972, 55 2002, 118 2007) and both DMG receipts matched; each receipt
  records mounted-payload and Finder-launch smoke as true.
- The release is published as regular Latest with 15 explicit assets. Published
  smoke run
  [46155228650](https://github.com/rtulloh/bowl_bound/actions/runs/46155228650)
  passed all six jobs: both Mac DMGs, both Mac ZIPs, Windows portable and the
  Windows installer, with no skipped targets. Each checked its published
  digest, exact API/rendered catalog, real-engine game/save behavior and clean
  shutdown.
- Pages `gh-pages` commit `ef2f4cf3faefc64a75eac81da48da9a58f7e2ab2` deploys
  the browser game and season playtest built from the tag. Both live manifests
  report the same 181-team catalog, every Python/Pyodide hash matched locally,
  and the playtest retains the `bowl-bound-118-playtest` library.
- The owner opened the hosted browser edition on a desktop and reported it
  working. This is a useful hosted-site confirmation, not a native fresh-
  download first-launch check.

Fresh browser-downloaded native first launch, default-browser/security prompts
and macOS 26 Intel compatibility remain unverified. The Mac apps are ad-hoc
sealed, unsigned and not notarized; Windows retains SmartScreen and
unknown-publisher limits. DEV-093 stays open for those gaps. The generated
charts remain statistical estimates, and their historical fit remains
incomplete.

For release documentation, Paydirt's
`docs/dev-notes/release-1.12.2-readiness.md` provided the pattern of tying
validation to a source commit and recording first-launch status separately.
Bowl Bound uses its own browser catalog, deployment instructions, and native
validation results. For the packaging fix, Paydirt’s
`scripts/audit_browser_spike_runtime.mjs` also demonstrated a dedicated browser
output directory. Bowl Bound keeps the existing native asset validation and
limits worker compilation to browser mode.
