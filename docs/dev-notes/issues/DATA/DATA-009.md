---
id: DATA-009
title: Return calibration needs semantic trace aliases and an exposed legal policy
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

The baseline-v1 training policy always fair-catches punts, leaving no punt-return exposure. The engine correctly labels interception/fumble return consultations turnover_return, while the observer matched only column names and omitted these draws. Use explicit engine-verified section aliases and a recorded current baseline policy with return choices; preserve prior reports and validate new candidates in a fresh seed domain. No chart values or football rules should compensate for missing observations.

## Resolution / verification

- Test normalized return draws including turnover/end-zone/reroll sections without parsing display tokens
- Retain an immutable legacy policy default in the shared runner and explicitly record generator training policy versions
- Use distinct paired training and held-out seeds for the renewed pilot; keep underexposed metrics failing

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 20:51 ---
The renewed training-only run showed standalone baseline-v10 deliberately omits
fourth-down kick preferences supplied by the chart-coaching wrapper. It produced
no punts, despite legal return choices. Interrupted before held-out validation and
retained all artifacts. Compose the existing situation-aware baseline offense with
current public-observation pending decisions, identically for both sides. New
regressions require actual punt and punt-return exposure plus saved replay.
