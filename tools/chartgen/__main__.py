"""Run public development chart generation with operator-supplied evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cli import normalize_main
from .release_pipeline import generate_release_cohort
from .source import read_normalized


def main(argv: list[str] | None = None) -> int:
    """Dispatch normalization or the complete current candidate pipeline."""
    parser = argparse.ArgumentParser(description="Bowl Bound development chart generator")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "normalize", help="normalize supplied ESPN-derived source", add_help=False
    )
    generate = subcommands.add_parser("generate", help="generate and audit a new local cohort")
    generate.add_argument("--source", type=Path, required=True)
    generate.add_argument(
        "--teams", type=Path, required=True, help="JSON object of source ID to name"
    )
    generate.add_argument("--season", type=int, choices=(2002, 2007), required=True)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=1)
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["normalize"]:
        return normalize_main(arguments[1:])
    args = parser.parse_args(arguments)
    try:
        if not args.source.is_file():
            raise ValueError("source file is unavailable")
        events, _ = read_normalized(args.source)
        teams = json.loads(args.teams.read_text())
        if not isinstance(teams, dict):
            raise ValueError("teams must be a JSON object of source IDs to display names")
        report = generate_release_cohort(events, teams, args.season, args.output, seed=args.seed)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        print(f"Generation failed: {error}", file=sys.stderr)
        return 2
    print(
        f"Generated {len(report['teams'])} teams; "
        "source qualification and release review remain required"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
