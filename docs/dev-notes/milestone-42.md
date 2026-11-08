# Milestone 42 — Play-specific depths and independent chart validation

Status: assigned for implementation, 2026-11-07. Validation and acceptance pending.
Owner directs this correction into the next milestone and release after Alpha 9.
Target: **1.0.0**, tag `v1.0.0`, per owner direction on 2026-11-07.
This supersedes the earlier Alpha 10 target. Confirm the tag is unused before
publication and preserve prior alpha tags/assets as immutable history.
Required high-priority work: [DATA-064](issues/DATA/DATA-064.md) corrects
play-specific interception depths; [DATA-055](issues/DATA/DATA-055.md) completes
independent per-event game accounting; [DATA-046](issues/DATA/DATA-046.md)
compares frozen candidates with the available compatible 2007/2008 developer
references. The owner explicitly added DATA-055/046 and requested a subagent
with high reasoning on 2026-11-07.

## Problem and resulting behavior

The released offense generator supplies the same team-level interception-depth
sample to every passing column. Ohio State's Screen INT 44 therefore draws on a
real historical catch depth without evidence that the play was Screen. The chart
viewer accurately shows its CSV; correcting display text would leave gameplay
unchanged and would not address the defect.

Generated interception depths must follow a declared policy appropriate to the
called play and the available evidence. An unidentified historical pass is not
observed Screen evidence. Keep observed conditional samples, unconditional team
support, authored priors and unknowns distinct in generation/audit receipts.
Do not promise exact real-world call identification where sources lack it.

## Paydirt consultation

Reviewed local Paydirt docs/dev-notes/issues/DATA/DATA-040.md, especially its
conditional-source, physical-mass and actual Priority validation requirements.
Adapt those principles and its lesson that an allocator fix can alter tactical
exposure even when aggregate mass is unchanged. Do not copy its NFL call mapping,
dice weights, fixed-depth assumptions, private team data or runtime code.
Bowl Bound's call definitions, source model, exact dice and resolver remain the
authority. Existing Bowl Bound generator inspection identifies _int_locations
and generate_team as the shared-pool path; work in the maintained research
lineage and export through the ordinary chart codec.

## Added audit and benchmark acceptance

For DATA-055, preserve the known failing kickoff-return recovery reproduction,
correct the distinction between chart consultations and actual recovery draws,
and independently verify event ownership, accepted/voided statistics, QT terminal
classification, consulted cells/priority and relevant pending-choice save/replay.
Use synthetic mutations and retained passing controls; rerun affected frozen
complete-game evidence. An aggregate engine-derived reconciliation alone is not
independent event acceptance.

For DATA-046, inventory and freeze the available authorized 2007/2008 compatible
reference pairs before running comparisons. Reuse the corrected observer and
matched runtime/coaching/rules conditions. Compare exact weighted mechanisms,
conditional depths/tails, tactical benefit/cost and terminal engine behavior;
assess both chart sets against the same eligible historical evidence. Explain
supported model differences and unresolved source questions instead of treating
reference equality as the target. Keep charts and detailed comparison reports
private, publish only a safe synopsis, and distinguish explored references from
transfer evidence on additional teams without references. Research-only 2008
candidate preparation does not add that season to the release catalog.

Implement the generator correction and observer tests as separately reviewable
changes, then freeze the candidate before numerical benchmark execution. Deliver
one evidence-backed component verdict per ticket and an overall release decision.
Do not close any of these three tickets through a partial helper result or an
unexecuted acceptance requirement. Report a concrete blocker if necessary while
continuing independent authorized work.

## Execution and acceptance

1. Freeze the Alpha 9 baseline, current generator/runtime/source identities and
   exact failing case. Inventory depth assignment for every passing call in both
   offense and defense, and report how often call labels are actually observed.
2. Define and review a simple conditional policy using Bowl Bound play semantics,
   eligible public evidence and authorized private reference diagnostics. Specify
   scarce/unknown support and authored-prior sensitivity explicitly. Choose
   numerical criteria before regeneration. Do not claim a universal yardage cap
   or historical conditional truth without support.
