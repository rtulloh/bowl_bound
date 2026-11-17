"""Acquire explicitly positioned historical commentary names from school tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from bowl_bound.roster import parse_roster
from bowl_bound.team_csv import team_folder_name
from tools.chartgen.private_io import private_destination

_POSITIONS = {
    "qb": "QB QUARTERBACK",
    "rb": "RB FB HB TB WB IBACK WINGBACK RUNNINGBACK FULLBACK HALFBACK TAILBACK",
    "wr": "WR SE FL WIDERECEIVER SPLITEND FLANKER",
    "te": "TE TIGHTEND",
    "ol": "OL C G T OG OT LG LT RG RT CENTER GUARD TACKLE OFFENSIVELINE "
    "OFFENSIVELINEMAN OFFENSIVETACKLE OFFENSIVEGUARD LEFTGUARD",
    "dl": "DL DE DT NT NG DEFENSIVELINE DEFENSIVEEND DEFENSIVETACKLE NOSETACKLE "
    "DEFENSIVELINEMAN NOSEGUARD RUSHEND LEFTRUSHEND RIGHTRUSHEND",
    "lb": "LB ILB OLB MLB WLB SLB LINEBACKER INSIDELINEBACKER OUTSIDELINEBACKER "
    "WILLLINEBACKER MIKELINEBACKER STRONGSIDELINEBACKER BUCKLINEBACKER",
    "db": "DB CB S FS SS DEFENSIVEBACK CORNERBACK SAFETY FREESAFETY STRONGSAFETY "
    "LEFTCORNERBACK RIGHTCORNERBACK",
    "k": "K PK KICKER PLACEKICKER",
    "p": "P PUNTER",
    "kr": "KR PR KICKRETURNER PUNTRETURNER RETURNSPECIALIST",
}
_ROLE = {alias: role for role, aliases in _POSITIONS.items() for alias in aliases.split()}


class _Tables(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.headings: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._title = False
        self._heading = False
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._title = True
        elif tag == "h1":
            self._heading = True
        elif tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._title:
            self.title.append(data)
        if self._heading:
            self.headings.append(data)
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._title = False
        elif tag == "h1":
            self._heading = False
        elif tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join(" ".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def parse_roster_page(text: str, season: int) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """Read names and explicit roles only after checking the page's own season."""
    parser = _Tables()
    parser.feed(text)
    title = " ".join(parser.title)
    labels = [title, " ".join(parser.headings)]
    if not any(
        re.search(rf"\b{season}\b", label) is not None
        and "football" in label.casefold()
        and "roster" in label.casefold()
        for label in labels
    ):
        raise ValueError("page does not identify the requested season-specific football roster")
    roster: dict[str, list[str]] = {}
    unmapped: Counter[str] = Counter()
    for table in parser.tables:
        columns = None
        for row in table:
            labels = [re.sub(r"[^a-z]", "", cell.casefold()) for cell in row]
            names = [i for i, label in enumerate(labels) if label in {"name", "fullname", "player"}]
            positions = [i for i, label in enumerate(labels) if label in {"pos", "position"}]
            if names and positions:
                columns = (names[0], positions[0])
                continue
            if columns is None or len(row) <= max(columns):
                continue
            name, position = row[columns[0]], row[columns[1]]
            name = name.rstrip("* ")
            if name.count(",") == 1:
                last, first = (part.strip() for part in name.split(","))
                suffix = re.search(r"\s+(Jr\.?|Sr\.?|II|III|IV)$", first)
                if suffix:
                    name = f"{first[: suffix.start()]} {last} {suffix[1]}"
                else:
                    name = f"{first} {last}"
            if not name:
                continue
            roles = {
                _ROLE[token]
                for piece in re.split(r"[/,&]", position)
                if (token := re.sub(r"[^A-Z]", "", piece.upper())) in _ROLE
            }
            if not roles:
                unmapped[position] += 1
            for role in sorted(roles):
                if name not in roster.setdefault(role, []):
                    roster[role].append(name)
    if not roster:
        raise ValueError("page contains no named positional roster table")
    parse_roster(json.dumps(roster))
    return roster, {"title": title, "unmapped_positions": dict(unmapped)}


def main() -> int:
    """Acquire a reviewed team/URL plan into a new private staging directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cache-dir", type=Path, help="Reparse retained <team-id>.html responses")
    args = parser.parse_args()
    plan = json.loads(args.sources.read_text())
    season = plan["season"]
    destination = private_destination(args.output)
    destination.mkdir(parents=True, exist_ok=False)
    raw = destination / "raw"
    raw.mkdir()

    def acquire(item: tuple[str, dict[str, str]]) -> tuple[str, dict[str, Any]]:
        identifier, team = item
        record: dict[str, Any] = {**team, "status": "failed"}
        try:
            if args.cache_dir is not None:
                cached = args.cache_dir / f"{identifier}.html"
                payload = cached.read_bytes()
                record["cached_response"] = str(cached)
            else:
                request = Request(
                    team["url"], headers={"User-Agent": "BowlBound-RosterResearch/1.0"}
                )
                with urlopen(request, timeout=25) as response:
                    payload = response.read()
                    record["resolved_url"] = response.url
            (raw / f"{identifier}.html").write_bytes(payload)
            record["source_sha256"] = hashlib.sha256(payload).hexdigest()
            roster, details = parse_roster_page(payload.decode("utf-8"), season)
            record.update(details)
            record["position_counts"] = {key: len(value) for key, value in roster.items()}
            record["players"] = len({name for names in roster.values() for name in names})
            if record["players"] < 20:
                raise ValueError(
                    "fewer than 20 explicitly positioned players; review partial source"
                )
            folder = destination / "seasons" / str(season) / team_folder_name(team["name"])
            folder.mkdir(parents=True)
            encoded = (json.dumps(roster, indent=2) + "\n").encode()
            (folder / "roster.json").write_bytes(encoded)
            record["roster_sha256"] = hashlib.sha256(encoded).hexdigest()
            (folder / "roster-sources.md").write_text(
                f"# {season} {team['name']} roster sources\n\n"
                f"Source: {team['url']}\n\nRetrieved: {datetime.now(timezone.utc).date()}\n\n"
                f"Source SHA-256: {record['source_sha256']}\n\n"
                "Names and explicitly listed positions only; no biographies, images or ratings.\n"
                "No starter status inferred. Return roles included only when explicitly listed.\n"
                f"Unmapped source positions: {json.dumps(record['unmapped_positions'])}\n"
            )
            record["status"] = "acquired"
        except (OSError, URLError, ValueError, UnicodeError) as error:
            record["error"] = str(error)
        print(identifier, record["status"], record.get("players", ""), flush=True)
        return identifier, record

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4))) as executor:
        results = dict(executor.map(acquire, plan["teams"].items()))
    report = {
        "season": season,
        "teams": results,
        "counts": dict(Counter(r["status"] for r in results.values())),
    }
    (destination / "acquisition.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["counts"]))
    return int(any(row["status"] != "acquired" for row in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
