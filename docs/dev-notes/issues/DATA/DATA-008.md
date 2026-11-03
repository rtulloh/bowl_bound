---
id: DATA-008
title: Calibration uncertainty must cluster independent games
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

The first aggregator counted both sides of a game as independent core-metric clusters and each kick/return draw as an independent special-team cluster. Keep raw play/draw counts, but estimate uncertainty by complete game and report denominator-weighted effective game exposure. A synthetic two-game test reproduces the overcount without historical input.

## Resolution / verification

- Aggregate each metric within each independent game before estimating variance
- Record raw denominators, independent game clusters, Kish effective exposure and cluster-robust ratio standard errors
- Reanalyze retained pilot games without changing chart values, candidate losses or predeclared tolerances

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