3. Add meaningful synthetic failures before changing behavior: known Screen and
   deep-call evidence, unidentified long-pass evidence, mixed/sparse/all-unknown
   sources, legal behind-LOS values, zero INT budgets and both possession sides.
   Passing controls preserve provenance and legal independent outcomes.
4. Correct generation and add a mandatory independent plausibility gate for the
   affected outcome locations. Check exact weighted INT exposure, per-call and
   per-formation budgets, Priority, catch depth, touchback/end-zone/return effects
   and uncertainty. Any changed target, support, frequency or mean is a declared
   model change, not a layout adjustment. Do not mask the problem with clipping,
   token relabeling, cosmetic shuffling or altered observation denominators.
5. Regenerate LSU/Ohio State first. Compare ordinary loaded CSVs, chart API and UI,
   report numerical before/after changes, and obtain owner visual review. Keep
   screenshots and full source comparisons private unless separately authorized.
6. After paired acceptance, regenerate the existing approved cohort and audit all
   teams/calls. Census INT and related outcome patterns; retain every exception
   with a reviewed explanation. Freeze exact model/source/output identities and
   verify complete semantic round trips. The final release candidate must pass
   the new plausibility gate; an unsupported required component is not a pass.
7. Run focused/cumulative generator and engine regressions, detailed representative
   full-game/rare-branch checks and the established full release gate. Renew all
   evidence affected by the model change, and disclose any untouched historical
   accuracy or full-season qualification limits. This milestone does not require
   exact historic winners or pretend that unknown designed calls are observed.
8. Commit the reviewed implementation, then coordinate 1.0.0 package/application,
   frontend, launcher, native installer and release metadata with a final regression
   run. Prepare the unused v1.0.0 tag, verified native builds and regular Latest
   release-page correction notes through the existing workflow. Preserve Alpha 9
   and all previous tags/assets plus current privacy/sample/generated-team
   allowlists. Record tested integration commits before resolution and applicable
   owner play-test confirmation before closure. See [1.0.0 preparation](release-1.0.0.md).

## Scope boundaries

Correct generated data and auditing; the UI remains an engine-provided chart
display. Do not alter Bowl Bound rules to compensate for a generation fault.
Razzle-Dazzle is an artificial engine action, not a chart/source play family.

The optional defensive (B) formula, new-season publication and completion of
broader historical calibration investigations outside DATA-046/055/064 remain
separately tracked. All three assigned tickets are milestone work; record their
acceptance dispositions before the next release. The already published
experimental Alpha 9 is not historical-accuracy approval.

## Planning validation

Documentation-only scheduling change. Regenerate the issue index and run existing
issue metadata/index/creation and applicable documentation checks. Implementation
has not started, no synthetic failure or fix pass is claimed, and no chart,
generator, engine, release version, tag or asset is changed by this plan.

Scheduling checks: issue index regenerated; 38 existing issue/documentation checks
pass; 20 local links resolve; whitespace checks pass. This validates the plan's
tracking only, not implementation or chart accuracy.

## Implementation checkpoint — paired review pending

The [authored catch-depth prototype](authored-interception-depth-policy.md)
records the provisional numerical contract, explicit observation qualification,
finite physical-mass objective, independent checks and remaining limitations.
The research generator reproduced the shared-pool fault with synthetic controls;
the paired ordinary CSV/API/browser preview is now available privately for
owner review. All 56 paired offense/formation encodings pass a separate
exhaustive allocation check. A bounded downstream panel checks both possession
sides at eight field anchors, retaining pending/unsupported components.

Full-cohort generation is held at the required owner paired-review checkpoint.
DATA-064, DATA-055 and DATA-046 remain open. The independent observer and reference
inventory/comparison work proceed in isolated research lanes. No release version,
tag or immutable Alpha 9 artifact has changed.

## Whole-cohort passing-cell audit

Owner explicitly requested this acceptance step on 2026-11-07: after the INT fix
is ready, audit passing cells for unreasonable values. This extends DATA-064's
existing all-team plausibility requirement; it does not replace the generator fix.

- Start with the corrected final-pipeline LSU/Ohio State pair. After owner visual
  acceptance and approved full regeneration, repeat over every team in the
  release candidate. Freeze model/source/chart identities and inventory every
  applicable cell so missing teams, columns or unparsed values fail coverage.
