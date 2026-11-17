# 2002 lsu roster candidate

Sources: https://storage.googleapis.com/lsusports-net-prod/2019/07/ca5f88d8-02fb001-012.pdf

Retained source: `raw/lsu.pdf`; SHA-256 `2c9d2768e0e942d642976518f800a45d15ee26d3e7e1043bafb04642fa1f9973`. PDF pages: [6, 7].

121 distinct names. Names and explicit positions only; no starter assignments, photos, biographies, or inferred returner roles. Composite positions map to each explicitly supported role, with per-role deduplication. Source ordering does not assert starter status.

Mapping: {"C": "ol", "CB": "db", "DB": "db", "DE": "dl", "DL": "dl", "DT": "dl", "FB": "rb", "FL": "wr", "FS": "db", "G": "ol", "HB": "rb", "ILB": "lb", "K": "k", "KR": "kr", "LB": "lb", "LG": "ol", "LT": "ol", "MLB": "lb", "NG": "dl", "NT": "dl", "OG": "ol", "OL": "ol", "OLB": "lb", "OT": "ol", "P": "p", "PK": "k", "PR": "kr", "QB": "qb", "RB": "rb", "RG": "ol", "RT": "ol", "S": "db", "SE": "wr", "SLB": "lb", "SS": "db", "T": "ol", "TB": "rb", "TE": "te", "WLB": "lb", "WR": "wr"}

Gaps: ["Numerical roster only; adjacent alphabetical summary has position differences (e.g. Shyrone Carey RB vs WR). Numerical table retained consistently; no merging of conflicting columns.", "SNP left unmapped; FB/SNP retains only explicit FB. No inferred returners. Media-guide roster does not establish per-game availability."]

Unmapped: [{"name": "Wendell York", "position": "SNP"}, {"name": "Henry Barham", "position": "SNP"}, {"name": "Steve Damen", "position": "SNP"}, {"name": "Jacob Guidry", "position": "SNP"}]

Consulted Paydirt `docs/dev-notes/issues/DATA/DATA-049.md`: season-correct narration-only naming and generic fallbacks apply. No NFL data, behavior, or runtime dependency reused. This is private source curation, not production behavior.

Validated with ordinary `bowl_bound.roster.load_roster`. Machine receipt: `raw/lsu-99-receipt.json`.
