---
id: RULE-018
title: Second-half kickoff can repeat the opening kicker
status: open
priority: High
milestone: '30'
created-at: 2026-10-31
resolved-at: null
closed-at: null
tags:
- reproduced
links: []
commits: []
---

## Description

The halftime chooser can independently select kick or receive, allowing the same team to kick off both halves. Basic V-3's second-half choice is the kick type for the team already assigned to kick, not a choice of which team receives. The expected order is reciprocal: the opening kicker receives, and the opening receiver kicks. Onside kicks are unsupported, so schedule the normal kickoff automatically without another choice.

## Resolution / verification

- Synthetic tests cover both opening toss decisions and prove second-half kickoff assignments are always reciprocal.
- Halftime offers no kick/receive choice and advances to the scheduled kickoff with Q3 clock and timeout state correct.
- Existing saved-game behavior is handled deliberately and covered by focused replay tests.
- Rules documentation, milestone notes, and the generated issue tracker describe the corrected behavior.
- Focused and cumulative project checks pass; retain resolved status until owner play-test confirms the fix.

## Comments

--- 2026-10-31 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
