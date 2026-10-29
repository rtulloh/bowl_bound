---
id: RULE-014
title: Return penalty acceptance refused with a false end-zone reason and inconsistent
  with kick returns
status: open
priority: Medium
milestone: '22'
created-at: 2026-10-27
resolved-at: null
closed-at: null
tags: []
links: [RULE-003]
commits: []
---

## Description

session disables return:accept whenever enforce_return_penalty raises and always reports end-zone enforcement is not yet supported, including an in-field interception return reaching a touchdown with a foul by the non-returning team. special_teams._accepted_return enforces the same foul from the real end-zone coordinate with touchback or safety fallback, so turnovers and special teams implement VI-4(C)(vi) differently.

## Resolution / verification

- One shared enforcement path for turnover and kick returns; accurate disable reasons; tests for fouls by each side on in-field and end-zone returns ending in the field, in the end zone and as touchdowns.

## Comments

--- 2026-10-27 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
