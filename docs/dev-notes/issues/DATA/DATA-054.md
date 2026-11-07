---
id: DATA-054
title: Parameterize actual-season runner and historical comparison by year
status: open
priority: High
milestone: 34a
created-at: 2026-11-06
resolved-at: null
closed-at: null
tags: [chart-generator, validation, planning]
links: [DATA-037, DATA-053, DATA-056, DATA-057, DATA-058, DATA-059]
commits: []
---

## Description

The requested runner accepts a selected year, conceptually run_full_season 2007, and uses that year's charts, fixtures, membership and explicit rules. Existing research implementation does not by itself certify a complete supported historical campaign.

## Resolution / verification

- Use actual conference and nonconference regular fixtures, keeping simulated postseason distinct from historical postseason results.
- Select declared year-appropriate conference/championship/BCS rules; refuse unsupported formats rather than inherit another year's format.
- Reject or explicitly label incomplete populations; never fabricate fixtures, substitute opponents or force historical winners.
- Always compare with eligible actual-season results; developer-chart comparison is additional evidence and is not applicable when references are absent.
- Verify runtime/coaching integration, document invocation and supported years, and renew affected receipts after corrections.

## Comments

--- 2026-11-07 — outstanding-question coverage review ---

Public-safe summary of the existing canonical research ticket; its ID and open status are preserved. Detailed source records and audit evidence remain private. Experimental Alpha 9 publication does not resolve this investigation. See [coverage review](../../chart-investigation-coverage.md).