- Cover offense and defense Screen, Sprint Out, Boot-leg and Drop Back, plus
  Option passing continuations and dependent B/QR/QT pass outcomes where relevant.
  Separate primary triggers from terminal results. Razzle-Dazzle is an artificial
  engine action, not a tenth chart/source play family.
- Check INT catch depth against each called play's declared observed support or
  authored policy, including legitimate behind-LOS values. Test the final
  post-calibration/export bytes so a later stage cannot reintroduce implausible
  depths. Distinguish catch depth, pass gain and return distance.
- Inspect unusually large positive/negative pass gains, blank/zero semantics,
  priority/replacement facts, incomplete-pass and special-result tokens, and
  sideline flags. Check actual engine interpretation and field/end-zone effects;
  a syntactically valid cell does not establish football plausibility.
- Census exact values, normalized result families and rendered color/flag unions
  for repeated rows, runs, cross-call/formation blocks and cross-team templates.
  Check all families together so an INT correction cannot conceal a QT, BLACK,
  B, penalty or ordinary-yardage allocation problem. Repetition alone is not proof
  of a defect, and cosmetic randomization is not a correction.
- Report raw counts and exact Bowl Bound dice-weighted primary and resolved
  frequencies separately, including Priority and conditional branch effects.
  Compare to declared source/model budgets where supported. Declare numerical
  criteria and source limitations before applying them; do not invent universal
  yardage caps, infer designed calls from unidentified passes, or tune thresholds
  after a finding merely to obtain a pass.
- Retain a per-finding team/call/roll/value explanation and disposition: corrected,
  supported retained result, or unresolved issue. Quantify complete coverage and
  unknowns. Any unresolved required plausibility finding must be surfaced in the
  release decision. Add meaningful synthetic regression controls before fixes,
  preserve probability controls and rerun the affected evidence.

Paydirt consultation for this extension: reviewed DATA-040 and DATA-041. Adapt
its separation of raw geometry, weighted exposure and terminal behavior, and its
lesson to census every outcome family rather than relocating one visible stripe.
Do not copy NFL call mappings, dice weights, thresholds, private charts or runtime
code. Detailed team-level evidence remains private; retain a public-safe synopsis.

Acceptance is pending: assigning this audit or passing documentation checks is
not a completed chart audit or release approval.

Tracking-only validation for this extension: regenerated the issue index with
`.venv/bin/python scripts/build_issue_index.py`; existing issue/documentation
checks (`tests/test_issue_tracker.py`, `tests/test_create_issue.py`,
`tests/test_priority_docs.py`, `tests/test_release_player_docs.py`) passed 38 tests
using `.venv/bin/python -m pytest ... -q`; `git diff --check` passed.

## Default web port for simultaneous Paydirt play

Owner added [DEV-078](issues/DEV/DEV-078.md) to the next 1.0.0 release on
2026-11-07. Both Bowl Bound web startup paths must default to 8001; the frontend
API proxy and current player documentation follow that default. Paydirt remains
on 8000. Explicit port overrides and existing local binding/lifecycle remain.

Consulted local Paydirt paydirt/__main__.py start_web_server and main: all normal
web paths select 8000. Choose a separate Bowl Bound default; do not copy its
server implementation or modify Paydirt. Existing running game ports are retained.

Test first: the backend parser and production-launcher listener checks both fail
against unchanged production at 8000; the explicit 8123 override control passes.
Changed expectation: Bowl Bound's default address is 127.0.0.1:8001, with 8002 as
an example alternate port when occupied. No football/chart semantics change.
Validation and tested commit references will follow before ticket resolution.

DEV-078 focused verification: 24 launcher tests pass after 2 expected default-port
failures and 1 passing explicit-port control before the implementation. Ran
`.venv/bin/python -m pytest tests/test_launcher.py tests/test_web_launcher.py tests/test_api.py tests/test_packaging.py tests/test_release_metadata.py tests/test_release_player_docs.py tests/test_issue_tracker.py tests/test_priority_docs.py -q`:
100 passed. Node 24.22.1 frontend `npm --prefix frontend test`: 158 passed;
`npm --prefix frontend run build` passes. Imported the actual Vite config and
verified its localhost:8001 proxy. Ruff lint/format and whitespace checks pass.
Actual synthetic-resource subprocess checks start both entry points at default
8001 while the existing HTTP service on 8000 remains unchanged. These checks do
not substitute for final 1.0.0 integration/native release acceptance.

