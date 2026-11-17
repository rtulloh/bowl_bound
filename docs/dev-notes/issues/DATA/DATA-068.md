---
id: DATA-068
title: Separate blocked-punt statistical yards from physical recovery location
status: open
priority: High
milestone: 34a
created-at: 2026-11-16
resolved-at: null
closed-at: null
tags:
- reproduced
- chart-generator
links: [DATA-066]
commits: []
---

## Description

The generator currently uses Event.yards both for ordinary punt distance and the BK recovery-location suffix. The runtime consumes BK distance as physical movement from the snap to initial recovery. A provider can credit a blocked punt as zero statistical yards while its explicit initial recovery spot is behind the line. Synthetic example: fourth down at own 40, block recovered at own 25, then advanced five yards; BK location is -15, independent of statistical punt credit or the later advance. The released 2007 catalog contains BK 0 tokens; their correctness needs event-level review rather than assuming statistical zeros locate recoveries.

## Resolution / verification

- Represent initial blocked-punt recovery movement separately from statistical punt credit and subsequent recovery advance.
- Use only explicit or independently corroborated physical source evidence, preserving unknowns and conflicts.
- Add synthetic regression coverage and review the existing released cohort without overwriting immutable release evidence.

## Comments

--- 2026-11-16 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-16 18:25 ---

Synthetic regressions first demonstrated 15 failures. The implementation adds
`Event.blocked_kick_yards`, normalized schema 6, explicit initial-distance
narrative parsing, and evidence-checked adjudication of the new field. Punt
generation now consumes only physical initial movement for BK suffixes and reports
known/unknown location counts; it refuses statistical-credit substitution. Existing
schemas remain readable with this fact unknown. The existing negative-location
fixture now states statistical credit and physical movement separately and retains
its negative-location assertion. The first focused source/adjudication suite
passed 39 tests; broader validation is in progress.

The runtime attestation correctly rejected the modified generator/source modules
before its reviewed source inventory was refreshed. Only `evidence.py`,
`generate.py` and `source.py` byte identities changed in that inventory; the engine,
coaching configuration, parent allocator and released chart pins remain unchanged.
New research-contract identity:
`e1becc11f8f0b041f0009b945895e4df9497691e616f3134f71535d1a8119f27`.
The prior identity and its receipts remain in the recovery record. Uncommitted work
does not resolve this issue; the 2007 event-level review remains outstanding.

--- 2026-11-16 18:32 ---

The follow-up models known team physical locations, otherwise known blocked-punt
locations from supplied live league evidence, independently of each team's block
rate. Synthetic controls first fail for missing pooling, own-evidence precedence
and no-block-rate preservation, then pass. A further two controls reject bare
zero-credit narratives and separate recovery clauses as physical movement. Explicit
physical zero remains valid alongside negative/positive locations. The final
research-contract identity is
`7a4988db3f13bf39623dfdf28fbcd633c14ed00acff9d31ccf727c669dd9fa9a`.

The private 2002 full candidate now generates all 55 selected teams. Its four
known physical locations are sparse evidence: 34 teams use an explicit league
conditional-location pool, three use own evidence and 18 have no observed blocks.
Individual unknowns remain unknown; neither source qualification nor a 2007
event-level review is implied. No released chart pin changed. Final tests and
candidate receipts are recorded in the linked DATA-066 recovery notes.
