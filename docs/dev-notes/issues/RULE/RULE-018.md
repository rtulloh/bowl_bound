---
id: RULE-018
title: Second-half kickoff can repeat the opening kicker
status: resolved
priority: High
milestone: '30'
created-at: 2026-10-31
resolved-at: 2026-10-31
closed-at: null
tags:
- reproduced
links: []
commits: [5b755cf]
---

## Description

The halftime chooser can independently select kick or receive, allowing the same team to kick off both halves. Basic V-3's second-half choice is the kick type for the team already assigned to kick, not a choice of which team receives. The expected order is reciprocal: the opening kicker receives, and the opening receiver kicks. Onside kicks are unsupported, so schedule the normal kickoff automatically without another choice.

## Resolution / verification

- Synthetic tests cover both opening toss decisions and prove second-half kickoff assignments are always reciprocal.
- Halftime offers no kick/receive choice and advances to the scheduled kickoff with Q3 clock and timeout state correct.
- Pre-M30 halftime saves resume at kickoff; old choices replay only when consistent with the fixed order.
- Tested in commit `5b755cf`: 2,606 Python tests passed with 93.29% branch-aware coverage; focused tests 190 passed; issue tracker tests 18 passed; Ruff checks passed; frontend tests 120 passed; production build passed; real-engine Playwright tests 33 passed.
- Playwright emitted the environment warning that `NO_COLOR` is ignored when `FORCE_COLOR` is set. No tests were skipped.

Keep resolved until owner play-test confirms the fix; then add a play-test confirmation and close.

## Comments

--- 2026-10-31 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-31 07:26 ---
Resolved in `5b755cf` after the full Python, frontend, build and browser regression
gates passed. Awaiting owner play-test confirmation before closure.
