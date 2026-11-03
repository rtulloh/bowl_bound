---
id: DATA-010
title: Training reception override must preserve production clock choices
status: open
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- reproduced
links: []
commits: []
---

## Description

The new pending-decision override also intercepted clock_choice. Engine clock prompts omit normal timing because the production coaching adapter supplies that implicit option and side ownership. Bypassing it exhausted timeouts and selected clock:spike repeatedly. Keep the training override out of clock_choice entirely and retain all interrupted pilot evidence; never adjust chart strengths to offset the harness mistake.

## Resolution / verification

- A synthetic complete composed-policy game contains no clock:spike selections or Spike reports
- Punts and punt returns still occur and midpoint/final replay remains exact
- Fresh training and held-out seed domains replace the interrupted training-only run

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
