---
id: DATA-067
title: Acquire season-correct commentary rosters for the release teams
status: open
priority: Medium
milestone: 34a
created-at: 2026-11-16
resolved-at: null
closed-at: null
tags: [rosters, release-blocker]
links: []
commits: []
---

## Description

Owner requests historical roster files for release commentary and position-aware
source attribution, initially the selected 55-team 2002 generated cohort. On
2026-11-16 the owner explicitly authorized release inclusion of these rosters;
the earlier private-only roster guidance is superseded for the reviewed release
cohort. This does not authorize unrelated local roster or PDF publication.

## Resolution / verification

Acquire names and explicit positions from identified season-specific sources,
retain source hashes and per-team provenance, validate with the ordinary roster
loader, and include qualified files through an exact release allowlist. Report
missing teams/roles; do not infer verified starters from statistics. Check the
existing 2007 release catalog for roster coverage too. Source narratives, photos,
logos and detailed acquisition evidence remain outside release bundles.

## Comments

--- 2026-11-16 — reviewed extraction from Oregon State bowl summaries ---

Oregon State's official bowl-summary PDF supplies explicit named positions for
56 players in its 2002 Insight Bowl roster and 89 in its 2007 bowl roster.
These are bowl rosters, not a claim of complete season participation. Ordinary
roster loading succeeds. Main staged coverage is now **21/55 for 2002** and
**66/116 for 2007**, before the subagent's eight-team acquisition. The remaining
source gaps are 34 and 50 respectively; role/source review remains separate.

Combined private candidate inventory SHA-256 values:

- 2002: `7276e573a56153784d7f1fe0e8846f6b5e9b0d3825c19508d584673e234eeae9`.
- 2007: `ac99c745583fa0b7e567e1b7af0ff11d42f35680de2478d2207f3a4c17e5f648`.

No historical roster has been added to the public release manifest yet.

--- 2026-11-16 — complete first pass over the 2007 catalog ---

Checked official HTML sources for all 116 published 2007 teams in two batches.
Acquired 65 candidates and recorded 51 gaps; all 65 load through the ordinary
loader. A combined private inventory pins 130 roster/provenance files, restricted
to exact existing release team slugs. Inventory SHA-256:
`2b9124066c6485164387e15078e597f9ec3e207a26dc26bd730ab1f51ada39d3`.
This is acquisition coverage, not completed role/source review or release pins.
An additional Northern Illinois 2002 roster is available only for the fumble
attribution investigation; it does not expand the selected release cohort.

--- 2026-11-16 — additional official sources ---

Michigan State's official digitally encoded 2002 roster PDF adds 101 names with
explicit positions; Baylor's official archived roster table adds 132. These
separate curated candidates bring the main acquisition to 20 of 55 teams, before
the subagent's eight-team work. Raw files and per-team receipts remain ignored.
Native Vision OCR fails on this host even outside the sandbox; temporary Python
CPU OCR successfully extracts the scanned Alabama source, but its names and
positions still require review before qualification. No OCR dependency is added
to the application or project environment. Washington's official multi-season
roster PDF identifies its 2002 and 2007 pages; reviewed extraction is underway.
Official HTML checks for the corresponding 2007 release teams are also underway.

--- 2026-11-16 — public acquirer and first staged cohort ---

Added the Python 3.12 development command `scripts.acquire_rosters`, using only
the standard library and ordinary roster validation. Synthetic tests first
demonstrated unsupported historical position labels and missing cached-response
reparsing; the implementation now supports explicit aliases and offline reparse.
Footnote asterisks are removed and surname-first lists are converted to display
names, preserving suffixes. Ambiguous specialist labels remain reported.

The retained official HTML sources produce 18 candidates out of 55 selected
teams, with 37 acquisition gaps. All 18 load through `load_roster`; a private
inventory pins their 36 roster/provenance files. It is a candidate inventory,
not the public release allowlist. Cached-response reparse preserves the earlier
receipts and avoids repeating acquisition after a parser correction.

