---
id: DATA-066
title: Regenerate the 2002 generated cohort with the budget-aware model before release
status: open
priority: High
milestone: 34a
created-at: 2026-11-16
resolved-at: null
closed-at: null
tags:
- chart-generator
- release-blocker
links: [DATA-068]
commits: []
---

## Description

The 52 generated 2002 teams produced by the older college-chartgen-v1 pipeline are not release-quality and cannot be added to 1.1.0 as-is. They were generated from ESPN public core API play-by-play (normalized checksum 5162d0cc87b3..., 81,380 rows, 440 games) and load cleanly, but their defensive charts are sparse and fail the release audit gate. Only generated charts are in scope; the two PDF-imported 2002 teams (Ohio State, Miami FL) stay private and excluded.

## Resolution / verification

- Regenerate the 52-team 2002 cohort with the approved bb-chartgen-budget-alpha-v1 exporter and authored-bb-budget-aware-v1 model so it passes scripts/audit_generated_charts.py. Every team must satisfy the tactical-contrast and numeric-support checks, have no fully blank defensive chart, and carry complete provenance. Then pin the exact files in release/manifest.json, extend release/generated-chart-audit.json, update docs/generated-charts.md and docs/ATTRIBUTION.md, and add the cohort to the 1.1.0 scope. Keep PDF-imported 2002 teams excluded.

## Comments

--- 2026-11-16 — official source resolves a standalone primary rushing gain ---

A retained official gamebook identifies the primary rushing gain in an
owner-reviewed standalone fumble. The one-event adjudication changes only kind,
primary gain and scrimmage phase, retaining provider disagreements on clock,
recoverer and recovery spot. Individual names, play sequences and source-event
values remain in the private pilot rather than this public ticket.

Private pilot: `private-data/data066-official-fumble-pilot/receipt.json`.
Corrected normalized SHA-256:
`12684ce6dce3df2c12cb66dfcf73540778d0e7812f178a2f1a573c73f5ef59dc`.
Ordinary normalized write/read round-trip passes. This is one source-adjudicated
standalone event, not a new automatic link or a completed cohort rerun; the
earlier 260-row automated unresolved count is unchanged until corrections are
incorporated into a fresh combined cohort. A separate standalone example still
lacks an independently verified primary gain.

--- 2026-11-16 — expanded official kickoff source coverage ---

Retained Illinois StatCrew gamebooks now cover 11 of its 12 games, containing
115 explicit gross kickoff records before event matching and deduplication.
The Southern Miss game survives under a named score article even though its
legacy statistics URL returns 404. The remaining Minnesota game currently has
only a box summary. This acquisition does not resolve discrepancies against
ESPN or qualify the full cohort for generation.

Private inventory: `private-data/data066-official-illinois-2002/combined-inventory-v2.json`.
SHA-256: `15ce5a30f55f7c5435a45e9aed7fb0f13fb35e5cd2e3ef361684f0e3a3ab505a`.
The previously verified one-event distance correction remains the only applied
official kickoff adjudication; broad ordinal joins would obscure known conflicts.

--- 2026-11-16 — official individual kickoff evidence pilot ---

An official 2002 StatCrew gamebook provides individual gross kickoff evidence.
A conservative one-event pilot applies only a corroborated missing distance,
binds retained HTML and exact event hashes, round-trips through the normalized
reader, and preserves raw ESPN bytes. Other rows have clock, returner or return-
length disagreements and are not automatically corrected. Individual sequence
and yardage evidence stays in the private pilot. No full-cohort claim is made.

Pilot: `private-data/data066-official-pbp-pilot/receipt.json`.
Normalized pilot SHA-256:
`1f8bc0b963e2d98e778c491d8e32886deea29c0a2e877ab717ff220769cdddfb`.
The existing 17 adjudication tests pass. University StatCrew archives provide a
concrete independent source path for the gross-distance blocker; broader
acquisition and conflict reconciliation remain required.

--- 2026-11-16 — same-clock primary continuation across drives ---

The owner-reviewed sack example is now handled by a shared primary linker and
production normalizer. A unique terminal rush/completion/sack and next drive's
first recovery must agree on named carrier/team, clock/period and exact
end/start owner, yard line, down and distance; primary yardage must be known.
No recovery advance supplies primary gain. Synthetic positive controls failed
before implementation; conflict controls, source lineage and idempotence pass.

This resolves another 33 rows: 19 rushes, 10 sacks and four completions. Latest
accounting: 1,028 strict primary links + 31 modeled clock links + 246 return links
+ **260 unresolved** = 1,565. Remaining first-failed reasons: 65 missing
predecessor, 75 clock disagreement, 69 non-primary predecessor and 51 unmatched
carrier. Both generation variants still stop at missing gross kickoff distances.
Standalone rushing fumbles with unknown primary gain stay unknown rather than
borrowing a different carrier's preceding gain.

