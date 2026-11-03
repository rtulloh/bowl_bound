"""Prepare private historical cohorts; broad calibration is a separate phase."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cohort_sources import audit_espn_headers, load_contracts
from .prepare import prepare_cohort
from .source import read_normalized
from .tactics import TacticalProfile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a private historical matchup review slate"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-source", type=Path, help="verify original PBP canonical headers")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--minimum-source-games", type=int, default=6)
    parser.add_argument("--tactics", type=Path)
    parser.add_argument(
        "--acquisition", type=Path, help="optional versioned metadata URL/hash record"
    )
    parser.add_argument(
        "--benchmark", action="append", default=[], help="authorized local reference ID"
    )
    args = parser.parse_args(argv)
    inputs = [args.source, args.membership, args.schedule, args.groups]
    inputs += [p for p in (args.tactics, args.acquisition, args.raw_source) if p is not None]
    if any(not path.is_file() for path in inputs):
        print("Cohort preparation failed: input file is unavailable", file=sys.stderr)
        return 2
    try:
        events, source = read_normalized(args.source)
        contracts = load_contracts(args.membership, args.schedule, args.groups, season=args.season)
        tactics = (
            TacticalProfile.from_dict(json.loads(args.tactics.read_text()))
            if args.tactics
            else None
        )
        provenance = {"normalized_source": source, "normalized_filename": args.source.name}
        if args.raw_source:
            provenance["canonical_header_audit"] = audit_espn_headers(
                args.raw_source, contracts, expected_raw_sha256=source["raw_sha256"]
            )
        if args.acquisition:
            provenance["metadata_acquisition"] = json.loads(args.acquisition.read_text())
        result = prepare_cohort(
            events,
            contracts,
            args.season,
            args.output,
            source_provenance=provenance,
            seed=args.seed,
            minimum_source_games=args.minimum_source_games,
            tactics=tactics,
            benchmark_ids=frozenset(args.benchmark),
            progress=lambda done, total, team: print(
                f"Generated candidate {done}/{total}; source team ID {team}", flush=True
            ),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"Cohort preparation failed: {type(error).__name__}; "
            "inspect private source contracts; existing outputs are retained",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
