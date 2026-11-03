---
id: DATA-021
title: Expanded cohort regression has little hosted CI timing headroom
status: open
priority: Medium
milestone: 34a
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags:
- investigating
links: []
commits: []
---

## Description

The synthetic full regression at 83f2cc6 passed hosted Tests 41673619396, but the complete job took 44 minutes 25 seconds against a 45-minute limit. Python took 37 minutes 27 seconds and the browser step 6 minutes 18 seconds including setup. Thirty-five seconds of remaining budget makes ordinary runner variance a repeatability concern; this is not a failed test or evidence of a hung engine.

## Resolution / verification

- Profile the expanded synthetic cases and preserve meaningful real-engine, serialization, replay, and branch-coverage checks while establishing documented CI timing headroom; verify the final arrangement in a fresh hosted run. Do not hide failures, skip tests, or blindly widen a timeout without evidence.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-03 17:20 ---
Bounded synthetic profiling passed 98 generator cases in 113.37 seconds without
coverage. The two complete cohort driver cases took about 34 seconds each; a
passing cProfile case attributes most instrumented time to existing v10 chart
coaching evaluation. Compression and source parsing are not the dominant cost.
Engine and coaching behavior remain pinned and unchanged.

A new workflow contract test failed on the original single-job arrangement.
The proposed fix preserves the entire Python/coverage/lint/pip job and its
45-minute bound, while moving unchanged frontend/build/audit/real-browser commands
to a separate 15-minute job. Both source guards/checkouts use the same immutable
SHA. Native builds still wait for the entire reusable workflow. All 18 focused
workflow cases pass, including malformed source guards in both jobs. Final
cumulative/hosted verification remains pending; this ticket stays open.
