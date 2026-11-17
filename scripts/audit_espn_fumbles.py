"""Diagnose separate ESPN fumble rows without changing source facts or rates.

Candidate links require matching drive sequence, clock, period, possession and
explicit carrier names. A link is not a completeness or statistical-fit approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tools.chartgen.espn_fumbles import link_primary_fumbles
from tools.chartgen.espn_returns import link_return_fumbles
from tools.chartgen.private_io import private_destination

POLICY = "espn-separate-fumble-diagnostic-v4"
_PRIMARY = {"Rush", "Pass Completion", "Sack"}


def _team(play: Mapping[str, Any]) -> str | None:
    reference = play.get("start", {}).get("team", {}).get("$ref", "")
    match = re.search(r"/teams/(\d+)(?:\?|$)", reference)
    return match[1] if match else None


def audit_game(plays: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return candidate primary/recovery links; never infer negative outcomes."""
    if any(not isinstance(row, Mapping) for row in plays):
        raise ValueError("expected JSON play records")
    identifiers = [row.get("id") for row in plays]
    if any(not isinstance(value, str) or not value for value in identifiers) or len(
        set(identifiers)
    ) != len(identifiers):
        raise ValueError("play identifiers must be nonempty and unique within each game")
    index: dict[tuple[str | None, str | None], list[Mapping[str, Any]]] = defaultdict(list)
    for row in plays:
        index[(row.get("drive", {}).get("$ref"), row.get("sequenceNumber"))].append(row)
    counts: Counter[str] = Counter()
    links, unresolved = [], []
    return_links = link_return_fumbles(plays)
    return_by_recovery = {link["recovery"]: link for link in return_links}
    primary_by_recovery = {link["recovery"]: link for link in link_primary_fumbles(plays)}
    for recovery in plays:
        if "fumble" not in recovery.get("type", {}).get("text", "").lower():
            continue
        counts["fumble_rows"] += 1
        if recovery["id"] in return_by_recovery:
            counts["matched_" + return_by_recovery[recovery["id"]]["family"]] += 1
            continue
        if recovery["id"] in primary_by_recovery:
            link = primary_by_recovery[recovery["id"]]
            counts["matched_" + link["kind"]] += 1
            links.append(link)
            continue
        drive = recovery.get("drive", {}).get("$ref")
        sequence = recovery.get("sequenceNumber")
        reason = None
        primary: Mapping[str, Any] = {}
        if not drive or not isinstance(sequence, str) or not sequence.isdigit():
            reason = "missing_drive_or_sequence"
        else:
            predecessors = index[(drive, str(int(sequence) - 1))]
            if len(predecessors) != 1:
                reason = "nonunique_or_missing_predecessor"
            else:
                primary = predecessors[0]
        kind = primary.get("type", {}).get("text", "")
        clock = recovery.get("clock", {}).get("displayValue")
        period = recovery.get("period", {}).get("number")
        if reason is None:
            if kind not in _PRIMARY:
                reason = "non_primary_predecessor"
            elif (
                not isinstance(clock, str)
                or re.fullmatch(r"\d{1,2}:[0-5]\d", clock) is None
                or type(period) is not int
                or period < 1
                or clock != primary.get("clock", {}).get("displayValue")
                or period != primary.get("period", {}).get("number")
            ):
                reason = "clock_or_period_disagreement"
            elif not _team(recovery) or _team(recovery) != _team(primary):
                reason = "owner_disagreement"
            else:
                pattern = (
                    r"complete to (.+?) \([^)]+\)"
                    if kind == "Pass Completion"
                    else r"^(.+?) \([^)]+\) (?:rushed|sacked)"
                )
                carrier = re.search(pattern, primary.get("text") or "", re.I)
                fumbler = re.search(r"fumble by (.+?) \([^)]+\)", recovery.get("text") or "", re.I)
                if not carrier or not fumbler or carrier[1].casefold() != fumbler[1].casefold():
                    reason = "carrier_unmatched"
        if reason is not None:
            counts[reason] += 1
            unresolved.append({"recovery": recovery["id"], "reason": reason})
        else:
            counts["matched_" + kind] += 1
            links.append({"primary": primary["id"], "recovery": recovery["id"], "kind": kind})
    return {
        "policy": POLICY,
        "source_rows": len(plays),
        "counts": dict(counts),
        "candidate_links": links,
        "return_links": return_links,
        "unresolved": unresolved,
        "negative_observations_established": False,
        "release_qualified": False,
    }


def audit_snapshot(source: Path) -> dict[str, Any]:
    """Bind per-game diagnostics to exact, unchanged core play-response bytes."""
    paths = sorted(source.glob("plays-*.json")) or sorted(source.glob("*.json"))
    if not paths:
        raise ValueError("source directory contains no JSON play responses")
    sources, games = {}, {}
    counts: Counter[str] = Counter()
    for path in paths:
        captured = path.read_bytes()
        document = json.loads(captured)
        if not isinstance(document, dict) or not isinstance(document.get("items"), list):
            raise ValueError(f"{path.name}: response needs a play items list")
        report = audit_game(document["items"])
        if path.read_bytes() != captured:
            raise ValueError(f"{path.name}: source changed during audit")
        sources[path.name] = hashlib.sha256(captured).hexdigest()
        games[path.stem] = report
        counts.update(report["counts"])
    return {
        "policy": POLICY,
        "sources": sources,
        "games": games,
        "counts": dict(counts),
        "negative_observations_established": False,
        "release_qualified": False,
    }


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    """Write a new private diagnostic report without replacing prior evidence."""
    destination = private_destination(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main() -> int:
    """Run the diagnostic on a directory of retained core play-response JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plays", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_snapshot(args.plays)
        write_report(args.output, report)
    except (OSError, ValueError, TypeError, AttributeError) as error:
        parser.exit(2, f"ESPN fumble audit failed: {error}\n")
    print(json.dumps(report["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
