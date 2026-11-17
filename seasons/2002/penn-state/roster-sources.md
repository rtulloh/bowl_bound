# 2002 penn-state roster candidate

Sources: https://fightingillini.com/news/2002/11/2/Penn_State_18_Illinois_7

Retained source: `raw/psu-illinois.html`; SHA-256 `17e24588ad708dbb6a43ec3c75f6589d9589e3f3303353e4082da7370fd6725b`. PDF pages: [].

21 distinct names. Names and explicit positions only; no starter assignments, photos, biographies, or inferred returner roles. Composite positions map to each explicitly supported role, with per-role deduplication. Source ordering does not assert starter status.

Mapping: {"C": "ol", "CB": "db", "DB": "db", "DE": "dl", "DEFENSE_LT": "dl", "DEFENSE_RT": "dl", "DL": "dl", "DT": "dl", "FB": "rb", "FL": "wr", "FS": "db", "G": "ol", "HB": "rb", "ILB": "lb", "K": "k", "KR": "kr", "LB": "lb", "LE": "dl", "LG": "ol", "LT": "ol", "MLB": "lb", "NG": "dl", "NT": "dl", "OG": "ol", "OL": "ol", "OLB": "lb", "OT": "ol", "P": "p", "PK": "k", "PR": "kr", "QB": "qb", "RB": "rb", "RE": "dl", "RG": "ol", "RT": "ol", "S": "db", "SE": "wr", "SLB": "lb", "SS": "db", "T": "ol", "TB": "rb", "TE": "te", "WLB": "lb", "WR": "wr"}

Gaps: ["PARTIAL: 22 positioned rows in Nov. 2, 2002 participation table; HERO remains unmapped, giving 21 usable names. Unpositioned reserves omitted; no K/P/KR verified.", "LT/RT in the DEFENSE section map to defensive line; offensive LT/RT map to offensive line. No starter assignments are inferred or stored."]

Unmapped: [{"name": "Chris Harrell", "position": "HERO"}]

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md`: season-correct narration-only naming and generic fallbacks apply. No NFL data, behavior, or runtime dependency reused. This is private source curation, not production behavior.

Validated with ordinary `bowl_bound.roster.load_roster`. Machine receipt: `raw/penn-state-213-receipt.json`.