## Paired visual review accepted

On 2026-11-07 the owner explicitly accepted the corrected LSU/Ohio State pair:
"yes, it looked good to me" and confirmed capturing a screenshot for their own
announcement. This accepts the actual final-pipeline-v2 pair, receipt SHA-256
7fdf099f6ca167f95e33e458b7a310145a85c1a73a11444a54ae2a0e3ba9f176, and lifts the
owner-review hold before full 116-team regeneration. Storage capacity remains an
independent prerequisite; do not bypass its reserve guard. All numerical,
whole-cohort passing-cell, independent event/reference and final release checks
remain mandatory. Do not treat visual approval as historical-fit certification
or publish a Facebook post on the owner's behalf.

## Local capacity and sibling cleanup

Owner requested the November 7 local cleanup in [DEV-079](issues/DEV/DEV-079.md).
Clearing only npm's rebuildable download cache reclaimed 6,416,461,824 bytes;
the generation agent may proceed under the unchanged real-capacity reserve.
Paydirt cleanup is separately assigned by the owner. Preserve the original
checkout's dirty maintenance record, active research/integration trees and live
previews. Retire idle late-half/web-history worktrees only after private archive,
per-file hash, retained branch and open-file verification. Preserve the independent
public repository's divergent work. Detailed recovery evidence stays ignored.

DEV-079 retirement completed: only late-half/web-history linked checkouts removed,
663 archived files verified, exact named branches/tags retained, original dirty
owner files unchanged, shared dependency targets retained and all three active
release/review previews healthy. Both current generation/event-audit lanes confirm
no retired-path dependency. The remaining sibling repositories are the main
checkout, research cohort/generator and independent public repository. About 20 GB
free after this and the owner's concurrent cleanup; full116 generation is running.
Recovery archives and manifest remain private. Existing tracker/docs checks follow.

DEV-079 operational resolution is recorded against tested commit a8009ac.
Regenerated the index with `.venv/bin/python scripts/build_issue_index.py`;
`.venv/bin/python -m pytest tests/test_issue_tracker.py tests/test_release_player_docs.py tests/test_priority_docs.py -q`
passed all 22 checks, and `git diff --check` passed. Verified retired directories
are absent from both the filesystem and registered worktree inventory. This is
local maintenance acceptance, not completion of the 1.0.0 chart/release gates.

## Corrected ordinary release inputs and compound gate

The owner-approved full cohort is now integrated into the actual ordinary release
inputs: 580 generated files for exactly 116 approved 2007 teams, plus 14 unchanged
fictional team files and the unchanged sample license. All candidate file hashes
match the independently reviewed export. The update changes 789 catch-depth cells
(688 offense, 101 defense); kinds, flags, incidence and other football facts remain
unchanged. Generated provenance and metadata record the authored depth policy.
The release manifest binds these exact bytes.

Reconsulted local Paydirt DATA-040 before integrating the release gate. Adapt its
separation of source observations, conditional assumptions and physical mass;
do not copy NFL weights, rules, private data or runtime code. The schema-three
expectations retain the original Alpha 9 budget baseline while independently
qualifying the new conditional component. Parent comparison masks only fixed
passing INT yardage; kinds, priorities, flags, colors, all other facts, family
budgets, formation budgets and QT anchors remain checked. A separate exhaustive
checker verifies every one of the 28 offense/defense passing columns per team
against the declared depth contract. Missing, variable, unsupported, noncanonical
or budget-unknown encodings refuse the gate. Explicit reviewed zero eligible
samples is required here; absent/unknown counts are never converted to zero.

