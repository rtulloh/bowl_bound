---
id: DATA-048
title: Require complete coverage and failures in statistical readiness decisions
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

An independent synthetic review found that a statistical helper can omit teams without eligible games and report success while a separate mechanics check fails. Partial diagnostic success cannot establish complete chart readiness.

## Resolution / verification

- Demonstrate missing-fixture, empty-team and failed-game cases with synthetic controls before changes.
- Require declared team/fixture/repetition coverage, accepted mechanics and eligible source metrics together.
- Report missing or insufficient evidence as UNVERIFIED; preserve failures and prevent pooled means from hiding an individual bad team.
- Freeze precision and equivalence criteria before campaigns and account for game-level dependence; do not tune thresholds after observing failures.

## Comments

--- 2026-11-07 — outstanding-question coverage review ---

Public-safe summary of the existing canonical research ticket; its ID and open status are preserved. Detailed source records and audit evidence remain private. Experimental Alpha 9 publication does not resolve this investigation. See [coverage review](../../chart-investigation-coverage.md).