Receipt `private-data/rosters-2002-v3/acquisition.json` SHA-256:
`ca9669aaf3e08dbeecbd961af122adc4fd1989000bb932cf5b3286b37849ec8e`.
Candidate inventory SHA-256:
`29bdb462863c704b78a4e60c1e901d851ca42c1d6c02ec118f761d1686f6470b`.
Several official archive URLs serve empty/current rosters. A search result for
a Rutgers 2002 roster actually downloads a baseball guide; visual review rejects
it. Alabama's official football roster is scanned and needs separately reviewed
extraction. No source biographies, images or raw pages are release candidates.

--- 2026-11-16 — initial source checks ---

ESPN 2002/2007 roster endpoints for Virginia Tech return no player entries. An
apparent official 2002 roster URL serves a 2026 roster; a year in the URL alone
is insufficient. The current SportsDataverse 2007 roster release has 8,738 rows
across 186 teams, but every position is unknown, so it cannot independently
populate positional commentary lists. Official Michigan, Boston College and
Miami 2002 roster pages are accessible. Raw responses remain ignored.

Consulted local Paydirt positional-list roster conventions and Bowl Bound's
existing loader/roster guidance. Reuse names/position lists, provenance and
ordinary loader validation; do not import NFL rosters or add a runtime dependency.

--- 2026-11-16 — eight-team acquisition incorporated into candidate inventory ---

The eight-team acquisition adds Iowa, Kansas, LSU, Notre Dame, Ohio State,
Penn State, Stanford and Virginia Tech. Together with the earlier official HTML
and curated sources, the selected 2002 cohort now has **29/55 roster candidates**
and **26 acquisition gaps**. All 29 pass the ordinary `load_roster` path. Exact
pins cover each candidate's roster and source document in the ignored inventory
`private-data/data066-rosters/rosters-2002-candidate-inventory-v3.json`:
`20b8382be0222f33668636c6b127c11de46471020fb008a2c57811f0b9b55106`.

The 2007 candidate count remains **66/116**, with 50 acquisition gaps. Candidate
loading verifies format; source/role review and exact release-manifest inclusion
remain outstanding. No historical roster has been added to a public artifact.

--- 2026-11-16 — reviewed roster recovery continues toward release ---

The new private curation adds Arizona State, Indiana, Purdue, Washington,
Wisconsin, Temple, Alabama, Texas Tech, Ole Miss and Georgia for 2002. Coverage
is now **39/55 candidates**, with **16 acquisition gaps**. Washington also brings
2007 coverage to **67/116**, with 49 gaps. All added candidates pass the ordinary
roster loader; no starter metadata or returner roles were inferred.

Coverage remains explicit: Arizona State is a spring roster; Indiana/Purdue are
22-player positional gamebook lineups; Wisconsin/Alabama are reviewed partial
scan transcriptions; Georgia is a preseason depth chart. Ole Miss currently uses
a contemporary third-party roster mirror and needs official corroboration.
Unreadable names and ambiguous specialist/rover positions remain excluded or
unmapped. The temporary OCR dependency stays outside the project environment.

Fresh ignored candidate inventories preserve prior versions:

