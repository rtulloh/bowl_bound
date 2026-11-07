---
id: DATA-049
title: Add source-supported field-goal accuracy qualification
status: open
priority: Medium
milestone: 34a
created-at: 2026-11-05
resolved-at: null
closed-at: null
tags: [chart-generator, validation, planning]
links: [DATA-045]
commits: []
---

## Description

Existing bounded kick diagnostics do not establish source-supported field-goal accuracy. Overall percentage alone can hide errors in distance-conditioned behavior and differences in kick selection.

## Resolution / verification

- Define source-supported pre-kick geometry, charged-attempt denominators, selection-policy scope, missing values and uncertainty.
- Use synthetic controls with equal pooled success but different distance-conditioned results to reject a corrupted chart.
- Qualify relevant blocked, fumble, penalty, return and PAT branches through the actual engine.
- Keep diagnostic results separate from a frozen numerical acceptance contract; retain unsupported populations as unknown.

## Comments

--- 2026-11-07 — outstanding-question coverage review ---

Public-safe summary of the existing canonical research ticket; its ID and open status are preserved. Detailed source records and audit evidence remain private. Experimental Alpha 9 publication does not resolve this investigation. See [coverage review](../../chart-investigation-coverage.md).
