---
id: DATA-020
title: Historical cohort runs need a retained-artifact storage budget
status: open
priority: High
milestone: 34a
created-at: 2026-11-03
resolved-at: null
closed-at: null
tags: []
links: []
commits: []
---

## Description

A pre-run filesystem check found limited free storage relative to the proposed multi-candidate historical cohort run. Full engine reports and failed seeds must remain retained. Measure representative artifacts, record the run storage estimate, and reject or bound a run before exhausting the destination; never silently discard evidence or delete existing private history.

## Resolution / verification

- A source-frozen preflight records available bytes and conservative retained-report estimates; bounded or compressed immutable artifacts preserve checksums and resume verification; synthetic tests cover insufficient storage without starting engine work; historical runs remain gated on the concrete slate review and available capacity.

## Comments

--- 2026-11-03 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.


Parent approved deterministic streaming gzip and a conservative capacity preflight
under this milestone. Source was kept frozen until the e74dc06 full regression
finished; that gate is not claimed to validate the new storage implementation.
New synthetic cases first failed for the absent interface, then passed initial
round-trip/resume/tamper/truncation/early-capacity checks. Complete artifacts and
semantic checksums remain retained; prior private outputs are unchanged.

Additional red/green corruption control: a valid gzip stream containing a JSON
list raised AttributeError at retained-contract access. It now rejects that
non-object root as a clear contract error without altering the artifact.
Cumulative 172 cases passed before this final guard; corrected-source focused
51 cases, repository lint/format, dependency consistency and whitespace checks
passed. Full changed-source acceptance and measured historical pilot storage
remain pending; this ticket stays open.

--- 2026-11-03 17:10 ---
Tested storage source commit: `83f2cc61c4fa845833560a51faf2e62fa0cf0821`.
Local full regression passed 3,491 cases / 91.54% branch-aware coverage; exact-source
hosted Tests 41673619396 passed 3,491 Python cases / 91.53%, 130 frontend cases,
38 real-engine browsers and zero audit vulnerabilities. Full logs remain private.
Measured historical pilot storage still awaits the concrete-slate review and run;
the ticket remains open rather than claiming that unperformed evidence.