Version-4 core receipts bind both primary and return policies; earlier core
versions remain readable. No engine or authored allocator parameter changed.
Experiment SHA-256: `ec1accc6052480fdb7ac9d4e234bf0e32d0bb24d062955aa2a5a4186fe44bb1a`.
Audit SHA-256: `e95beaac080b0ebba0de04cf4ce382439fae5f2a27f269ed7e949b151e88e2a5`.
Focused cumulative validation passes 145 checks, plus 13 selected generation
checks (80 explicitly deselected). Full release qualification remains pending.

--- 2026-11-16 — interception-return fumbles integrated ---

Owner classified a named interceptor's subsequent fumble as a return fumble.
Extended the shared source linker and production normalizer, using the same
adjacent-drive, unique-terminal-play, name/team, period, position and bounded
clock checks. Version-3 core receipts identify the expanded policy; old version-1
and version-2 snapshots remain readable. Synthetic controls preserve the original
interception, assign the fumble to the returning opponent, omit duplicate fitting
records and round-trip source lineage. Experiment reporting distinguishes the
20 interception-return links from the unchanged 226 special-teams links.

The new experiment has 995 strict primary links, 31 modeled primary clock links,
246 return links and **293 unresolved** recoveries (98 missing predecessor,
75 clock disagreement, 69 non-primary predecessor, 51 carrier unmatched).
Both generation variants still fail on absent gross kickoff yardage before a
team completes. Receipt `private-data/data066-fumble-experiment-v3/experiment.json`
SHA-256: `00267b24e9d864358a8617d2a7b82dad70a16670adb6d1bc17ff25019d78de1c`.
The reviewed runtime inventory changes only the `source.py` reader pin for this
step; engine files and authored chart-allocation parameters are unchanged.
Roster acquisition proceeds under DATA-067. No release chart pins changed.

--- 2026-11-16 — cross-drive return attribution in generator ---

