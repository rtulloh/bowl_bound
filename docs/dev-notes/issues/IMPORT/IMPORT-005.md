---
id: IMPORT-005
title: Redact unexpected ValueError messages at the PDF CLI boundary
status: open
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: null
closed-at: null
tags:
- review
- reproduced
- privacy
links:
- IMPORT-007
- IMPORT-009
commits: []
---

## Description

Confirmed on main ab4c70e and draft 2822c3b using a synthetic exporter that raises ValueError("SYNTHETIC_PRIVATE_SENTINEL"). The sentinel appears verbatim on stderr. Main prints every ValueError/OSError; draft _failure_reason returns str(error) for every ValueError and error.strerror for every OSError. Those categories include parser/decoder failures whose messages are not controlled by this project. The existing KeyError and ordinary FileNotFoundError tests do not establish the documented no-chart-text guarantee. The draft roadmap already identifies this blocker.

## Resolution / verification

- Use explicit project-owned safe error types or reason codes whose messages are constructed without source text. Give every other exception a fixed public-safe message; use a safe errno mapping rather than arbitrary OSError.strerror.
- Test generic ValueError, UnicodeDecodeError, parser exceptions and custom OSError messages containing a synthetic sentinel, path and newline in single-file, batch, inspection and output-error paths.
- Retain useful approved validation/install hints and nonzero exit status; batch processing must continue for independent documents. Test stdout and stderr together.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.
