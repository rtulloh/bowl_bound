---
id: RULE-024
title: Define gameplay effects for Bowl Bound power ratings
status: closed
priority: Low
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: 2026-11-01
tags:
- scope-review
- wont-fix
links: []
commits: []
---

## Description

Advanced Rule VIII power ratings are distinct from importer metadata and local placeholder ratings. Decide whether ratings affect eligibility or outcomes and define the rule before any rating influences gameplay.

## Resolution / verification

- The owner decided power ratings are not important to gameplay. Keep ratings as chart metadata and optional point-spread/tracking information; do not use them to change eligibility or game outcomes.
- Advanced Rule VIII (printed pp. 28–29) describes point spreads, player rating points, cumulative ratings, and tracking the favorite. The owner declined those gameplay-adjacent scoring systems for this engine.
- No runtime behavior changed; no behavioral test was applicable. The rules profile and roadmap now record this scope decision.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Closed as wont-fix for engine behavior per the owner's statement that power rating
is not important to the game. The importer may retain rating metadata, but the
engine does not use it.
