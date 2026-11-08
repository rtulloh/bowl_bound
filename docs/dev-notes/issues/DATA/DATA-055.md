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
commits: [52c80b9]
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

--- 2026-11-07 — bounded recovery implementation checkpoint ---

The maintained observer now distinguishes routine two-draw kickoff returns from
F-return recovery, with externally pinned version-2 recovery-range evidence.
Fixed in-field own/opponent recoveries check field state, original credit owner,
called/resolved category, full boxes, score, actual draw/row closure and timing.
QT negative, zero and positive outcomes, QR loss and pass-origin B-F are forced
synthetic subjects. Legal recovery advances and tainted chains remain UNVERIFIED.

The exact reviewed implementation and synthetic controls are being integrated
with a matched baseline/Hard runner and strict replay. Read-only re-audit of the
34 frozen wrappers retains all 6,419 reports and independently closes the two
initial recovery refusals; it is not fresh candidate/full-event acceptance.
Five forced pending-save cases do not establish complete addressed save coverage
for that old panel. See the [implementation contract and limits](../../milestone-42-observer.md).

The reviewed `a9007c32` checkpoint adds bounded accepted-previous-spot
commitment and separate local ten-second timing checks. Its exact safe observer
closure is integrated without engine changes or research history. It passes
2,149 synthetic checks; independent review verifies source and retained evidence.
Read-only re-audit retains 6,419 reports, 121 live/122 report commitments and
39 local clock proofs; unsupported prior chains and 83 associated clock cases
remain unknown. The 1,042 old observed nonclock mandatory decisions have no
addressed save evidence. An opt-in addressed capture is a separate next step;
aggregate reconciliation and replay do not prove independent event ownership.
Full DATA-055 remains OPEN through candidate/benchmark and final acceptance.

--- 2026-11-07 — addressed-save conformance checkpoint ---

An opt-in development collector now records actual-object mandatory boundaries,
complete native saves and typed command links. Its explicit midpoint resume edge
preserves both original and restored addresses. Optional normal-clock
continuations remain separately counted and replayed. Synthetic mutations first
exposed missing final boundaries, duplicated command ownership, forged phase and
creator metadata, loose JSON types and foreign resume origins; the guards are
implemented without changing engine behavior or weakening the original checks.

The exact frozen source passes 33 synthetic checks, including a complete Hard
game with collection on/off exact save, view, journal and dice equality plus
native midpoint/final strict replay. That game accounts for 154 raw pending
boundaries through 153 continuations and one handoff. The 184 related capture
and runner checks pass. See [method and limits](../../pending-choice-capture.md).
No fresh historical panel is claimed; the old missing addresses, independent
causal football populations and full milestone acceptance remain outstanding.

--- 2026-11-07 — bounded punt / fair-catch integration ---

The reviewed `0e10dc50` safe delta adds independent fixed numeric punt landing,
actual receiver pending-menu and fair-catch terminal checks, with full excluded
credit, boxes, score, report freshness and separate local ten-second timing.
Period, marked, complex, return and unsupported prior chains remain unknown.
The retained 34-wrapper re-audit checks 394 pending creators, 194 report facts,
192 live fair catches and 192 local clock charges; two period continuations are
clock-unknown. All 6,419 reports remain retained. The terminal-handler census
links 5,320 reports and leaves 1,099 without authority; this is coverage, not an
accuracy percentage. The old 1,042 mandatory decisions still lack addressed saves.

The pre-period-followup cumulative passes 2,216 checks, with 177 final related
checks after two reproduced period guard failures. Integration passes 131
focused observer/CLI checks and twenty production files pass Pyright and Ruff.
See the [bounded contract](../../independent-pbp-punt-contract.md). This is not
fresh corrected-candidate game evidence or complete DATA-055 acceptance.
