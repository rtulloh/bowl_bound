---
id: DATA-007
title: Generator CLI tests collide with terminal tests during full collection
status: resolved
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: '2026-11-02'
closed-at: null
tags:
- tested
links: []
commits:
- 1f84e56
---

## Description

The focused generator suite passed, but full pytest collection imported the new chartgen/test_cli.py under the same module name as tests/test_cli.py because the new test directory lacked a package marker. Give generator tests a separate package namespace without skipping or renaming away terminal coverage.

## Resolution / verification

- Full collection includes both terminal CLI and generator CLI tests
- Run the full branch-coverage regression gate after the collection fix

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-02 21:11 ---
Full namespace-safe collection and regression at `1f84e56`:3,183 passed,92.06% branch-awarecoverage. No terminal or generator tests were skipped.
Owner play-test confirmation is unrecorded; ticket remains resolved, not closed.
