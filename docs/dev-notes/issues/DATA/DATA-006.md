---
id: DATA-006
title: Generator private-output guard must normalize paths and protect evidence permissions
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

Review found that checking an unresolved private-data path component permits parent traversal to escape the ignored tree, and normalized evidence used default file permissions. Enforce resolved private paths, reject symlink parents and create normalized evidence owner-only.

## Resolution / verification

- Parent traversal and symlink destinations fail before output
- Normalized source files use mode 0600 and refuse overwrite

## Comments

--- 2026-11-02 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
