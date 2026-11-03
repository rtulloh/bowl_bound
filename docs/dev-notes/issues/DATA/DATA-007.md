---
id: DATA-007
title: Generator CLI tests collide with terminal tests during full collection
status: open
priority: High
milestone: '34'
created-at: 2026-11-02
resolved-at: null
closed-at: null
tags:
- reproduced
links: []
commits: []
---

## Description

The focused generator suite passed, but full pytest collection imported the new chartgen/test_cli.py under the same module name as tests/test_cli.py because the new test directory lacked a package marker. Give generator tests a separate package namespace without skipping or renaming away terminal coverage.

## Resolution / verification

- Full collection includes both terminal CLI and generator CLI tests
- Run the full branch-coverage regression gate after the collection fix

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
