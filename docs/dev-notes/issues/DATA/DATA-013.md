---
id: DATA-013
title: Large cohort generation repeats source work and lacks resumable batches
status: open
priority: Medium
milestone: 34a
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags:
- testing
links: []
commits: []
---

## Description

Generating many teams repeats full-source provenance scans and hashes and the initial two-team runner has no safe cohort checkpoint contract. Expanded work must cache evidence and opponent fits once and resume immutable artifacts safely.

## Resolution / verification

- Use synthetic tests for cached deterministic bundles, bounded execution and tamper-safe checkpoint resume.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-03 phase-two regression ---
The two-process synthetic test caught use of the newer executor.map buffersize
API on supported Python 3.12. Replaced it with an explicit queue bounded to the
worker count; do not raise the Python floor or submit the whole slate at once.

--- 2026-11-03 complete-driver resume ---
The 138-case cumulative run exposed a CSV newline mismatch on full-driver resume:
writer CRLF bytes compared against universal-newline text. Use an explicit LF
CSV contract so exact comparison stays strict. The failing test retains the
full real-engine generation/train/held-out/coaching/resume path; no assertion
was weakened and no completed artifact is replaced.
