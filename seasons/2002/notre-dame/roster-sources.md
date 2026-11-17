# 2002 notre-dame roster candidate

Sources: https://scarletknights.com/sports/2017/6/26/_m_footbl_stats_2002_2003_ru_nd_html

Retained source: `raw/nd-rutgers.html`; SHA-256 `23d79732d42cecead070909f76bda47a6de61e31f90242ac438c58d2c32f0bbf`. PDF pages: [].

22 distinct names. Names and explicit positions only; no starter assignments, photos, biographies, or inferred returner roles. Composite positions map to each explicitly supported role, with per-role deduplication. Source ordering does not assert starter status.

Mapping: {"C": "ol", "CB": "db", "DB": "db", "DE": "dl", "DEFENSE_LT": "dl", "DEFENSE_RT": "dl", "DL": "dl", "DT": "dl", "FB": "rb", "FL": "wr", "FS": "db", "G": "ol", "HB": "rb", "ILB": "lb", "K": "k", "KR": "kr", "LB": "lb", "LE": "dl", "LG": "ol", "LT": "ol", "MLB": "lb", "NG": "dl", "NT": "dl", "OG": "ol", "OL": "ol", "OLB": "lb", "OT": "ol", "P": "p", "PK": "k", "PR": "kr", "QB": "qb", "RB": "rb", "RE": "dl", "RG": "ol", "RT": "ol", "S": "db", "SE": "wr", "SLB": "lb", "SS": "db", "T": "ol", "TB": "rb", "TE": "te", "WLB": "lb", "WR": "wr"}

Gaps: ["PARTIAL: 22 explicitly positioned names from Nov. 23, 2002 official Rutgers game participation table. Unpositioned reserves omitted; no verified K/P/KR. Given-name initials retained without expansion.", "Official spring roster not merged into fall: contains departures and changed positions. University-archived Observer fall roster retained as raw research only, not qualified as official athletics source. WordPress Maryland gamebook URL returned HTML, not a PDF; excluded."]

Unmapped: []

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md`: season-correct narration-only naming and generic fallbacks apply. No NFL data, behavior, or runtime dependency reused. This is private source curation, not production behavior.

Validated with ordinary `bowl_bound.roster.load_roster`. Machine receipt: `raw/notre-dame-87-receipt.json`.
