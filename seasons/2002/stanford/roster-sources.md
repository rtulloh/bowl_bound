# 2002 stanford roster candidate

Sources: https://gostanford.com/news/2002/10/12/washington-st-stats-9

Retained source: `raw/stanford-stats.html`; SHA-256 `9512adae5979d6ac09d58280a0a89ed6a72109f521735ff506132e6d900bb5be`. PDF pages: [].

22 distinct names. Names and explicit positions only; no starter assignments, photos, biographies, or inferred returner roles. Composite positions map to each explicitly supported role, with per-role deduplication. Source ordering does not assert starter status.

Mapping: {"C": "ol", "CB": "db", "DB": "db", "DE": "dl", "DEFENSE_LT": "dl", "DEFENSE_RT": "dl", "DL": "dl", "DT": "dl", "FB": "rb", "FL": "wr", "FS": "db", "G": "ol", "HB": "rb", "ILB": "lb", "K": "k", "KR": "kr", "LB": "lb", "LE": "dl", "LG": "ol", "LT": "ol", "MLB": "lb", "NG": "dl", "NT": "dl", "OG": "ol", "OL": "ol", "OLB": "lb", "OT": "ol", "P": "p", "PK": "k", "PR": "kr", "QB": "qb", "RB": "rb", "RE": "dl", "RG": "ol", "RT": "ol", "S": "db", "SE": "wr", "SLB": "lb", "SS": "db", "T": "ol", "TB": "rb", "TE": "te", "WLB": "lb", "WR": "wr"}

Gaps: ["PARTIAL: 22 explicit positions in Oct. 12, 2002 participation table; unpositioned reserves omitted. No K/P/KR verified. Atogwe given-name initial retained exactly; no inferred expansion.", "LT/RT in the DEFENSE section map to defensive line; offensive LT/RT map to offensive line. No starter assignments are inferred or stored."]

Unmapped: []

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md`: season-correct narration-only naming and generic fallbacks apply. No NFL data, behavior, or runtime dependency reused. This is private source curation, not production behavior.

Validated with ordinary `bowl_bound.roster.load_roster`. Machine receipt: `raw/stanford-24-receipt.json`.
