# Milestone 42 — Play-specific interception depths and plausibility

Status: prioritized and scoped, 2026-11-07. Implementation and validation pending.
Owner directs this correction into the next milestone and release after Alpha 9.
Target: Alpha 10, subject to checking the next unused immutable tag at publication.
[DATA-064](issues/DATA/DATA-064.md) is a required next-release correction.

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
8. Commit the reviewed implementation, then prepare the next unused Alpha 10
   release tag, native builds and release-page correction notes through the
   existing release workflow. Preserve immutable Alpha 9 assets/tag and existing
   privacy/sample/generated-team allowlists. Record tested integration commits
   before resolution and applicable owner play-test confirmation before closure.

## Scope boundaries

Correct generated data and auditing; the UI remains an engine-provided chart
display. Do not alter Bowl Bound rules to compensate for a generation fault.
Razzle-Dazzle is an artificial engine action, not a chart/source play family.

The optional defensive (B) formula, new seasons and completion of every broader
historical calibration investigation remain separately tracked. This milestone's
defined correction and acceptance checks are required before the next release;
the already published experimental Alpha 9 is not historical-accuracy approval.

## Planning validation

Documentation-only scheduling change. Regenerate the issue index and run existing
issue metadata/index/creation and applicable documentation checks. Implementation
has not started, no synthetic failure or fix pass is claimed, and no chart,
generator, engine, release version, tag or asset is changed by this plan.

Scheduling checks: issue index regenerated; 38 existing issue/documentation checks
pass; 20 local links resolve; whitespace checks pass. This validates the plan's
tracking only, not implementation or chart accuracy.
