---
id: DATA-069
title: Research Nicely archive and chart-design methods for earlier historical seasons
status: open
priority: Low
milestone: 34b
created-at: 2026-11-17
resolved-at: null
closed-at: null
tags:
- research
- historical-seasons
- chart-generator
- archives
links: [DATA-037, DATA-072]
commits: []
---

## Description

Investigate the owner's leads about Dr. Thomas R. Nicely's Paydirt/Bowl Bound design articles, archived personal/faculty pages, and any surviving chart-development material. Determine whether verified methodology could support seasons before 2002 when detailed play-by-play is unavailable. Treat the supplied article descriptions, formula-transfer history, community mirrors and rights assertions as research leads, not established facts. This is exploratory follow-up, not a new current-release blocker.

## Resolution / verification

- Inventory Wayback captures of trnicely.net and the www/faculty Lynchburg hosts; record original URLs, exact capture timestamps, redirects and missing downloads. Preserve retrieved source bytes and SHA256 privately; publish only a concise source catalog and findings.
- Confirm magazine titles, authors, issue dates and printed/PDF page numbers from the scans, including Balancing Act (volume 2 number 4), Your SI Football Game (volume 3 number 1), and the claimed 1977 chart/rules article (volume 1 number 4). Separate chart-design evidence from gameplay variants and cross-set balancing advice.
- Locate actual equations, worksheets, source code or explanatory notes if available. Verify the claimed Matt Floray/Odd Man Games formula lineage from attributable primary evidence; distinguish confirmed recovery from community reports and inaccessible files.
- Record the precise scope and limitations of each authorship/license declaration. Nicely's own declaration is evidence of his stated intent, not automatic clearance of publisher-owned or third-party material; retain existing exact publication allowlists and require separate review/owner approval before redistribution.
- Assess an aggregate-statistics route for pre-2002 seasons: required inputs, missing variables, uncertainty, era/rules compatibility and independently testable calibration/held-out validation. Do not treat a published balancing modifier as a chart-generation algorithm or copy Paydirt rules into Bowl Bound.
- Post a recommendation with direct source links, verified versus unresolved claims and a bounded next experiment. Do not change the engine/generator, distribute historical charts or claim older seasons are supported as part of this research ticket.

## Comments

--- 2026-11-17 00:00 ---
Created with scripts/create_issue.py. Keep evidence public-safe.

--- 2026-11-17 — initial source recovery and research boundaries ---

Verified starting points:

- The Internet Archive availability API returns an HTTP-200 capture at
  [2019-09-06 14:03:52 UTC](https://web.archive.org/web/20190906140352/http://trnicely.net/#PDBB).
  The replay HTML was retrieved successfully. Its football section describes
  Nicely's development work during much of 1977–1995 and retirement in February
  1996. It contains his declaration concerning his own charts and developmental
  materials, acknowledges that his authority to make it was disputed, and
  expressly excludes other authors' charts. No chart/formula download links
  were found in that section. This does not establish that such files never
  existed elsewhere or were never archived.
- [OEIS preserves a PDF of the faculty homepage](https://oeis.org/A007053/a007053_1.pdf),
  printed October 28, 2021 from faculty.lynchburg.edu/~nicely/index.html.
  PDF pages 5–6 contain the football discussion and declaration. This is a
  useful readable mirror of the page, not a recovered development archive.
- [All-Star Replay volume 2 number 4](https://www.vftt.co.uk/files/AH%20All-Star%20Replay/All-Star%20Replay%20Vol%202%20No%204.pdf)
  is retrievable; indexed article text confirms Balancing Act: Playing Old
  Charts vs. New in Paydirt and Bowlbound, credited to Dr. Thomas R. Nicely.
  It discusses cross-generation chart compatibility and offensive increments.
  Confirm all exceptions and page references directly from the scan before
  considering any implications for our cross-season model.
- [All-Star Replay volume 3 number 1](https://www.vftt.co.uk/files/AH%20All-Star%20Replay/All-Star%20Replay%20Vol%203%20No%201.pdf)
  is retrievable; indexed text confirms Your SI Football Game by T. R. Nicely,
  on printed page 17 with continuation on page 20. Its described subject is
  customized equipment and play selection; this is not evidence that it
  discloses a statistical chart-generation formula.

Open leads and access limits:

- The volume 1 number 4 PDF downloads, but its alleged 1977 article/byline,
  exact publication dates and page references remain unverified in this pass.
  These local magazine PDFs have no useful pdfplumber text layer; visual review
  or bounded OCR is the next step. Search-index text is not a substitute for
  checking formulas, layout and qualifications on the actual pages.
- A bounded CDX query through 2019 returns 223 unique successful original URLs
  under trnicely.net; none has paydirt/bowl/sport/game in its URL. This is only
  one host/query scope, not proof of absence. Check alternate Lynchburg hosts,
  earlier captures, differently named downloads and outgoing references next.
- The faculty availability lookup requested near September 2019 returns
  [2020-11-27 20:09:39 UTC](https://web.archive.org/web/20201127200939/https://faculty.lynchburg.edu/~nicely/index.html).
  Do not present this as a 2019 faculty capture or infer when either site died.
- No formula archive, spreadsheet, community mirror contents or transfer to
  Matt Floray/Odd Man Games has yet been verified. The assertion that the
  exact algorithm became public decades later remains an open question.

Consulted local Paydirt docs/development.md,
docs/dev-notes/issues/RULE/RULE-022.md and
docs/dev-notes/source-season-coverage.md: an existing primary magazine citation
and the distinction between aggregate coverage and observed play distributions
are useful research inputs. Deliberately do not reuse NFL timing policy,
Paydirt implementation behavior or private team data. No runtime dependency,
chart calibration change or publication clearance is introduced.

Raw HTML/CDX/API responses and magazine scans stay ignored under
private-data/nicely-research-20261117/. Metadata/index checks are the appropriate
validation for this research-only addition; full application tests run on GitHub.
