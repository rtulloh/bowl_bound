---
id: IMPORT-016
title: Import and resolve defensive parenthesized Breakaway results
status: open
priority: Medium
milestone: '26'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- importer
- chart-semantics
- maysfootball
links: []
commits: []
---

## Description

A MaysFootball defense chart contains a parenthesized Breakaway result. Track the full
path from PDF cell extraction through normalized team data and engine resolution. The
engine must handle it as a defensive priority override without generalizing support to
other decorated named results. Do not include historical team names, coordinates, or
cell evidence in this ticket.

## Resolution / verification

- Use synthetic fixtures to verify PDF extraction preserves the `(B)` result and source provenance through normalization and team-file export/import.
- Verify the priority-chart handling lets defensive `(B)` override ordinary offensive results while offensive parenthesized yardage and penalties retain their precedence.
- Verify the winning defensive result triggers the offense's B-column reroll and records the consulted results in the engine trace.
- Import the affected private team into `seasons/` and confirm the result during local play-testing before closing the ticket.

The Mays 2007 rules separately define B as Breakaway, say the offense rolls its B column
when a play results in Breakaway, and define defensive parentheses as an override. The
published Priority Chart has no defensive B column. On 2026-10-30 the owner interpreted
this combination as a defensive breakdown that grants the offense a Breakaway reroll,
except where offensive parenthesized yardage or penalties control. See the [Mays 2007
rules](https://maysfootball.com/bbrules2007.pdf) and [Priority Chart](https://maysfootball.com/bbpriority.pdf).
The implementation is deliberately limited to this defensive result.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 23:20 ---
Synthetic tests now cover normalization, defensive placement, PDF extraction, team-file
round trip, priority exceptions and the offense's B-column reroll. The local private
source import and owner play-test confirmation are still required before closure.

--- 2026-10-30 21:45 ---
Owner requested explicit tracking for defense `(B)` cell parsing/extraction, priority
chart handling, and finding a real example to verify during play-testing. Existing
acceptance criteria now call out each step in that path.
