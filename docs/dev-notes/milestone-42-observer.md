# Milestone 42 independent observer work

Status: implementation in progress; DATA-055 remains open.

## Recovery evidence contract

The first correction distinguishes chart consultations from dice consumption.
A fixed numeric kickoff flight and return require exactly two offensive draws;
a fumbled return can legitimately consume a third recovery draw with only two
chart rows. The routine numeric oracle must not reject that branch merely for
having three draws, or award recovery correctness without independent evidence.
Unsupported recovery remains UNVERIFIED and taints subsequent endpoint continuity.

The bounded recovery oracle accepts externally pinned inventory version
2. Each team declares team ID, season, the save-format chart fingerprint, full
normalized-object SHA-256, gameplay-metadata SHA-256 and an inclusive recovery
interval with strict integer endpoints between 10 and 39. Version 1 remains valid
for existing lookups but supplies no recovery authority. A range excluding a roll
is known opponent recovery, distinct from missing range evidence. Matching a
fingerprint is input agreement, not source qualification or loaded-code attestation.

Initially admit only a fixed in-field F location, one additional fresh offensive
recovery draw, and no recovery advance, end-zone depth, variables, penalties or
additional return lookup. Derive side/spot from the retained typed graph and the
externally pinned range before reading report outcomes or statistical credit.
Kick returns remain excluded-zero offense. Scrimmage F retains its resolved
category; last QR/QT controls, with a negative QT net result a sack, QT zero or
positive a rush, and ordinary passing F a completion. Stop original offensive
yardage at first opposing recovery. Full boxes, scoring, called/resolved labels,
field/report flags and observed draw/row/request closure remain checked separately.
Unknown branches cannot become passes through a matching claimed credit.

Required synthetic controls include both sides; own/opponent recovery; missing
range evidence versus a known excluding range; malformed endpoints and false
identity pins; wrong owner/location/category/boxes; numeric extra draws; QT
negative/zero/positive and ordinary completion controls; retained pending state
without premature credit; exact save/load continuation. Complex recovery advances,
end-zone returns, penalties and independent period attribution remain explicit
unknowns until their own supported population is implemented and reviewed.

## Paydirt consultation

Reviewed local `tests/test_fumble_replay_statistics.py` and
`tests/test_zero_yard_sacks.py`. Adapt mutation controls that distinguish retained
from voided events, original statistical owner and terminal pressure outcomes.
Do not reuse NFL sack accounting, Paydirt zero-yard sack semantics, mocked
resolver expectations, chart values or its runtime. Bowl Bound statistics use
explicit markers, include sacks in rushing totals and classify QT zero as rush.

## Initial test-first evidence

On unchanged `cbc88611`, the maintained synthetic F-return recovery test fails
at the routine two-draw assertion; numeric return and numeric-extra-draw controls
pass (1 failed, 2 passed). Moving the assertion into the numeric return population
passes all three without granting recovery GO. The related kickoff/CLI regression
passes 120 tests on Python 3.13.1. Read-only re-audit of all 34 frozen Alpha 9 wrappers now completes without
observer refusal (6,419 reports). Version-1 inventories keep recovery outcomes
UNVERIFIED; this is not complete independent PBP acceptance. Input and observer
hashes remain unchanged before/after; no engine module was imported. Original
receipts, failures and source artifacts remain unchanged.

## Fixed recovery implementation population

Inventory version 2 uses exact `fingerprint`, `object_sha256`,
`metadata_sha256`, and inclusive `recovery_range: [low, high]` fields in each
team entry alongside team ID and season. It still requires every one of the
840 normalized cell addresses per team. The interval and hashes are detached
from caller mutation. Missing version-1 metadata stays unverified; wrong known
fingerprint or malformed/noninteger/out-of-10–39 interval refuses.

