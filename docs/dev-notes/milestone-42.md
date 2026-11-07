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
