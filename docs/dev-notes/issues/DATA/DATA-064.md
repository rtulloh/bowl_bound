---
id: DATA-064
title: Qualify pooled interception depths before assigning passing-play results
status: open
priority: High
milestone: 42
created-at: 2026-11-07
resolved-at: null
closed-at: null
tags: [chart-generator, source-conditioning, reproduced, validation]
links: [DATA-045, DATA-060]
commits: []
---

## Description

A community report asks whether Ohio State's Screen INT 44 is supported. The immutable Alpha 9 offense CSV contains that exact value at roll 18, as does Drop Back at roll 18. This is present in the data, not introduced by the visual chart.

Owner prioritized this as a required correction for the next milestone and release on 2026-11-07. Assigned to [Milestone 42](../../milestone-42.md), now targeting **1.0.0** per the owner's subsequent direction, superseding Alpha 10. The next release must satisfy the documented correction and plausibility gate.

There is a real 44-yard interception depth in the team's 2007 source evidence. The [official Ohio State–Purdue play-by-play](https://ohiostatebuckeyes.com/documents/download/2023/6/30/2007-6-Purdue.pdf#page=18) records a second-and-seven pass from Purdue's 46 intercepted at Purdue's 2, with no return. Neither that report nor the normalized event identifies the designed play as Screen. The historical depth is supported; its assignment to Screen is not established by that event.

The generator's _int_locations collects known team interception spots without conditioning on the called family. generate_team passes that common collection to each passing column. A real value in the pooled population therefore cannot establish that a particular passing play has that conditional depth distribution. This extends beyond a fixed-depth/repeated-stripe visual issue.

## Resolution / verification

