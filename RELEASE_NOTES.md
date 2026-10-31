# Bowl Bound release notes

## 0.1.0-alpha.3 — Third alpha

- Advances quarter and game transitions through normal plays; there is no separate
  clock-runoff action. Use a kneeldown when you want to run down the clock.
- Supports timeout requests with the `T` suffix when the engine offers a timeout.
- Corrects second-half kickoff order and keeps older saved games loadable.
## 0.1.0-alpha.2 — Second alpha

A follow-up prerelease of the Bowl Bound college-football strategy game for
community testing. It includes the verified Windows x64 installer/portable build
and portable macOS Apple Silicon and Intel builds introduced with alpha 1, plus
the latest reviewed documentation and issue inventory.

### Changes since alpha 1

- Publishes the current reviewed source and issue inventory after the milestone 25
  draft/current-alpha code review.
- Records importer safety, launcher, release-manifest, documentation and frontend
  test-hygiene follow-up tickets without changing game rules or save compatibility.
- Updates player-facing version, installation and release guidance for alpha 2.
- Retains the alpha 1 fictional sample rosters and announcer-style engine
  commentary; no private or historical team charts are added.

### Included

- Local browser game with regulation play, season-appropriate overtime,
  penalties, special teams, scoring and team statistics.
- Human-versus-computer play and local two-sided manual control.
- Easy, Medium (default) and Hard coaching; difficulty never changes dice odds.
- Save/resume, including pending decisions, with matching installed team charts.
- Play logs and recorded dice/chart audits, with natural engine-generated
  play-by-play shared by browser and terminal.
- Original fictional Cedar Valley and Harbor Tech sample teams, including
  fictional rosters for illustrative commentary names, not individual-player statistics.
- A separate source-installed terminal game and optional PDF chart extractor.

### Known limitations

- Alpha software: keep save backups and expect issues. There is no automatic save.
- This is a local game, not an authenticated Internet multiplayer service.
- Season profiles cover 1940–2023. Not every optional rule or PDF layout is
  supported. Scanned charts, advanced kick options, alternate/hybrid timing,
  IB/OOB declarations and some end-zone recovery/return-foul branches are
  unavailable. Unsupported controls stay disabled.
- Historical charts, PDFs and rosters are not included. Importing your own teams
  requires the separate Python extractor and permission to use the source material.
- Standalone builds are unsigned. Verify the published SHA256 files before use;
  Windows SmartScreen or macOS Gatekeeper may require the documented local
  approval.
- Linux does not yet have a standalone alpha build; source installation remains
  available.

### Getting started and feedback

See [installation](docs/installation.md), [how to play](docs/playing.md), and
[importing teams](docs/importing-teams.md). Report problems to
**bowlboundsupport@gmail.com**, including the game version, short description,
reproduction steps and relevant reviewed logs if available.
The [bug-report guide](docs/reporting-bugs.md) includes a template and privacy
checklist. Please do not send private charts or source PDFs.
