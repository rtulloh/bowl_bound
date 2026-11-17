# 2002 virginia-tech roster candidate

Sources: https://s3.us-east-2.amazonaws.com/sidearm.nextgen.sites/vatech.sidearmsports.com/documents/2018/4/25/sanfran02.pdf, https://hokiesports.com/football-media-guides-in-pdf-format

Retained source: `raw/vt-real.pdf`; SHA-256 `eb9bf13a2c2b25e1dd0272a26f2530ee780b51dd29e14aae116ceebe250b238e`. PDF pages: [12].

73 distinct names. Names and explicit positions only; no starter assignments, photos, biographies, or inferred returner roles. Composite positions map to each explicitly supported role, with per-role deduplication. Source ordering does not assert starter status.

Mapping: {"C": "ol", "CB": "db", "DB": "db", "DE": "dl", "DL": "dl", "DT": "dl", "FB": "rb", "FL": "wr", "FS": "db", "G": "ol", "HB": "rb", "ILB": "lb", "K": "k", "KR": "kr", "LB": "lb", "LG": "ol", "LT": "ol", "MLB": "lb", "NG": "dl", "NT": "dl", "OG": "ol", "OL": "ol", "OLB": "lb", "OT": "ol", "P": "p", "PK": "k", "PR": "kr", "QB": "qb", "RB": "rb", "RG": "ol", "RT": "ol", "S": "db", "SE": "wr", "SLB": "lb", "SS": "db", "T": "ol", "TB": "rb", "TE": "te", "WLB": "lb", "WR": "wr"}

Gaps: ["Official 2002 San Francisco Bowl guide roster; season-end bowl roster is not an assertion of identical availability every week.", "DS and ROV left unmapped; no inferred kick returners. Modern season/2002 page rejected as current content."]

Unmapped: [{"name": "Travis Conway", "position": "DS"}, {"name": "Michael Crawford", "position": "ROV"}, {"name": "Billy Hardee", "position": "ROV"}, {"name": "Ken Keister", "position": "DS"}, {"name": "D.J. Walton", "position": "ROV"}]

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md`: season-correct narration-only naming and generic fallbacks apply. No NFL data, behavior, or runtime dependency reused. This is private source curation, not production behavior.

Validated with ordinary `bowl_bound.roster.load_roster`. Machine receipt: `raw/virginia-tech-259-receipt.json`.
