"""Phase-two cohort operator entry point; requires the reviewed fixture hash."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .artifacts import ArtifactCompression, StorageCapacityError
from .cohort_refinement import run_cohort_refinement
from .source import read_normalized
from .tactics import TacticalProfile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refine a reviewed actual historical cohort slate")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewed-manifest-sha256", required=True)
    parser.add_argument("--training-repetitions", type=int, default=4)
    parser.add_argument("--validation-repetitions", type=int, default=8)
    parser.add_argument("--coaching-repetitions", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--master-seed", type=int, default=20081103)
    parser.add_argument("--generation-seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--artifact-compression",
        choices=[value.value for value in ArtifactCompression],
        default=ArtifactCompression.GZIP.value,
        help="complete retained game reports: gzip (default) or legacy json",
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if any(not path.is_file() for path in (args.source, args.manifest, args.targets)):
        print("Cohort refinement failed: input file is unavailable", file=sys.stderr)
        return 2
    try:
        events, _ = read_normalized(args.source)
        manifest = json.loads(args.manifest.read_text())
        targets = json.loads(args.targets.read_text())
        tactics = TacticalProfile.from_dict(manifest["source"]["tactics"])
        result = run_cohort_refinement(
            events,
            manifest,
            targets,
            args.output,
            reviewed_manifest_sha256=args.reviewed_manifest_sha256,
            training_repetitions=args.training_repetitions,
            validation_repetitions=args.validation_repetitions,
            coaching_repetitions=args.coaching_repetitions,
            iterations=args.iterations,
            master_seed=args.master_seed,
            generation_seed=args.generation_seed,
            workers=args.workers,
            compression=ArtifactCompression(args.artifact_compression),
            tactics=tactics,
            resume=args.resume,
            progress=lambda done, total, status: (
                print(f"Games {done}/{total}: {status}", flush=True)
                if done % 16 == 0 or done == total or status != "passed"
                else None
            ),
        )
    except StorageCapacityError as error:
        print(f"Cohort refinement failed: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"Cohort refinement failed: {type(error).__name__}; "
            "private candidates/failures are retained",
            file=sys.stderr,
        )
        return 2
    print(
        f"Mechanics ready: {result['mechanics_ready']}; "
        f"all per-team statistical gates: {result['all_team_statistical_gates_passed']}",
        flush=True,
    )
    return 0 if result["mechanics_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
