---
id: RULE-028
title: Add the Bowl Bound Razzle-Dazzle play
status: resolved
priority: Medium
milestone: '22'
created-at: 2026-11-01
resolved-at: 2026-11-01
closed-at: null
tags:
- advanced-option
links: [RULE-022, AI-033]
commits: [33a53da, 427b42e]
---

## Description

The owner approved Razzle-Dazzle under Advanced Rule I-1 for implementation on 2026-11-01. It is available as a callable play. The engine resolves it only when called and does not infer it from an ordinary chart result.

## Resolution / verification

- Implemented in `33a53da` after synthetic test-first cases failed on the missing RZDZ/WCRZDZ actions and resolution.
- The engine rolls defense first, offense second, awards ties to offense, and lets the winning side choose only from the permitted non-penalty chart results (or a penalty when all available results are penalties). It resolves the selected result through ordinary priority, supplemental, variable-yardage, penalty, turnover, timing, statistics, and trace paths.
- Advanced II behavior covers exact WCRZDZ as a no-dice incompletion and all other Wild Card guesses as incorrect; free and conditional eligibility retain their normal yardage effects. Run/Pass defense classifies the selected result, including option and quarterback results.
- Synthetic tests cover chooser ownership, ties, result limits, penalties, Wild Card eligibility, option/B/QR/QT, fumbles, save replay, API, CLI, and coaching estimates.
- Focused validation: 425 Python tests passed across engine, API, regulation, save, CLI, coaching, and resolution suites; Ruff check/format and `git diff --check` passed.
- Status is resolved pending owner play-test confirmation; do not close from automated tests alone.

## Comments

--- 2026-11-01 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-01 ---
Owner approved this implementation as part of the three-option scope in RULE-022.
Runtime behavior remains unavailable until the test-first implementation lands.

--- 2026-11-01 ---
Updated the API regression to complete the newly offered Razzle-Dazzle decision
before asserting the final play log; tested in `427b42e`.

--- 2026-11-03 ---
Owner play-test question: a human-called Razzle-Dazzle completed without a human
result prompt. Review confirmed the computer defense had the lower comparison
total, so it owned the chart-cell choice. A selected supplemental result then
required its normal further roll. This follows the approved chooser rule; a
human offensive result prompt is required only when offense wins or ties.
No gameplay implementation change or ticket-closure claim follows from this
clarification. Private team names, cell values and traces are omitted.

--- 2026-11-03 ---
[AI-033](../AI/AI-033.md) separately investigates CPU result-choice quality during
M33 owner review. Its first-legal-choice fallback is distinct from this ticket's
correct comparison/chooser ownership and engine follow-up procedures.