- 2002 v4: `8dddeac992a3200e10f4951ea7fb8241c62608bf90b4d8aeea88e25525fcf43d`.
- 2007 v3: `c6cbaa3433a7b4a144f48181745f151722e6c483d689d846076e928c882f4421`.

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md` and its season roster
guidance for this phase: adapt season-correct narration, explicit position
mapping, private historical audits and actual packaged commentary checks.
Deliberately do not reuse Paydirt's whole-season-directory packaging; Bowl Bound
still requires an exact reviewed file allowlist. Source/role qualification and
release-manifest integration remain open.

--- 2026-11-16 — all selected 2002 teams have season-specific roster candidates ---

The private inventory now covers **55/55 selected 2002 teams**, with no missing
team. All candidates pass the ordinary roster loader. Inventory v5 SHA-256:
`d013d2de3bee3f3e87b1e2c30d5552d38007847e66af8336cbddeeee28065574`.
Its exact 110 roster/provenance pins retain each candidate's source root; this is
not permission to copy any complete local seasons directory.

Coverage includes full, spring and bowl rosters, depth charts, and explicitly
partial positional gamebook lineups. Missing specialist positions keep generic
commentary. No returner role or verified starter metadata was inferred. The
Rutgers lineup was checked against the actual 2002 Tennessee gamebook image;
the similarly named baseball guide remains rejected. An Oklahoma archive page
mixing seasons was also rejected in favor of its dated 2002 Baylor gamebook.
Contemporary third-party mirrors for Ole Miss, Oklahoma State and Kansas State
are identified in their retained receipts and still need final source review.

The existing 2007 cohort remains **67/116 candidates**, with 49 acquisition gaps;
this does not establish roster completeness for that entire season. Final
source/role review, packaged commentary checks and exact release inclusion are
still outstanding. Raw source pages, images and detailed evidence remain private.

--- 2026-11-16 — all 55 roster candidates verified in assembled runtime ---

The combined unpublished package includes the exact 110 reviewed 2002 roster
and source-note candidates. Normal API and terminal paths import that assembled
runtime and exercise every new team. Names appear in engine-owned commentary;
generic fallback remains for missing positions. Named/generic outcomes and
semantic reports match, roster loading and repeated rendering preserve dice/RNG
and save digests, and API/CLI reload reproduces narration. These are ordinary
application-path checks, not monkeypatched research-runner results.

Private receipt:
`private-data/data066-packaged-roster-check-v1/receipt.json`.
Partial/spring/bowl/depth/dated-lineup limitations and the outstanding mirror
source reviews remain as recorded above. The 2007 inventory still has 49 gaps;
this check does not manufacture full rosters or clear unrelated files for release.

--- 2026-11-16 — official corroboration and bounded Ole Miss selection ---

All 99 Oklahoma State candidate names/positions match the official 2002
alphabetical archive. Kansas State's official numerical archive matches all 48
selected names; the later November depth chart controls an in-season DB role
and the explicitly printed returner roles, with preseason disagreement disclosed.
Neither team's roster JSON changes.

Ole Miss now has a bounded, school-produced bowl-depth selection with 54 distinct
names and explicit returner memberships, plus two dated school notes supporting
additional role/spelling evidence. The earlier mirror-only 137-name selection
is preserved privately. Conflicting source spelling and a dubious TE row remain
disclosed rather than creating another player/role. This is a partial commentary
roster, not a complete availability list.

All 55 selected teams remain covered in inventory v6, SHA-256
`84d52ce2ee5b5bca43250f30762e5075b52005b6ddae8be165ad6778a6ad6434`.
The fresh exact package and all 55 normal packaged API/CLI commentary, save/load
and RNG-equivalence checks pass. Receipt:
`private-data/data066-packaged-roster-check-v2/receipt.json`.
Historical publication, maintained-tree integration and browser/full regression
qualification remain separately gated; this ticket stays open.


--- 2026-11-16 — native archive roster guard regression ---

The native archive still rejected separately selected historical rosters after
successful staging. Three synthetic controls reproduced the rejection on all
supported targets. The isolated fix uses the exact verified assembled resource
inventory and preserves changed/unselected-file rejection. Four added controls
also reproduce and fix unselected roster source notes outside that inventory.
All 255 combined
packaging, chart-audit and native integration checks pass, including extraction
and Windows installer lists. This is not an actual native build or platform
play-test; main-tree integration and browser validation remain pending. See the
[native archive regression notes](../../data066-generator-recovery.md#native-roster-archive-regression-2026-11-16).


--- 2026-11-16 — all 55 rosters pass actual packaged browser paths ---

The exact combined candidate now passes real engine roster narration and UI
save/download/load for every new team, with both selected canonical IDs asserted.
API and rendered catalog agree on 173 entries; no browser errors occur and server
shutdown is normal. Receipt:
`private-data/data066-browser-container-work-v1/candidate-browser-review-v3/receipt.json`.
The separate unchanged 72-test browser suite also passes locally in Linux.
Native build/platform launch certification, maintained packaging integration and
final Python coverage remain separate; roster inclusion authorization already
recorded on this ticket is unchanged.