The selected typed B/QR/QT/Option graph is derived before reading credit. A fixed
in-field F branch can finish with one extra fresh offensive recovery draw and no
extra lookup. The approved [turnover profile](../turnovers.md#fumbles) authorizes recovery
rolls 17–19 when retained, or 37–39 when lost, to allow another
return and remain outside this first population. Goal/end-line, variable, penalty,
extra return and scoring chains remain unverified. Known no-advance recovery
checks the original credit owner, last-QR/QT category, called/resolved labels,
actual net gain, both full offensive boxes, zero points, field state, report
history, strict TimingFacts and complete request/row/draw/priority closure.
A pass-origin B fumble is a completion followed by a fumble; QT cannot become a
completion under the approved marker policy. Both sides, both recovery owners,
QT negative/zero/positive, QR loss and pass-origin B are forced synthetic subjects.

For kick recoveries, final receiver possession has a 10-second change of
possession. If the kicking team regains the fumble, final possession matches the
pre-kick side; with no other short category the standard matrix requires 30
seconds, deferred through the documented normal clock-choice format. This follows
[rules-profile standard timing](../rules-profile.md#standard-timing-matrix), not
an unconditional ten-second kickoff assumption. Strict normal context, unchanged
committed clock/ledger, exact field, excluded-zero boxes and pending timing remain
checked. Period crossing, carried fouls, overtime and modifiers stay outside scope.
A transient possession change is not a second clock charge.

## Pending save subjects

Five forced synthetic subjects save before each mandatory decision: interception
decline, live interception return, end-zone touchback, accepted previous-spot
penalty and declined penalty. They compare exact saved bytes and future
continuation across the restored object, check that pending states append no
committed report or offensive credit/points, then check exactly one committed
original-owner credit and independently literal field/stat totals. These subjects
exercise supported save boundaries; they do not certify every pending decision in
the retained historical games. The whole-game `pending_choice_save` capability
therefore remains UNVERIFIED without a complete corresponding exposure inventory.

## Recovery regression evidence

Before recovery implementation the fixed recovery positives remain unverified.
The initial six corruption fixtures had a callback-signature error; after its
correction all six reproduce DID NOT RAISE against the exact restored pre-recovery
function source. The maintained new implementation refuses those wrong owner,
yards, class, called/resolved and outcome facts. No engine defect is claimed.
The initial pending conformance run used an incorrect box-field name, corrected to
the documented `interceptions` field; those setup failures are retained privately.
Two meaningful before/after inventory-class alias failures precede the CLI binding
fix. The frozen focused recovery/inventory/pending/CLI suite passes 78 tests.
The version-2 read-only re-audit completes all 34 wrappers and 6,419 reports,
with no engine imports or changed input/source bytes. It independently checks
the two initial F-return recoveries that caused the old refusals; a later
F-return behind unsupported prior state remains unverified rather than reanchored.
No qualified QT-F event occurs in this retained population; its new authority
is exercised by the explicit synthetic matrix. The pre-followup cumulative passes 2,029 checks in 440.19 seconds. A later
actual synthetic recovery-advance probe found an additional premature graph/row
closure: a legally authorized advance can consume another return row. Four
maintained own/opponent scrimmage/kickoff controls fail before the narrow guard
correction, then 44 focused controls pass. These advances remain UNVERIFIED;
known no-advance recovery and ordinary numeric row/draw closure stay strict.
The completed cumulative is retained as pre-followup evidence, not a claim that
the later source passed the identical full run. Two final related-test command
attempts named nonexistent test files and ran no tests; those setup refusals are
retained separately. No failed run is promoted to a pass.


The renewed frozen source passes 704 related checks in 235.21 seconds on Python
3.13.1, including the four advance controls, prior numeric-extra refusal and
physical-dice populations. Independent review passes 73 overlapping focused
checks in 7.89 seconds and verifies all 52 source/test pins. All 34 immutable
wrappers re-audit with 6,419 reports, zero engine imports and unchanged input/source
hashes; the prior core accounting/results fields remain identical. These are
read-only retained-evidence audits, not new game executions. Documentation checks
pass 34 cases. Full DATA-055 remains open; the next acceptance step inventories
actual unqualified events and per-choice save evidence rather than treating every
nonmatching helper exclusion as a separate football gap.

## Previous-spot penalty checkpoint

The reviewed `a9007c32` observer adds independent accepted-previous-spot
commitment checks. It derives supported enforcement from the typed foul token,
retained dice and prepared state, checks replayed down and half-distance behavior,
and refuses invented credit, owners, called/resolved labels or excluded boxes.
Mixed offsets, retained-defense continuations, marked or complex prepared plays
remain unknown. See the [bounded contract](independent-pbp-penalty-contract.md).

A separate local timing proof admits only the documented normal-regulation
ten-second population with matching clock anchors, ledgers, timeout budgets and
initial/pending timeout mirrors. It never clears an unsupported earlier clock or
continuity chain. Twelve meaningful ignored-corruption failures preceded the
commitment correction; six timeout-mirror corruptions preceded the final narrow
guard. Existing precise PAT failures remain preserved.

The exact reviewed source passes 2,149 synthetic checks in 479.69 seconds, with
no skips or warnings. All eighteen production observer/producer/runner files
pass Pyright without errors or warnings. Independent review verifies the actual
committed source and retained artifacts. The integration copies exactly the
48-file recursive safe dependency closure, without research history or runtime
engine changes.

Read-only re-audit of the same 34 immutable wrappers retains 6,419 reports,
checks 121 live previous-spot commitments and 122 reports, and independently
checks 39 local ten-second charges; 83 associated clock cases remain unknown.
All prior result fields remain unchanged. The terminal-handler census links
5,128 reports to existing bounded authority and leaves 1,291 without it; this is
coverage bookkeeping, not an accuracy percentage. The 1,042 observed nonclock
mandatory decisions lack addressed save records in these old wrappers. Aggregate
midpoint/final replay flags cannot repair that missing evidence. No fresh
historical games or complete DATA-055 qualification are claimed.

Integration validation on the exact copied source passes 168 focused
penalty/CLI/runner checks and 36 documentation/tracker checks. Ruff and the
18-file production Pyright check pass; the shell's system Python/npm-version
warnings were corrected by using the established explicit project interpreter
and Node 24 paths. Those setup failures are not engine regressions. The pending
save recorder and its runner callback are excluded from this observer checkpoint.
