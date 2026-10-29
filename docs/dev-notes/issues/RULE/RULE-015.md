---
id: RULE-015
title: Trace labels mislabel the end-zone depth roll and the F_ENDZONE decline text
status: open
priority: Low
milestone: '22'
created-at: 2026-10-27
resolved-at: null
closed-at: null
tags: []
links: []
commits: []
---

## Description

_turnover_trace_entry renders the end_zone_depth white-face roll with cell text 'recovery', and _penalty_result_text describes an F_ENDZONE prepared result as a fumble with location still to be resolved although the location is fixed one yard into the end zone.

## Resolution / verification

- Depth roll labeled as depth; decline text states the fixed location; tests on the structured trace and decline label.

## Comments

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
