---
id: RULE-039
title: Choose supported advanced rules before starting a game
status: open
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: null
tags:
- enhancement
- rules-profile
links: []
commits: []
---

## Description

Players need pregame selection for supported advanced Bowl Bound options. Advanced II/Wild Card defenses are currently enabled as a blanket default, even though players may want different rules profiles. Choices must be visible before a game starts, persisted with the save, and never altered during play.

## Resolution / verification

- Define the supported player-facing options and defaults, beginning with Advanced II/Wild Card defenses, against the approved rules profile.
- CLI and browser setup expose the same validated pregame choices; the engine receives explicit options rather than presentation-owned rule decisions.
- A save records the selected options and restores them exactly; existing saves have documented compatibility defaults.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
