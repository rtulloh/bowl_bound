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
