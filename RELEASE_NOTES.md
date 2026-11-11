# Bowl Bound release notes

## 1.0.1 — Published-install validation

Adds native validation of the actual release downloads on GitHub runners:
checksums and release identity, the complete 118-team catalog, rendered team
selection and game startup, game/save behavior and clean shutdown. The Windows
installer is checked separately from the portable ZIP.

This maintenance release keeps the 1.0.0 charts, football rules, save schema and
default port 8001. Applications remain unsigned; fresh-machine security prompts
are separate from automated functional checks. See the
[installation guide](docs/installation.md).

## 1.0.0 — Passing-chart corrections and simultaneous play

- Corrects interception catch depths across the 116 generated 2007 teams using
  separate models for Screen, Sprint Out, Boot-leg and Drop Back.
- Preserves interception frequencies, other chart outcomes and the original
  fictional sample teams. The visual viewer displays the corrected chart data.
- Moves Bowl Bound's default web address to **http://127.0.0.1:8001**, allowing
  it to run alongside Paydirt on port 8000. Explicit port overrides still work.
- Strengthens automated chart checks and game/save/replay validation.

Generated charts remain statistical estimates for community feedback. When the
source does not identify the designed passing play, catch-depth distributions
are explicitly modeled assumptions. This release does not certify historical
team balance or complete independent causal/clock accounting. See
[generation and testing limits](docs/generated-charts.md).

Football rules and save schema are unchanged. Generated charts have new content
identities: older generated-team saves may require their original chart catalog.
Keep backups and retain the earlier version for those games. Standalone builds
remain unsigned; follow the [installation guide](docs/installation.md).

## 0.1.0-alpha.9 — Revised generated pass defenses

- Reworks generated pass-defense responses with explicit tactical opportunities
  and source-supported interception-depth variation.
- Preserves existing event budgets. Zero-budget mechanisms stay dormant; scarce
  budgets show limited contrasts instead of manufactured outcomes.
- Adds versioned release audits for these budgets, preserved chart facts, actual
  priority outcomes and the exact files loaded by the game and native builds.
- Retains the 116 generated 2007 teams, two fictional samples and visual chart viewer.

This is an experimental community-testing release. Historical formations are
unobserved; tactical roles and short/long depth priors are authored assumptions.
Source completeness and historical calibration remain in progress. Additional
seasons and refinements to rare defensive breakaway placement are follow-up work.
Read [generation and limitations](docs/generated-charts.md).

Football rules and save schema are unchanged. Revised generated charts have new
content/provenance identities, so older saves may require their original catalog.
Keep save backups. Original fictional sample bundles remain unchanged.

## 0.1.0-alpha.8 — Visual charts and generated defensive tradeoffs

- Adds the web chart viewer described below: both matchup teams, offense,
  defense, Special Teams and Priority, with independent tabs/windows.
- Corrects the generated neutral A–F profile with original experimental
  formation/play yardage tradeoffs. These authored tactical assumptions are
  separate from measured team strength, not observed historical formation data.
- Preserves the same 116 generated teams plus two fictional samples, all
  nondefensive charts, printed response allocations and corrected OOB evidence.
- Requires a fresh exact-probability, priority-resolved tactical and preserved-
  baseline audit in CI and staged native builds. Stored green reports cannot
  bypass recomputation.

This remains a community-testing alpha. Current paired diagnostic games average
3.79 pure rushing yards per attempt versus 4.77 in the supplied conditioned
source, sacks 7.19% of dropbacks versus 5.75%, and interceptions 3.97% of attempts
versus 3.22%; primary fumbles are 2.21% of eligible snaps versus 1.48% known
source incidence. These balance gaps mostly predate this correction; sparse two-game
team exposures under AI/schedule mixtures different from the historical season
do not establish historical accuracy. Independent official season totals remain unverified. Read
[generation and limitations](docs/generated-charts.md).

Save schema and football rules are unchanged, but saves require identical chart
bytes. Earlier generated-team saves may require their original chart catalog.
Original fictional sample charts and rosters are unchanged. Alpha 7's immutable
tag and unpublished draft remain preserved; Alpha 8 carries the corrected catalog.

## 0.1.0-alpha.7 — Visual charts

- Adds a Charts button with both matchup teams' actual loaded offense,
  defense and Special Teams charts, readable labels, colors and explicit zeroes.
- Uses Running Plays / Option / Passing Plays bands, large defense formation
  letters, boxed dice totals and a separate supplemental B/QR/QT block.
- Shows all offensive totals 10–39 and all six defensive formation groups
  together on a desktop page; smaller windows and phones support scrolling.
