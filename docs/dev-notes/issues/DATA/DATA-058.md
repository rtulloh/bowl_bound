---
id: DATA-058
title: Attest actual observer origins and prefreeze lazy engine sources
status: open
priority: High
milestone: 34a
created-at: 2026-11-06
resolved-at: null
closed-at: null
tags: [chart-generator, validation, planning]
links: [DATA-054]
commits: []
---

## Description

Hashing expected local paths does not prove that loaded observer or engine modules came from those paths. Lazy imports can otherwise introduce unpinned runtime code after preflight.

## Resolution / verification

- Attest actual loaded engine and observer/tool origins and reject foreign-checkout modules.
- Freeze eligible engine/harness source identities before play and verify later-loaded modules against those pins.
- Reject mutations and unmeasured lazy modules with synthetic controls.
- Confirm integrated tests and independent review before resolution; do not equate a research checkpoint with final qualification.

## Comments

--- 2026-11-07 — outstanding-question coverage review ---

Public-safe summary of the existing canonical research ticket; its ID and open status are preserved. Detailed source records and audit evidence remain private. Experimental Alpha 9 publication does not resolve this investigation. See [coverage review](../../chart-investigation-coverage.md).
