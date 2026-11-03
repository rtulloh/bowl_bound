---
id: DATA-008
title: Calibration uncertainty must cluster independent games
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
- c0cbf10
---

## Description

The first aggregator counted both sides of a game as independent core-metric clusters and each kick/return draw as an independent special-team cluster. Keep raw play/draw counts, but estimate uncertainty by complete game and report denominator-weighted effective game exposure. A synthetic two-game test reproduces the overcount without historical input.

## Resolution / verification

- Aggregate each metric within each independent game before estimating variance
- Record raw denominators, independent game clusters, Kish effective exposure and cluster-robust ratio standard errors
- Reanalyze retained pilot games without changing chart values, candidate losses or predeclared tolerances

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 20:51 ---
Synthetic unequal-exposure complete-game clusters verify raw counts, Kish effective exposure and cluster-robust ratio standard-error math. Retained original pilot games were reanalyzed privately; candidate selection and tolerances were not changed.
Focused cumulative gate at 9565398: 121 passed. Owner play-test confirmation remains unrecorded, so this ticket is not closed.