- Adds the shared Priority reference with operation definitions and the
  approved defensive Breakaway extension. Chart reading help starts closed.
- Shows loaded kicks, returns, field goals and GOOD/NG extra points with
  context-specific Special Teams help.
- Opens independent chart views in a new browser tab or separate window, so
  charts can stay on another display while the game continues.
- Chart viewing consumes no dice, selects no play and changes no game/save state.

Retains Alpha 6's exact 118-team catalog and generated-chart attribution.
Football rules, save schema and the `bowl-bound-m33-v1` profile remain unchanged.
Keep save backups and follow the [installation guide](docs/installation.md).
Detached chart links belong to the current running game; reopen from the active
game after restarting the server. Browser settings may control separate windows.

## 0.1.0-alpha.6 — Generated 2007 teams

- Adds 116 generated 2007 college teams, retaining the two original fictional
  samples: 118 playable teams in the web and source-installed terminal games.
- Pins every packaged chart and its generated virtual-cell provenance; native
  acceptance checks the exact catalog and a snap plus save/load for every team.
- Corrects inflated generated out-of-bounds markers and their late-half clock
  effects while preserving all non-OOB chart facts. Missing source mentions remain
  unknown; estimated marker rates reflect lower-bound narrative incidence.
- Fixes computer analysis aborts after a penalty moves a two-point try from the
  original two-yard spot.
- Retains Alpha 5's coaching, halftime/final summaries and playability fixes.

The new charts are statistical estimates from individual SportsDataverse/cfbfastR
ESPN-derived events, with pooled/inferred families where source calls are unknown.
They carry [CC BY 4.0 attribution and modification notices](seasons/GENERATED-LICENSE.md).
See [generation provenance, coverage and limits](docs/generated-charts.md).
No historical player rosters, private imported PDF charts or raw source data are
included. Generated teams use generic player-role commentary.

These charts are released for community feedback; historical calibration remains
in progress. Older retained baseline-coaching season runs do not establish current
Hard-AI accuracy. Recent seasons are separate work. Save schema and
`bowl-bound-m33-v1` profile are unchanged; matching installed chart content remains
required. Keep save backups. QB Sneak ball-carrier commentary remains a known
minor issue. Builds remain unsigned alpha software; follow the
[installation guide](docs/installation.md).

## 0.1.0-alpha.5 — Fifth alpha

- Adds a shared public fourth-down policy and clearer decision guidance for
  human and computer coaches.
- Corrects late-half computer field-goal and punt selection, improves
  Razzle-Dazzle choices, and keeps surprise calls uncommon.
- Resolves fumble outcomes before penalty choices and improves pre-play timeout
  controls without exposing the computer's committed call.
- Adds clearer halftime presentation and two-point commentary, and displays the
  same scoring and team-statistics boxes at the end of a terminal game.
- Clarifies pending interception locations, result choices, save guidance, and
  Hail Mary labels.

Includes only the existing original fictional Cedar Valley and Harbor Tech
sample teams. Generated season charts are separate work and are not included.
The existing save schema is retained; Milestone 33 uses the
`bowl-bound-m33-v1` engine profile. Keep copies of saves before upgrading.

Known follow-up: QB Sneak commentary can name the wrong ball carrier; its
football result is unaffected.
Builds are unsigned alpha software. Back up saves and report reproducible issues.

## 0.1.0-alpha.4 — Fourth alpha

- Adds engine-offered QB Sneak, Razzle-Dazzle (RZDZ), onside kickoffs,
  intentional delay, elected safeties, and in-bounds/out-of-bounds declarations.
- Improves computer coaching for clock management, penalties, play variety, and
  fourth-down decisions, including chart-aware punt and field-goal choices.
- Refines browser and terminal play controls, modifier indicators, and penalty
  prompts; fixes return scoring, penalty enforcement, and older-save compatibility.
- Updates imported team metadata and chart validation for defense markers while
  preserving source tokens. Use the matching source checkout for the optional
  PDF extractor; the standalone game does not import PDFs itself. See the
  [import guide](docs/importing-teams.md). You can find
  [a few free sample Bowl Bound charts at Mays Football](https://maysfootball.com/stuff.htm)
  to import for your personal use, subject to the source's terms.
- Repairs standalone packaging so the required game and coaching modules are
  included on all three platforms.

Advanced II defensive calls remain deferred for eventual user-selectable options.
Historical charts and PDFs are not bundled. Builds remain unsigned alpha software;
keep save backups and follow the [installation guide](docs/installation.md).

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