Test first: the old gate accepted a declared unsupported depth; null declarations
and foreign checker imports also produced meaningful failures before their guards.
Seventeen new controls and 70 existing audit controls now pass. Isolated subprocess
fixtures were extended to copy the complete checker dependency closure; assertions
were retained. Ruff lint/format and focused Pyright pass. Independent source review
accepts this bounded gate. The fresh public auditor passes all 116 actual integrated
teams with exact 216/36 physical distributions. This is authored-model qualification,
not historical conditional truth. The original baseline remains frozen privately.

The full Python coverage gate is running; the current frontend has 158 passing
unit tests, a successful production build and 64 passing real-engine browser tests.
Browser tooling reports its existing color-environment warning. Fresh representative
and matched reference games, addressed decision saves and final release acceptance
remain separate requirements. No version, tag, native asset or published release
has changed at this checkpoint.

Independent review caught report labels that overstated whole-fact preservation
for schema three. A meaningful synthetic failure now guards precise
`except_passing_int_depths_preserved` fields; schemas one/two retain their original
labels. All 88 related tests pass after this correction, and focused Pyright has
zero errors/warnings. The full coverage run was stopped before this report-source
edit and restarted on the final bytes; the interrupted run is not a pass.

The real packaging path also passes `stage_sources` followed by a fresh
`audit_staged_charts` over all 116 staged teams; temporary audit expectations are
removed afterward as required. The first staging invocation correctly refused an
output inside its source tree before writing; the successful run uses a separate
ignored destination. Package selection remains the exact approved allowlist.
All 38 tracker/player-documentation checks and `pip check` pass; generated files
contain no absolute developer paths or private source/report paths.

## Fresh-game observer boundary followup

A matched reference game exposed a false observer refusal at a tied fourth-quarter
punt decision: the correct fair-catch report was followed by fresh overtime toss
rolls, while the observer asserted zero total decision draws before its near-period
exclusion. Eight meaningful unchanged-source failures cover fair catches, numeric
returns, mirrored sides and tied toss sequences. The correction independently
matches the recorded overtime requests/faces under strict normal tied-quarter
prerequisites before checking the intrinsic zero/one return draw. Report, complete
boxes, score, fresh IDs, chart lookups and ordinary unexpected-extra-draw controls
remain strict. Overtime continuation, clock and continuity stay UNVERIFIED; matching
the toss tail is not general overtime qualification.

Author verification passes 168 related tests; independent review passes 37 new
controls plus the ordinary extra-draw refusal. The separate integration checkout
passes the same 37 controls, lint and formatting. The retained 190-report capture
now receives an explicit partial result with its overtime continuation unknown;
no engine game was rerun to replace the refusal. Active game captures retain their
original source pins. Final coverage must run on the completed reviewed integration,
not the earlier intentionally interrupted 1,033-pass pre-fix run.

The next retained benchmark refusal was also an observer scope error: an Option
penalty path resolves through Bootleg, a second penalty and an incomplete pass;
the original numeric defense is correctly cancelled. The fixed ordinary-penalty
observer checked retained defense before excluding that prepared Option path.
Four meaningful synthetic failures precede the minimal eligibility correction.
The selected typed Option marker/path must be bound before the whole commitment
is left UNKNOWN; ordinary retained-defense corruption still refuses, and global
row/priority checks remain intact. Author 93 related checks, independent six controls
and the retained 202-report read-only re-audit pass at that scope. No engine, chart,
coaching, source threshold or event credit rule changes. The original refusal is
retained, and only unexecuted matched exposures resume under the old capture pins.

## Completed integrated regression and representative checkpoint

The [integrated validation checkpoint](milestone-42-final-validation.md) records
the actual corrected release data, full broad passing census/dispositions,
5,525 passing Python tests (92.25% combined/87.73% branch coverage; no skips or
warnings), unchanged frontend/browser evidence and independently reviewed 34-game
core/strict/addressed results. Both complete raw repeats pass. Independent causal
and clock results remain partial, with exact unqualified populations retained.
The complete matched inventory is executed/reused, sealed and independently
reviewed at its declared finite scope. All three assigned tickets remain open through
final acceptance. No software version, native build, push, tag or publication is
claimed. Final coordinated 1.0.0/native/default8001/screenshot acceptance stays
separate from authored-model and bounded audit qualification.
