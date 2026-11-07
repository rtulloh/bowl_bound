---
id: DATA-057
title: Reject ambiguous fixture phases and bind primary overrides
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

Synthetic review found ambiguity between raw regular/postseason labels, primary overrides and conference-title profile IDs. Some corrections exist in the research lineage; final integration and acceptance must be verified before closing.

## Resolution / verification

- Require explicit supported source phases and preserve raw and effective classification plus primary evidence.
- Apply phase and classification together and reject contradictory override/profile authorities before games run.
- Cover both regular-to-postseason and postseason-to-regular cases synthetically.
- Record the integrated tested commit, independent review and applicable cumulative checks before resolution.

## Comments

--- 2026-11-07 — outstanding-question coverage review ---

Public-safe summary of the existing canonical research ticket; its ID and open status are preserved. Detailed source records and audit evidence remain private. Experimental Alpha 9 publication does not resolve this investigation. See [coverage review](../../chart-investigation-coverage.md).
