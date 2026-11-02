---
id: RULE-040
title: Disable deferred Wild Card defense by default
status: closed
priority: High
milestone: '22'
created-at: 2026-11-01
resolved-at: null
closed-at: 2026-11-02
tags:
- reproduced
- rules-profile
links: []
commits: []
---

## Description

A normal terminal game currently enables Advanced II by default, allowing a defense with a printed W marker to call Free Wild Card despite the owner's decision to defer Wild Card defense. Preserve printed defense-chart markers as metadata, but do not expose or allow Wild Card until an explicitly enabled future rules-profile option exists.

## Resolution / verification

- New normal games leave Wild Card and other deferred Advanced II calls unavailable by default, even for a team with a W marker.
- Synthetic tests cover a W-marked team and verify normal terminal/save construction cannot offer or select a Wild Card defense.
- Chart marker import, legacy save parsing, and metadata provenance remain intact without treating markers as enabled gameplay privileges.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 00:00 ---
Play-test confirmation: a normal game repeatedly offered only the six standard
defenses (`A-F`) and did not expose Wild Card calls. The printed team marker
remained visible only as non-gameplay metadata.
