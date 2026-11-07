---
id: DATA-055
title: Complete independent full-game event accounting beyond local-runner invariants
status: open
priority: High
milestone: 42
created-at: 2026-11-06
resolved-at: null
closed-at: null
tags: [chart-generator, validation, planning]
links: [DATA-045, DATA-053]
commits: []
---

## Description

Aggregate scoring/stat/clock checks and engine-derived replay are useful but do not independently validate every event, statistic owner or rare branch. The Alpha 9 bounded observer explicitly leaves fumbled kickoff-return recovery cases unverified.

On 2026-11-07 the owner selected this high-priority ticket for [Milestone 42](../../milestone-42.md), alongside DATA-046 and the DATA-064 generator correction. Close the known observer gap with synthetic failures first, then use the corrected independent event accounting in the milestone's candidate and benchmark checks. This assignment does not change the ticket's acceptance requirements.

## Resolution / verification

- Use synthetic mutations for credited/voided statistics, side ownership, period attribution, consulted cells/dice/priority and called-versus-resolved branches.
- Audit each event independently and retain the first inconsistent event privately.
- Extend kickoff-return fumble coverage: distinguish two chart consultations from a legitimate third recovery draw; retain the existing failing reproduction and numeric/recovery controls.
- Force rare supported branches and pending-choice save/load; identify unsupported components explicitly instead of counting them as passes.
- Check QT terminal sacks, rushing plays, fumbles and completions against engine accounting rather than classifying a primary trigger as a completed pass.
- Keep baseline/Hard exposure separate and rerun affected frozen evidence after observer changes.

## Comments

--- 2026-11-07 — outstanding-question coverage review ---

Public-safe summary of the existing canonical research ticket; its ID and open status are preserved. Detailed source records and audit evidence remain private. Experimental Alpha 9 publication does not resolve this investigation. See [coverage review](../../chart-investigation-coverage.md).
