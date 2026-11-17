# 2002 ohio-state roster candidate

Sources: https://ohiostatebuckeyes.com/documents/download/2023/5/20/2002_Roster.pdf

Retained source: `raw/osu.pdf`; SHA-256 `9b8b46ab764a49dca790d054dca22028edaaffe327e62caa2975a41459892fca`. PDF pages: [1, 2].

112 distinct names. Names and explicit positions only; no starter assignments, photos, biographies, or inferred returner roles. Composite positions map to each explicitly supported role, with per-role deduplication. Source ordering does not assert starter status.

Mapping: {"C": "ol", "CB": "db", "DB": "db", "DE": "dl", "DL": "dl", "DT": "dl", "FB": "rb", "FL": "wr", "FS": "db", "G": "ol", "HB": "rb", "ILB": "lb", "K": "k", "KR": "kr", "LB": "lb", "LG": "ol", "LT": "ol", "MLB": "lb", "NG": "dl", "NT": "dl", "OG": "ol", "OL": "ol", "OLB": "lb", "OT": "ol", "P": "p", "PK": "k", "PR": "kr", "QB": "qb", "RB": "rb", "RG": "ol", "RT": "ol", "S": "db", "SE": "wr", "SLB": "lb", "SS": "db", "T": "ol", "TB": "rb", "TE": "te", "WLB": "lb", "WR": "wr"}

Gaps: ["Visually transcribed alphabetical roster on PDF pages 1-2 (printed 20-21), not duplicated numerical reference. OCR errors corrected against rendered source, including Bryce Culver DE and Scott McMullen.", "P-K normalized to P/K; H and LS left unmapped. Explicit P/DB and P/K retained in both supported roles. No inferred returners or starters."]

Unmapped: [{"name": "Kyle Andrews", "position": "LS"}, {"name": "Andy Groom", "position": "H"}, {"name": "Jeremy Miller", "position": "LS"}, {"name": "Kurt Wilhelm", "position": "LS"}]

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md`: season-correct narration-only naming and generic fallbacks apply. No NFL data, behavior, or runtime dependency reused. This is private source curation, not production behavior.

Validated with ordinary `bowl_bound.roster.load_roster`. Machine receipt: `raw/ohio-state-194-receipt.json`.
