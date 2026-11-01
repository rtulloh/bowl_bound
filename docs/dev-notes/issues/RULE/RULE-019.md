---
id: RULE-019
title: Define and implement Bowl Bound Advanced II defensive options
status: open
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- advanced-option
- reopened
links: []
commits: [e0081ac, 2bea18e]
---

## Description

Advanced Rule II lists Wild Card, run/pass, nickel-zone, and red-zone defenses, while the current engine exposes only its supported standard formations. The Wild Card procedure also has Priority Chart exceptions. Confirm each Bowl Bound procedure before implementation; do not copy Paydirt or NCAA rules.

## Resolution / verification

- Record the approved W-coded eligibility policy and printed outcomes for Wild Card, Run/Pass, Nickel Zone, and Red Zone.
- Offer only legal calls, resolve them in the engine through the Priority Chart, and retain rule-table rolls in traces without fabricating chart provenance.
- Cover exact defensive-die ranges, Play 5 option branches, conditional yardage doubling, QR/QT classification, Red Zone eligibility, API/CLI actions, and save replay with synthetic charts.
- Keep QR/QT pass classification limited to conditional-call correctness; fixed result cells remain keyed to the selected play and resolved SOP/BLP branch.
- Reject malformed saved marker arrays, including nested JSON values, through the normal invalid-save error path.
- Rename the persisted team metadata key and matching metadata model property from `privileges` to `defense_chart_markers`; keep legacy team bundles and saves readable.
- Test-first evidence: all nine initial synthetic Advanced II cases failed before the engine exposed these calls. Synthetic coverage now checks eligibility, every defensive roll total, Play 5 branches, QR/QT and Screen classification, Red Zone limits, API/CLI actions, save replay, and malformed marker data.
- Tested commits: `e0081ac` implements Advanced II; cumulative regression was run on `2bea18e`.
- Validation: 2,904 Python tests passed at 92.76% branch-aware coverage; 35 focused Advanced II tests; 119 frontend tests; production build; npm audit with zero vulnerabilities; 33 real-engine browser tests; Ruff lint/format, pip check, and 18 issue-index tests all passed.
- Automated verification is complete. Owner play-test confirmation remains before closure.

## Comments

--- 2026-11-01 00:00 ---
Owner approved all four Advanced II defenses with the rulebook's W-coded default: W-coded teams receive free Wild Card and Run/Pass access; other teams may use them conditionally. Implementation and synthetic verification are underway. No play-test confirmation has been recorded.

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 13:52 ---
Rulebook review clarified that QR/QT affect whether a conditional Run/Pass guess is correct, while the defense result tables remain keyed to the play row (including an SOP/BLP branch changing Play 5 to Play 7/8). Add synthetic tests for both facts.

--- 2026-11-01 14:05 ---
Resolved after synthetic tests and cumulative regression passed on `2bea18e`. The new defense-result tests distinguish conditional guess classification from fixed play-row results. Kept open for owner play-test confirmation.

--- 2026-11-01 ---
Reopened by owner request to rename the persisted team metadata marker field to
`defense_chart_markers`, now that the rulebook meaning of W is confirmed. Preserve
legacy bundle and save reads while writing the explicit marker name.
