---
id: RULE-023
title: Implement Bowl Bound yardage factors
status: closed
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: 2026-11-01
tags:
- advanced-option
- scope-review
- wont-fix
links: []
commits: []
---

## Description

Advanced Rule IX yardage factors are excluded from gameplay. Both printed methods use power ratings and point spreads to modify yardage; the owner decided power ratings must not affect game outcomes. Reconsider only if the owner later approves a rating-independent yardage policy.

## Resolution / verification

- Decision (2026-11-01): defer both Full Feature and Simplified yardage factors. The rulebook's Advanced IX (printed pp. 29–31) ties them to point spreads, rating-based team factors, and score margin. Keep standard integer chart outcomes unchanged; no factor metadata, arithmetic, trace, or save behavior is added.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Owner chose to defer yardage factors because their rating/point-spread effects are not wanted in gameplay. Closed for this milestone; re-scope through a new ticket if that decision changes.