- Add synthetic controls first: unidentified long-pass interceptions must not become claimed observed Screen-depth evidence; known screen, known deep-call, sparse and all-unknown populations retain correct provenance.
- Audit offense and defense across all teams/calls for unsupported conditional depths and related pooling assumptions, not just the reported cell.
- Propose a declared source-informed conditional depth policy for each passing call, with conservative authored priors where designed calls are unobserved. Preserve the distinction between observed and modeled support.
- Review physical INT mass, Priority, catch location, end-zone/touchback/return consequences, unknown support and team calibration together. Do not silently clip depths, relabel the number as return yards, shuffle cells cosmetically or change event budgets to conceal the mismatch.
- Validate the chosen model on LSU/Ohio State before broader regeneration; use private developer references as diagnostics without treating them as generation targets.
- Bind corrected ordinary CSV/API/rendered identities and rerun affected probability, mechanics and source-fit evidence. Record integrated tested commits and play-test confirmation before resolution/closure.
- After the final INT correction, run the [whole-cohort passing-cell audit](../../milestone-42.md#whole-cohort-passing-cell-audit) on the actual release candidate: all offensive and defensive passing calls and relevant dependent pass outcomes. Check call-specific interception depths, extreme gains/losses, special-result semantics and suspicious repeated tokens/families/colors; preserve exact weighted event accounting. Report every flagged exception with evidence and a disposition, not just aggregate pass counts. Unchecked, unsupported or unparseable cases cannot silently pass.

## Comments

--- 2026-11-07 — community report investigated ---

Read-only checks confirm the released CSV equals the immutable Alpha 9 tag. The historical 44 is catch depth, not return distance; return distance is zero. This investigation does not establish that a 44-yard Screen interception occurred. No chart/model/runtime change or release mutation was made.

Consulted Paydirt DATA-040's source-conditional and physical-mass review requirements. Adapt that separation of observed support from authored allocation; do not import its NFL model, weights, source data or runtime dependencies. Private source identities and the detailed trace are retained locally.

--- 2026-11-07 — paired authored prototype implemented; acceptance pending ---

The [numerical policy and independent gate](../../authored-interception-depth-policy.md)
now distinguish explicit designed-call observations from unidentified/generic-deep
passes, retain missing locations as unknown, and encode call-specific authored
priors without moving any INT slots. Synthetic shared-pool failures preceded the
generator repair; independent encoding mutations reject a supported but collapsed
distribution. Ordinary paired CSVs reload with all nondepth football facts intact
and agree with API/browser cells. Both possession sides and bounded field/return
consequences have separate private evidence.

The prototype is awaiting the required LSU/Ohio State owner visual review.
All-cohort, shape-sensitivity, final execution/source identities and full
benchmark/observer/regression requirements remain outstanding. No historical
conditional-fit approval or ticket resolution is claimed.

--- 2026-11-07 — identity and canonical-allocation review ---

Two synthetic failures exposed effective-strength and export identities retaining
the strength-four hash during another execution. The correction binds the actual
execution contract and requires the matching export identity. A separate tied
mixed-weight counterexample exposed a lost canonical witness; a two-pass allocator
and stricter exhaustive gate now verify the complete objective and row ordering.
All changed expectations are documented in the policy note. The paired
strength-four ordinary files remain byte-identical after these fixes.

The final accepted 1.0.0 handoff must include fresh Ohio State offense/defense
screenshots from that actual candidate, with corrected Screen depths visible and
CSV/API/cell identity evidence. Exploratory preview images do not satisfy this
deliverable. The owner will handle any external posting.

The actual legacy post-calibration ordinary export reproduced a synthetic Screen
INT outside its declared conditional support (meaningful RED). The maintained
finalizer now applies conditional depths after that completed calibration, then
requires independent target-weight/finite-encoding checks before export and after
ordinary reload. The regression passes through the finalizer; parent incidence
and all nondepth facts remain checked. This implements the final data-producing
boundary; paired conditioned-source files, owner review, the approved full cohort
and final release acceptance are still required. Ticket remains OPEN.

--- 2026-11-07 — actual paired broad passing-cell census ---

The [census contract](../../passing-cell-audit-method.md) now covers the four
passing calls, Option and B/QR/QT dependencies, plus all-family repeated
token/flag/color patterns. One meaningful synthetic RED shows why the older
depth-only gate cannot qualify extreme pass gains; fourteen controls and 87
related checks pass. The actual final-pipeline pair has 780 scoped cells,
1,260 cluster cells and 120 primary contexts with 18,000 independent Priority
address checks. No fixed gain falls outside the declared conditioned source
diagnostic envelopes. Numeric unidentified-call support, conditional terminal
paths and repeated-column dispositions remain explicit unresolved components;
this is not historical or full passing-plausibility approval. All 76 consumed
identities stayed unchanged. Full-cohort generation/audit remains held for owner
paired review; DATA-064 remains OPEN.
--- 2026-11-07 — owner accepts corrected paired visual review ---

Owner explicitly confirmed the corrected LSU/Ohio State charts looked good and
has captured a screenshot for their own release announcement. The required paired
visual review is accepted; proceed with full 116-team regeneration after the
storage prerequisite is met. Bind this approval to the final-pipeline-v2 pair
(receipt SHA-256 7fdf099f6ca167f95e33e458b7a310145a85c1a73a11444a54ae2a0e3ba9f176).
This is visual acceptance only. Full-cohort passing-cell/source/engine audits,
independent event/reference validation and final release gates remain required;
the ticket is not resolved by the screenshot or approval.

--- 2026-11-07 — corrected full cohort and broad passing census ---

The owner-accepted final pipeline now produces all 116 approved historical
teams and the unchanged fictional samples. Independent ordinary-file review
verifies all 97,440 historical records, all nondepth facts/incidence/metadata,
789 corrected locations and every conditional encoding column. The complete
[passing census](../../passing-cell-audit-method.md#frozen-full-cohort-checkpoint)
adds 45,240 scoped cells, 73,080 all-family cluster cells and 1,044,000 independent
Priority checks. All 31 diagnostic source-envelope exceptions receive private
per-address dispositions and weighted outcomes; negative defensive contributions
are not automatically constrained by whole-play source minima. Repeated-column
groups and unsupported historical/terminal components stay explicit. No cap,
shuffle, full source-fit claim or ticket resolution is introduced. Final observer,
matched games, regression and release acceptance remain required.

--- 2026-11-07 — corrected data integrated; final acceptance pending ---

All approved corrected ordinary files now occupy the actual release input paths,
with refreshed manifest hashes and schema-three expectations. The public gate
preserves original incidence/nondepth budget checks and independently requires
canonical conditional-depth encoding across all 28 passing columns per team.
Seventeen new synthetic controls and 70 existing audit controls pass, including
unknown/declaration/import-binding refusals; independent source review and a fresh
actual-file audit pass all 116 teams. This is the data correction and maintained
release gate, with authored assumptions explicit. It does not certify historical
call fit. Fresh full-game/save/reference evidence, final regression, release
integration and fresh accepted-candidate screenshots remain pending; ticket stays
OPEN.
