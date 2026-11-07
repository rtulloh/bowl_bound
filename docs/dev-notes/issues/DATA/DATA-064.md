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

--- 2026-11-07 — owner accepts corrected paired visual review ---

Owner explicitly confirmed the corrected LSU/Ohio State charts looked good and
has captured a screenshot for their own release announcement. The required paired
visual review is accepted; proceed with full 116-team regeneration after the
storage prerequisite is met. Bind this approval to the final-pipeline-v2 pair
(receipt SHA-256 7fdf099f6ca167f95e33e458b7a310145a85c1a73a11444a54ae2a0e3ba9f176).
This is visual acceptance only. Full-cohort passing-cell/source/engine audits,
independent event/reference validation and final release gates remain required;
the ticket is not resolved by the screenshot or approval.
