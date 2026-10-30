---
id: IMPORT-005
title: Redact unexpected ValueError messages at the PDF CLI boundary
status: resolved
priority: High
milestone: '25'
created-at: 2026-10-30
resolved-at: 2026-10-30
closed-at: null
tags:
- review
- reproduced
- privacy
links:
- IMPORT-007
- IMPORT-009
commits: [0f050eb]
---

## Description

Confirmed on main ab4c70e and draft 2822c3b using a synthetic exporter that raises ValueError("SYNTHETIC_PRIVATE_SENTINEL"). The sentinel appears verbatim on stderr. Main prints every ValueError/OSError; draft _failure_reason returns str(error) for every ValueError and error.strerror for every OSError. Those categories include parser/decoder failures whose messages are not controlled by this project. The existing KeyError and ordinary FileNotFoundError tests do not establish the documented no-chart-text guarantee. The draft roadmap already identifies this blocker.

## Resolution / verification

- Use explicit project-owned safe error types or reason codes whose messages are constructed without source text. Give every other exception a fixed public-safe message; use a safe errno mapping rather than arbitrary OSError.strerror.
- Test generic ValueError, UnicodeDecodeError, parser exceptions and custom OSError messages containing a synthetic sentinel, path and newline in single-file, batch, inspection and output-error paths.
- Retain useful approved validation/install hints and nonzero exit status; batch processing must continue for independent documents. Test stdout and stderr together.

Implemented and committed on `wip/5d-batch-import` as `0f050eb`.

- Baseline: seven new assertions failed because single-file and batch paths printed arbitrary `ValueError` and `OSError` messages, including paths and newline-injected text. The generic parser exception already used the fixed fallback.
- The CLI now prints only typed project-authored messages, a safe errno mapping, or a fixed unexpected-error message. Inspection errors with local paths are path-free; exporter validation no longer copies normalization or model exception text into user-visible errors.
- Added synthetic coverage for `ValueError`, `UnicodeDecodeError`, parser exceptions and custom `OSError` details across inspection, batch export and write failures. Batch processing still continues for unrelated PDFs. Tests capture stdout and stderr together.
- Existing validation guidance and the optional PDF dependency install hint remain visible.
- Verification: `tests/test_pdf_*.py tests/test_export_hardening.py` — 194 passed; Ruff check, Ruff format check and `git diff --check` passed.
- Final integration onto the active Milestone 25 branch remains tracked by IMPORT-009.

## Comments

--- 2026-10-30 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-10-30 00:00 ---
The CLI now redacts untrusted exception details and the regression tests pass in `0f050eb`.
Final integration remains tracked by IMPORT-009; do not close before the integrated Milestone
25 regression gate passes.
