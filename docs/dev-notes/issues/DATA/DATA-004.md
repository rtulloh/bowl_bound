---
id: DATA-004
title: Generator replay validation must accept legitimate blank chart traces
status: resolved
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: '2026-11-02'
closed-at: null
tags:
- tested
links: []
commits:
- 55f530d
---

## Description

The legacy coaching audit treats an empty rendered chart cell as missing trace evidence. A normalized NO_CHANGE cell intentionally has an empty canonical display token, so generated neutral defensive responses can falsely fail that audit despite complete roll evidence. Preserve blank semantics and validate replay through the local-season structural audit rather than changing chart values.

## Resolution / verification

- Complete synthetic generated games with genuine blank defensive cells
- Verify midpoint save/load continuation and full replay using structural trace validation

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 20:51 ---
Generated synthetic games retain genuine blank cells and pass structural trace validation, midpoint restoration and final journal replay. The generator uses this valid audit path; the separate legacy audit assumption is not declared repaired.
Focused cumulative gate at 9565398: 121 passed. Owner play-test confirmation remains unrecorded, so this ticket is not closed.
