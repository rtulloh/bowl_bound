"""Development command entry points; source data is always operator-supplied."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .generate import CalibrationProfile, generate_team, write_bundle
from .source import coverage_report, import_espn, read_normalized, write_normalized


def normalize_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize a local ESPN-derived college PBP snapshot"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args(argv)
    try:
        if "private-data" not in args.output.absolute().parts:
            raise ValueError("historical source evidence must stay under private-data")
        events, source = import_espn(args.input, url=args.source_url)
        args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_normalized(args.output, events, source)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"Source conversion failed: {type(error).__name__}; "
            "check source contract and destination",
            file=sys.stderr,
        )
        return 2
    print(f"Normalized {len(events)} identified events; review private source/coverage evidence")
    return 0


def generate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 1: generate an immutable private Bowl Bound chart"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--team", required=True, help="stable source team ID")
    parser.add_argument("--name", required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--profile", type=Path)
    parser.add_argument(
        "--coverage", type=Path, help="optional expected_games and official totals JSON"
    )
    args = parser.parse_args(argv)
    if not args.source.is_file():
        print("Generation failed: source file is unavailable", file=sys.stderr)
        return 2
    try:
        events, source = read_normalized(args.source)
        profile = (
            CalibrationProfile(**json.loads(args.profile.read_text()))
            if args.profile
            else CalibrationProfile()
        )
        bundle = generate_team(
            events, args.team, args.name, args.season, seed=args.seed, profile=profile
        )
        coverage = json.loads(args.coverage.read_text()) if args.coverage else {}
        bundle[2].update(
            {
                "raw_source": source,
                "coverage": coverage_report(events, args.team, **coverage),
                "baseline_profile": asdict(CalibrationProfile()),
            }
        )
        write_bundle(args.output, bundle)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"Generation failed: {type(error).__name__}; inspect source/profile/output contracts",
            file=sys.stderr,
        )
        return 2
    print("Generated complete local chart; review generation-manifests before play testing")
    return 0


def refine_main(argv: list[str] | None = None) -> int:
    """Run the separate engine-based refinement phase against an immutable source."""
    from .refine import SeedPlan, run_refinement

    parser = argparse.ArgumentParser(description="Phase 2: refine charts with real-engine games")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--team", action="append", required=True, help="ID=Display Name; exactly twice"
    )
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20071102)
    parser.add_argument("--generation-seed", type=int, default=1)
    parser.add_argument("--training-games", type=int, default=128)
    parser.add_argument("--validation-games", type=int, default=512)
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        pilot = dict(item.split("=", 1) for item in args.team)
        if len(args.team) != 2 or len(pilot) != 2 or any(not k or not v for k, v in pilot.items()):
            raise ValueError("supply exactly two distinct ID=Display Name pilot teams")
        events, source = read_normalized(args.source)
        report = run_refinement(
            events,
            pilot,
            args.season,
            args.output,
            seed_plan=SeedPlan(args.seed, args.training_games, args.validation_games),
            generation_seed=args.generation_seed,
            iterations=args.iterations,
            progress=lambda done, total, status: (
                print(f"Games {done}/{total}: {status}", flush=True)
                if done % 16 == 0 or status != "passed"
                else None
            ),
        )
        report["raw_source"] = source
        (args.output / "refinement-report.json").write_text(json.dumps(report, indent=2) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"Refinement failed: {type(error).__name__}; "
            "private candidate/failure evidence is retained",
            file=sys.stderr,
        )
        return 2
    print(
        f"Mechanics ready: {report['mechanics_ready']}; "
        f"held-out statistical gates: {report['heldout_assessment']['passed']}"
    )
    return 0 if report["mechanics_ready"] else 1