Owner identified punt/kickoff return sequences among the missing-predecessor
cases and requested production integration. Shared source-linking logic now
feeds the core normalizer and diagnostic. It resolves 226 of the 344 rows:
131 punt-return and 95 kickoff-return fumbles, counted once with retained source
lineage and excluded from primary rush/receiving fumbles. With the earlier clock
fallback, total unresolved falls from 539 to 313 (118 missing predecessor,
75 clock disagreement, 69 non-primary predecessor, 51 carrier unmatched).
No missing distances or negative observations are invented. The production
generator rejects positive-only return-fumble rate support alongside unknowns.
Fresh candidate attempts still stop at missing gross kickoff yardage; no team
completes. See the [correction evidence](../../data066-generator-recovery.md#cross-drive-special-teams-fumble-correction).
Independent review caught and verified a correction to team totals: the returner
receives the fumble/lost count while the kick remains owned by the kicking team.
Final focused checks pass (90 checks, plus 13 selected generation checks);
the interrupted full gate is not a pass.
DATA-066 remains open; released charts and pins remain unchanged.

--- 2026-11-16 — fallback experiment evaluated ---

Evaluated strict links and an opt-in same-carrier clock-disagreement fallback on
the retained 506-game snapshot. The fallback adds 31 links (1,026 total), leaving
539 of 1,565 recovery rows unresolved. Eighteen selected teams gain 23 links.
Both fitting views explicitly use modeled narrative-incidence negatives;
source flags and raw records remain unchanged. Both get past the primary-fumble
guard and fail before completing the first team with
`no known kickoff yardage evidence; supply individual-play source evidence`.
No recovery advance, return distance or zero is substituted for a primary gain
or gross kick. The official gamebook conflict is retained. Ten new synthetic
controls pass; cumulative release validation remains pending. See the
[experiment results](../../data066-generator-recovery.md#historical-fallback-experiment-results)
for counts, assumptions, reproducible command and receipt hash. This is progress
on attribution, not release qualification; DATA-066 stays open.

--- 2026-11-16 — Paydirt attribution fallback ---

Owner identified Paydirt's historical fallback. Reviewed its role/gain class
proxy, fitting-only omission policy, synthetic tests and completion-boundary
notes. It provides a practical modeled-candidate approach: preserve observed
facts, disclose inferred classes separately and retain omitted events with full
counts and per-team impacts. CFBD access is optional corroboration for this
evaluation, not a prerequisite. The 2002 unresolved share is much larger than
Paydirt's documented fitting omissions, so quantify the effect rather than
inheriting its acceptance. See the
[fallback comparison](../../data066-generator-recovery.md#paydirt-historical-attribution-fallback).
No production inference threshold, fumble denominator or release pin changed.

--- 2026-11-16 — upstream flag construction and official control ---

Traced pinned cfbfastR R and SportsDataverse Python source. Their fumble flags are
derived from row-local narrative text; explicit processed false is not independent
evidence of a non-fumble play. All 55,985 fresh 2002 Rush/Pass Completion/Sack rows
lack inline fumble mentions, so directly copying that rule would miss the separate
recoveries. Added a public, tested diagnostic that reproduces 995 candidate links
and retains the unresolved cases without changing flags or generator rates.

An independent official gamebook control disagrees with the provider on fumble
counts and a matched primary gain. Individual event values remain private.
Source reconciliation is therefore required alongside joining. Current upstream
2007 bulk was inspected as comparison evidence; its hash differs from the frozen
published input and it does not replace that input. CFBD (key/configuration
location requested) and official archives are the next 2002 source checks;
cfbstats' 2005 start cannot fill 2002. Full evidence, hashes and scope are in the
[investigation](../../data066-generator-recovery.md#upstream-fumble-flag-investigation).
No production fumble interpretation, model parameter or release chart pin changed.

--- 2026-11-16 — ESPN companion evidence ---

Owner recalled ESPN enrichment and pointed back to the source research notes.
Revisited `college-play-by-play-sources-2026-11-02.md`: cfbfastR's ESPN path shares
the current upstream provider; its proposed separate NCAA narrative feed is
documented from 2013, not 2002. Companion endpoint probes and a conservative
drive/sequence/clock/possession/carrier diagnostic identify 995 candidate links
between primary plays and separately recorded fumbles in the fresh snapshot.
This is a normalization lead, not evidence for treating other missing flags as
false or fitting a positive-only denominator. See the
[recovery investigation](../../data066-generator-recovery.md#espn-enrichment-follow-up)
for counts, retained receipt and remaining accounting requirements. No model
prior, production fumble interpretation or release chart pin changed.

--- 2026-11-16 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-16 — measured blocker evidence ---

The 52 generated 2002 bundles were produced by the older `college-chartgen-v1`
pipeline (generation manifests record `tool_version: college-chartgen-v1`,
`tactical_evidence: inferred-neutral`, and `family_evidence` observed counts of
zero for every play family). They load through the strict codec and the catalog
reports no problems, but they are not release-quality:

- **Tactical contrast: 0 of 52 teams pass.** The release audit requires strict
  directional run contrast across formations for gains 4, 10 and 18. Every 2002
  team returns identical primary values across the ordered formations (for
  example `[144, 144, 144]`), so `scripts/audit_generated_charts.py` would reject
  the whole cohort.
- **Blank defensive charts.** `california` and `oklahoma-state` are 100% neutral
  (`no_change`) across all 270 defensive cells, so every formation resolves
  identically. Twelve teams have under 10% non-neutral defensive cells; the
  cohort median is 44% versus 2007's 70–100% range.
- **Sparse defensive fill.** 32 of 52 teams fill under half of their defensive
  cells; the cohort minimum is 0.00 and median 0.44, against 2007's 0.70–1.00.
- **Model mismatch.** The release gate pins `authored-bb-budget-aware-v1`
  (`a46aaf83…`) and exporter `bb-chartgen-budget-alpha-v1`. The 2002 metadata
  records `source_filename: generated-model-v1.json`, which is not the approved
  model identity.

Offense and special-teams fill are comparable to 2007 (offense median 0.97,
special 0.86), so the defect is concentrated in the defensive generation.

The budget-aware exporter is not present in this checkout or its branches; only
the older `college-chartgen-v1` generator exists on
`origin/research/college-pbp-cohort`. Regeneration therefore needs the approved
exporter from the machine that produced the 2007 cohort.

Local-only verification: the 52 bundles were copied into the gitignored
`seasons/2002/` with their provenance CSVs for UI testing. Nothing was committed;
the two PDF-imported 2002 teams remain private and excluded.

--- 2026-11-16 — regeneration preflight ---

Owner requested a fresh 2002 regeneration to distinguish stale prototype output from a current-pipeline failure. Preflight at `e218fd9` found no `private-data/`, `.ai-audits/`, or `seasons/2002/` in this checkout, and only one registered Bowl Bound worktree. Available research refs retain `college-chartgen-v1`; no approved budget-aware producer was found in the available tracked generator history. The earlier local-only copies described above are therefore not available in this environment. No generation has run and no new chart-quality result is claimed. The approved producer/configuration and frozen 2002 source snapshot must be located before reproducing the released pipeline; requested their location from the owner. Existing charts and release pins remain untouched.

Paydirt consultation: reviewed `docs/chart-calibration.md`, bounded calibration cycle (steps 1, 2 and 6). Adapt immutable source/configuration identities, preserved prior candidates and whole-cohort comparison; do not reuse NFL policies, private charts or Paydirt-specific qualification thresholds. The rerun should write a separate ignored candidate and retain source/generator hashes, strict-load results, tactical contrast, numeric support and provenance diagnostics before release integration.

--- 2026-11-16 — recovered public producer and fresh source rerun ---

Recovered the matching budget-aware producer and fictional tests from the
November 12 backup, verifying archive and per-file checksums. Integration lives
in public `tools/chartgen/` and `tests/chartgen/`, with the owner's explicit
direction to publish code. See [recovery notes](../../data066-generator-recovery.md)
and [public workflow](../../../chart-generation.md). Python 3.12 is used.
The existing local-season runner and original 2007 model contract are preserved;
the explicit 2002/2007 execution extension has a distinct model identity.

Reacquired ESPN core-v2 regular/postseason inventories locally: 913 listed games
checked, 506 with play records, 99,968 normalized events. Fresh schedule checks
identify 55 teams with at least ten observed games and no listed omissions;
this does not establish identity with the unavailable old 52-team snapshot.
Normalized file SHA-256:
`9c0edcf3f148d9edeb65da4b147a42ce98bb4e0904dc91143cd527ba389fe8f7`.
Acquisition receipt SHA-256:
`c2cd98e7017c7d8ef9e8c7324854312b9a170453c4e6e23dfddb3999df045a1f`.
Raw responses, normalization evidence and failed candidates remain ignored.

The first attempt correctly refused missing interception locations. After a
conservative core adapter recovered 529 of 1,088 interception spots using
corroborating next-snap evidence, the second attempt reached the primary-fumble
support guard and failed with `all positive rush primary fumble support is
unknown`. Here "positive" means positive observation weight, not an assertion
that every rush fumbled. All 37,244 rush, 17,084 completion and 1,657 sack rows
lack primary-fumble flags; separately labeled recovery rows do not establish
their missing primary mechanism. Unknown observations were not changed to false
and no zero-location proxy was introduced. The legacy public 2002 Parquet file
contains only 193 rows from one game, so it does not replace the cohort source.

The synthetic candidate pipeline passes ordinary-codec, budget/contrast,
conditional-depth and deterministic-pin checks. The released 2007 audit still
passes all 116 teams. **DATA-066 remains open:** a better-qualified source or an
explicitly reviewed modeling extension is needed before generation and release
qualification can complete. No 2002 files have been added to release pins.

--- 2026-11-16 — exact official kickoff pilot clears first kicking guard ---

A bounded pilot reconciles all 139 explicit kickoff rows in Virginia Tech's 14
retained official gamebooks. Exact game-date, period, clock, receiver team/name,
return-distance and end-spot checks identify 29 new missing gross distances.
The other 110 records remain unapplied: 56 exact-match failures, 40 without an
explicit named return and 14 involving penalties, onside kicks or no-play text.
Fresh raw normalization and the existing public adjudicator preserve the earlier
Illinois/Danny Smith corrections and round-trip 99,968 events across 506 games.

Both strict and modeled-clock Virginia Tech generation attempts now clear the
kickoff guard and fail with `no known punt yardage evidence; supply individual-play
source evidence`. No team completes. The experiment retains its unchanged
1,028 strict primary links, 31 additional modeled clock links and 246 return
links; automated unresolved accounting remains 260 with that clock fallback.
The individually corrected standalone fumble does not change that linking count.

Normalized SHA-256:
`5eacba86e472f65d23e83c878fad6e75ae688ef4869a59506677922c9bbb3305`.
Experiment `private-data/data066-kickoff-pilot/generation-vt/experiment.json`:
`c985ede4359b27a556759575cdbf1337b4814e31c1750b42e2f85d11a3e0380e`.
The 30 known gross kickoffs are concentrated in selected named returns and do
not qualify a league distribution. A limited punt-evidence follow-up is recorded
in the [shutdown checkpoint](../../data066-generator-recovery.md#bounded-official-kickoff-reconciliation-before-shutdown-2026-11-16).
No model parameter, engine rule, release chart pin or publication scope changed.

--- 2026-11-16 — punt pilot identifies blocked-punt and return-denominator gaps ---

One independently matched explicit 47-yard punt is now included in a separate
fresh-normalization pilot, preserving all earlier candidates. Both strict and
clock-fallback attempts then stop at **`no known BK location evidence`**. VT has
two blocked punts with no known gross distance in that snapshot; an ordinary punt
cannot supply their location. A source candidate with an explicit one-yard block
is retained for review because the provider clock/recovery spot conflict.

Normalized SHA-256:
`f3314e3ba033f377b12f1cd8e4c1600a898c8fc4e9938a9c7dd231b48ba462bc`.
Experiment SHA-256:
`2ba3a8ff1185a33b8988c7b5e7670ccbe241a743798df6e363bdf8eb5926866e`.
No team completes and the sparse distance sample does not qualify for release.
A separate direct existing-guard check rejects the punt-return fumble sample:
three annotated positives, 33 unknowns, no explicit negative observations.
This later guard was checked directly; full generation stops earlier at BK.

The [recorded resume steps](../../data066-generator-recovery.md#completed-pilot-results-and-resume-point)
cover broader source reconciliation, a disclosed fitting-only return denominator,
full-cohort validation and outstanding release rosters. Raw flags and authored
allocator/engine behavior remain unchanged. Focused validation passes 248 checks
in total, with 80 generation tests explicitly deselected; full shared coverage,
publication and release qualification remain outstanding. All local pilot
commands have completed and their snapshots/receipts are retained for shutdown.

--- 2026-11-16 18:11 — resumed source and return-denominator pilot produces a candidate ---

The saved source/candidate work remains intact. The official blocked-punt
candidate now supplies its explicitly stated one-yard gross distance through a
hash-bound correction; provider clock and field-position conflicts remain in
the evidence. The fresh 33-correction snapshot round-trips all 99,968 events.

Experiment policy v5 adds a separately opt-in modeled return denominator,
preserving source observations and potential origins of unresolved recoveries.
It also retains the verified standalone rushing fumble for fitting; the earlier
experiment incorrectly omitted it as an unresolved recovery. Interception-return
absence is no longer silently modeled by the primary-play branch. Synthetic
controls first fail for all three behaviors; 32 experiment checks now pass,
with 89 passing cumulative experiment/diagnostic/core checks.

**Both strict-link and modeled-clock VT candidates now complete generation.**
The pipeline's final ordinary-file load and chart semantic/contrast checks pass.
This is one team's working candidate, not historical-fit or release approval.
The paired fitting reports each retain one standalone primary, model 6,747
return negatives separately from 67,927 primary negatives, and preserve the
automated unresolved counts (291 strict, 260 with clock fallback).
Private output: `private-data/data066-resumed-vt-return-model/`.

The [resume investigation](../../data066-generator-recovery.md#resume-after-shutdown-2026-11-16-evening)
records policy details and source pins. A baseline preflight now checks every
selected team to inventory remaining cohort failures. No authored allocator or
engine source changed, and no new historical files entered a public manifest.

--- 2026-11-16 18:32 — all selected teams generate private current-model candidates ---

The original whole-cohort preflight completes 19/55 baselines, with 36 blocked
by absent BK location evidence. DATA-068 separates physical initial blocked-punt
movement from statistical punt credit. Checked official-source corrections now
supply four physical locations; explicit team-then-league blocked-location pooling
preserves each team's block rate and reports the sparse support separately.

**All 55 selected teams now complete baseline and full current-model candidate
generation**, including exact output pins, ordinary-file loading, budget,
tactical-contrast and catalog checks. The candidate contains 275 final files and
275 baseline files, retained privately under
`private-data/data066-all-team-preflight-v3/candidate/`.
Three teams use own physical block evidence, 34 pool the known league block
locations and 18 have no observed blocks. Unknown individual locations remain
unknown. No ordinary-punt/zero-distance proxy was added.

The [recovery record](../../data066-generator-recovery.md#physical-blocked-punt-locations-and-full-candidate-2026-11-16)
pins the new 44-correction source and describes preserved provider conflicts,
denominator modeling and validation. This is software/pipeline success;
source/coverage, statistical, real-engine and distribution review still remain.
Four physical block locations and ten gross punt distances are sparse selected
evidence, and 260 modeled-clock fumble associations remain unresolved. Rosters
remain 29/55 candidates for 2002 and 66/116 for 2007. DATA-066 stays open; no
2002 historical output was added to a release manifest or approved for publication.

--- 2026-11-16 18:34 — final repeatability and shutdown verification ---

The final guarded source tree passes 315 focused source/generator/roster/package/
special-teams checks. Candidate v4 again completes all 55 selected teams with
identical baseline/final pins and an identical generation receipt. Independent
verification rehashes all 550 baseline/final files and reloads all 55 final teams
against their retained semantic identities. The current released 116-team audit
also passes. Full shared coverage and local browser verification remain incomplete;
this does not authorize a push or qualify historical data for release.

The [final recovery checkpoint](../../data066-generator-recovery.md#final-verification-and-stopping-point-2026-11-16-evening)
preserves the dirty public integration and exact private artifact pins for shutdown.
No local pilot must remain running. Source/statistical review, the unresolved
recoveries and roster completion remain outstanding; status stays open.

--- 2026-11-16 — complete roster acquisition, full-game panel and expanded kick evidence ---

All 55 selected teams have private season-correct roster candidates (DATA-067).
The v4 chart candidate passes a balanced 55-game current-engine panel: every
team appears twice, every game finishes and reconciles, and checkpoint/final
save replay succeeds in all 55 games. This is a mechanics panel, not a historical
schedule or proof of statistical fit. Coaching and per-team fit review remain
separate. Its receipt does not attest the newer source described below.

A fresh hash-bound normalization combines 99 individually reviewed corrections:
56 known gross kickoff distances, 39 known gross punt distances and four physical
blocked-punt locations. The additional 55 distance facts retain explicit official
source distances; they do not infer gross yardage from terminal field position.
Unknown individual facts and provider disagreements remain preserved. Normalized
snapshot SHA-256:
`ab7dd283c6536d14e5ed1e52c3b6d06ca8aed8b64bf8d49d46440a4dbb3f1b09`.
Adjudication manifest SHA-256:
`edd005e852a6bd319c7ad006d300dcea71243761592abf73c0c5e3f13814592d`.
Round-trip and independent event-difference verification pass; a fresh v5 full
candidate is regenerating. No authored allocator or engine behavior changed.

The final production-tree Python coverage gate is running. Frontend unit tests
(197), production build and dependency checks pass. Local browser tests cannot
start Chromium because macOS denies its Mach-port bootstrap, including outside
the workspace sandbox; no application assertion is reached. That host failure
must remain disclosed and needs actual browser evidence on a supported runner.
The previously successful upstream pipeline attests only its earlier build fix.
DATA-066 stays open pending final candidate review, exact packaging and release
checks. No newly generated historical files have been published.

--- 2026-11-16 — complete fresh candidate and combined private package ---

The fresh, separately retained source inventory supports 55 selected teams,
rather than the 52 successful old-pipeline outputs described in the original
report. All 55 regenerate with the cohort wrapper of the preserved authored
allocator. This is a new source/candidate identity, not reconstruction of the
missing 440-game snapshot or a silent extension of the old 2007 grant.

Independent local checks replay the retained normalization/adjudication inputs,
verify all 550 final/baseline pins and preserve all 70,887 selected OOB statuses
as unknown. The staged combined package passes the chart audit for 171 generated
teams and retains all existing 2007 chart bytes. Its normal catalog has 173 teams
including the two fictional samples. All 55 new roster pairs pass real packaged
API/CLI commentary, save/load and RNG-equivalence checks. The unchanged canonical
runner's separate 55-game panel passes with all checkpoint/final replays verified.

The 251 actual selected-opponent fixtures are undergoing source-matched fit and
coaching review. The private v1 driver's unsupported postseason label requires
a transparent continuation; it is not a complete qualifying panel yet. Full
Python coverage, browser validation, exact distribution/attribution review and
final public manifest integration remain pending. No new historical files are
public, and DATA-066 remains open. See the
[review record](../../data066-generator-recovery.md#final-source-review-and-exact-package-candidate-2026-11-16)
for exact identities, correction receipts and limitations.

--- 2026-11-16 — actual-matchup panel passes mechanics; rushing fit needs work ---

The explicit continuation completes all 251 selected-opponent fixtures, including
13 correctly configured postseason games, with zero failures and all replay
checks. Independent review finds no illegal coaching choice or fallback.
However, non-sack rushing averages 3.564 simulated versus 4.502 matched-source
yards per attempt, exceeding the existing 0.5-yard experimental reference
tolerance. Equal-team averaging agrees with the direction. This is an unresolved
candidate-quality finding within DATA-066; do not claim historical fit or relax
the threshold. The discrepancy is being decomposed before any generator change.

Local browser probes have also been stopped at the owner's direction because
startup failures trigger dialogs. Browser permission is granted; the host startup
problem remains a gap requiring a working validation environment.

--- 2026-11-16 — rushing mechanism review preserves the failed fit assessment ---

Of 19,454 panel rushes, 2,324 are fixed-rule QB Sneaks (0.880 credited yards)
and 137 are kneels. The net raw-result versus credited difference is 0.181 yards
per overall rush, combining field limits and recovery advances.
Ordinary numeric primary pairs separately show quantization/defense/field-limit
effects. These are different conditional populations, so they are not summed as
causal corrections and do not clear the inclusive 3.564-versus-4.502 finding.
The current published 2007 charts retain a similar failed accuracy assessment;
that comparison is not a new-cohort fit waiver. No engine or generator behavior
was changed to compensate for the coaching mixture. See the
[mechanism and roster review](../../data066-generator-recovery.md#rushing-decomposition-and-remaining-roster-review-2026-11-16).


--- 2026-11-16 — portable browser regression passes ---

All 72 unchanged real-engine browser tests pass in a local Linux ARM64 container
in 4.7 minutes. All 498 staged public source/test pins still match the main tree;
no Mac browser was launched. Actual native artifacts/default-browser launches
remain separate. The actual 173-team catalog check exposed an automated
substring-selection error in its private helper; exact displayed labels and both
team IDs are now checked before game startup. No production code or historical
data changed for that correction. The renewed 55-team UI roster/save run remains
pending. See the [Linux browser notes](../../data066-generator-recovery.md#linux-browser-gate-and-exact-catalog-follow-up-2026-11-16).


--- 2026-11-16 — all 55 actual-candidate UI checks pass ---

The actual assembled 173-team catalog matches API and rendered pickers. All 55
new teams pass exact team-ID selection, real engine roster commentary and UI
save/download/load in supported drive mode. No browser errors occur and the
server shuts down normally. Linux receipt SHA-256:
`665b8a77435008454cd8d4a0b40758c647ceb51ea0e52d1e3ee9b0e997c50a6e`.
No Mac browser was launched. The full Python gate continues; its first failure
is a stale schema-5 expectation after the documented schema-6 blocked-punt
extension. Unchanged focused reproduction confirms it; a precise expectation
correction is being validated separately. Packaging integration, final full
regression and new-cohort distribution review remain outstanding.

--- 2026-11-16 — final source-order and exact-inventory review ---

All 524 inferred interception locations independently match raw next-numbered-drive
starting coordinates and possession, with compatible period/clock. This resolves
31 provider-array ordering questions without changing source/model/chart bytes;
it corroborates provider consistency rather than official historical accuracy.
The pinned readiness review verifies all 1,045 runtime files, exact 275 new chart/
provenance files and 110 roster/source-note files, all 580 unchanged 2007 pins,
and no collision with original private imported benchmark paths. A fresh audit
passes all 116 shipped 2007 teams. Final integrated full coverage and exact new
chart distribution approval remain outstanding; rushing fit remains unverified.
See the [candidate review](../../data066-release-review.md).

--- 2026-11-16 — full expanded-season regression started privately ---

The proposed 173-team catalog first reproduces the install validator's exact
118-team assertion failure. Updating that expectation precisely to 173 retains
sample membership and passes all 69 focused install/packaging/documentation
checks. A separate complete coverage run now exercises the exact expanded
manifest, 275 new generated files and 110 roster/source-note files in a frozen
private tree. Engine/generator bytes match the parallel integrated source gate.
No full-run pass, publication permission or fit certification is claimed. Main
historical files remain untouched; exact new-chart distribution review is pending.

--- 2026-11-16 22:16 ---

The original full serial control completes with 6,849 passes, 91.01% branch-
enabled coverage and one stale schema-5 assertion failure. Its precise schema-6
correction is already in the frozen integrated source and season proposals.
Neither proposal's full gate is reported passing yet; one expanded-season
failure is being investigated. Two redundant serial copies are explicitly
interrupted, preserving their partial logs. Source replay, roster and browser
evidence remain separately scoped; DATA-066 remains open.

--- 2026-11-16 22:24 ---

The expanded-season failure is the old assertion that every runtime roster must
be one of the two fictional sample pairs. It is reproduced before correction.
The private proposal now preserves those exact sample pairs and additionally
requires exactly 110 hash-pinned files paired across its 55 selected 2002 teams.
Both affected packaging/install modules pass 112 tests; no production, chart or
roster bytes change. A fresh complete season gate is underway. The source gate
retains its correct old-manifest assertion and continues independently.

--- 2026-11-16 23:14 ---

The corrected exact 173-team private proposal completes all 6,886 Python tests
in 3,034.69 seconds, with 90.77% branch-enabled coverage, zero skips/warnings and
exit 0. Independent receipts verify all original cases exactly once, all 1,987
frozen inputs and the measured import roots. Evidence:
`private-data/data066-season-validation-v2/completion.json`; log SHA-256
`8cf32fbc22549629f32c634c189aba44d705501b597d05e5d7c097f8812a8fa3`.
Earlier failed/interrupted gates remain preserved. No further production or
candidate-data correction was required. The separate source-only gate and
maintained integration are still pending. Historical fit remains UNVERIFIED;
the rushing reference remains FAILED. New-chart distribution approval remains
pending; the reviewed roster approval is already recorded in DATA-067.
Acceptance stays open until the reviewed release selection is committed.

--- 2026-11-16 23:26 ---

The source-only full gate also passes: 6,886 tests, 90.77% branch-enabled
coverage, 5,198.89 seconds, zero skips/warnings, exit 0. All original cases,
1,601 frozen source pins and measured import roots verify independently.
Receipt: `private-data/data066-parallel-validation-v1/source/completion.json`;
log SHA-256 `b517a46cabdcce13e296f453f84b1a73166c50d95bdc203edf6e5c205717b606`.
The guarded integration applies exactly 12 reviewed source/packaging changes,
with backups and no historical-data or FLOW-007 changes. Both full gates now
pass. The [candidate review](../../data066-release-review.md) records exact
55-team scope, package hashes and the failed experimental rushing reference.
Generator source publication is authorized; exact new-chart distribution and
maintained data acceptance are still pending. Keep this ticket open.

--- 2026-11-17 06:54 ---

The owner authorizes a two-hour rushing-calibration timebox and an earlier
stop after a valid setting. The first eligible setting,
`CalibrationProfile(run_yards_scale=1.15)` shared across all 55 teams with
every other field and defensive profile neutral, is frozen before opening
unused-seed validation metrics. Source facts/targets, rules and reference
coaching are fixed. A second predeclared training trial is retained without
changing that selection; no third setting or additional tuning is needed.

All 12 existing pooled references pass on the 251-fixture fresh-seed panel.
Against source 4.5020132767, non-sack rushing improves from 3.4982233895
(19,419 attempts) to 4.2383582090 (20,100 attempts), reducing absolute pooled
error by 73.734%. Average absolute team rushing error improves from
0.9359369477 to 0.2931111067; 47/55 teams are within half a yard, versus 10/55.
The paired improvement's approximate 95% interval is [0.6162990219, 0.8639706171]
yards/attempt. Both 251-game validation panels pass state/trace, period-score,
checkpoint/final replay and legal-choice review, with no coaching fallbacks.

The generator's release API now exposes its existing bounded calibration
profiles; synthetic tests verify neutral byte identity, profile receipts,
increased rushing gains and independent passing targets/event rates. The shared
breakaway response can legitimately change passing-cell representation.
The original 2007 manifest's 580 generated-file pins still match. Full details:
[bounded calibration](../../data066-generator-recovery.md#bounded-rushing-calibration-2026-11-17).

Selected private files/profile/paired audit:
`private-data/data066-rush-calibration-20261117-v1/scale-1.15/candidate/`,
`selected-profile.json`, and `validation-review.json`.
Generation-receipt SHA-256:
`bd2d86b428e4b00a28b1aa1bf6f03f7f64183dea050b6dfeab28a3d3d9e6c535`.
Numerical search stops after this validation as requested.

DATA-066 remains open for maintained release acceptance using the selected
candidate's exact pins. The prior package/full-gate data pins describe the
neutral charts. Historical fit stays UNVERIFIED: eight individual teams remain
outside the half-yard reference, source/model limitations persist, and unused
simulation seeds are not held-out historical observations. Exact chart
distribution approval remains separate; generator/source and DATA-067 roster
approvals are already established.

--- 2026-11-17 10:13 ---

Source publication regression is complete with the runtime interruption
disclosed: the full 6,888-case inventory passes 6,886 cases and encounters
two `FileNotFoundError` failures after Homebrew replaces the original Python
3.12.8 standard-library path. Both exact cases then pass on Python 3.12.16
with unchanged code and assertions. Combined branch-enabled coverage is
90.77%, with all original arcs preserved and no skips/warnings.
This is a composite result, not one clean full run. All 1,602 frozen source
pins, original test execution and import roots verify independently.

The 14 release-pipeline cases also pass on the current Python 3.12 runtime.
Frontend 197/197, production build, audit (zero vulnerabilities), Linux
real-engine browser 72/72, lint, formatting, dependency consistency and the
published-chart audit pass. Final API regeneration reproduces all 55 selected
teams' 275 final and 275 baseline pins. Source publication includes the API,
synthetic tests and documentation; candidate charts remain private and the
published 2007 manifest stays unchanged. Details and exact commands:
[source regression](../../data066-generator-recovery.md#completed-source-regression-after-runtime-retests).

Composite receipt: `private-data/data066-rush-calibration-20261117-v1/publication-gate/completion.json`
(SHA-256 `46c6c476dd719f77e365c63d38606a30278608a27500ad7cbeb872ab24b7c6d9`). Earlier failed attempts are retained.
DATA-066 remains open for maintained selected-candidate release acceptance;
historical fit remains UNVERIFIED and exact new-chart distribution remains a
separate approval scope. No further numerical tuning is performed.
