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
links: []
commits: []
---

## Description

Advanced Rule II lists Wild Card, run/pass, nickel-zone, and red-zone defenses, while the current engine exposes only its supported standard formations. The Wild Card procedure also has Priority Chart exceptions. Confirm each Bowl Bound procedure before implementation; do not copy Paydirt or NCAA rules.

## Resolution / verification

- Record the approved W-coded eligibility policy and printed outcomes for Wild Card, Run/Pass, Nickel Zone, and Red Zone.
- Offer only legal calls, resolve them in the engine through the Priority Chart, and retain rule-table rolls in traces without fabricating chart provenance.
- Cover exact defensive-die ranges, Play 5 option branches, conditional yardage doubling, QR/QT classification, Red Zone eligibility, API/CLI actions, and save replay with synthetic charts.
- Keep QR/QT pass classification limited to conditional-call correctness; fixed result cells remain keyed to the selected play and resolved SOP/BLP branch.
- Reject malformed saved privilege arrays, including nested JSON values, through the normal invalid-save error path.
- Full focused and cumulative regressions, formatting/lint checks, and the tested commit reference remain to be recorded before resolution.

## Comments

--- 2026-11-01 00:00 ---
Owner approved all four Advanced II defenses with the rulebook's W-coded default: W-coded teams receive free Wild Card and Run/Pass access; other teams may use them conditionally. Implementation and synthetic verification are underway. No play-test confirmation has been recorded.

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 13:52 ---
Rulebook review clarified that QR/QT affect whether a conditional Run/Pass guess is correct, while the defense result tables remain keyed to the play row (including an SOP/BLP branch changing Play 5 to Play 7/8). Add synthetic tests for both facts.
