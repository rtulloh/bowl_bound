"""Private human/machine matchup usage exports after real historical simulations."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .cohort_report import canonical_hash


def write_matchup_usage(
    output: Path,
    manifest: Mapping[str, Any],
    training: Sequence[Mapping[str, Any]],
    heldout: Mapping[str, Any],
    coaching: Mapping[str, Any],
    *,
    selected_profiles: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """One physical fixture once, with all actual attempts and failures reconciled."""
    stages = {"training": list(training), "heldout": [heldout], "coaching": [coaching]}
    expected = set(manifest["target_game_ids"])
    for summaries in stages.values():
        for summary in summaries:
            if set(summary["fixture_exposure"]) != expected:
                raise ValueError("actual matchup usage differs from frozen target/simulation slate")
    rows = []
    profiles_hash = canonical_hash(selected_profiles)
    for fixture in manifest["fixtures"]:
        row = {
            k: fixture[k]
            for k in (
                "season",
                "date",
                "game_id",
                "away",
                "away_name",
                "home",
                "home_name",
                "neutral_site",
                "classification",
                "inclusion_reason",
            )
        }
        failed = []
        for stage, summaries in stages.items():
            row[stage + "_runs"] = sum(
                s["fixture_exposure"][fixture["game_id"]]["attempted"] for s in summaries
            )
            failed.extend(
                f
                for s in summaries
                for f in s["failed_fixture_runs"]
                if f["game_id"] == fixture["game_id"]
            )
        row.update(
            failed_runs=len(failed),
            manifest_sha256=manifest["manifest_sha256"],
            source_sha256=manifest["source_sha256"],
            engine_sha256=heldout["engine_sha256"],
            selected_profiles_sha256=profiles_hash,
        )
        rows.append(row)
    if {r["game_id"] for r in rows} != expected or len(rows) != len(expected):
        raise ValueError("matchup usage fixture set is duplicated or incomplete")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream, fieldnames=list(rows[0]) if rows else ["game_id"], lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    lines = [
        f"# {manifest['season']} actual calibration matchup usage",
        "",
        f"Frozen manifest: `{manifest['manifest_sha256']}`",
        f"Source: `{manifest['source_sha256']}`",
        f"Engine: `{heldout['engine_sha256']}`",
        f"Selected profiles: `{profiles_hash}`",
        "",
        "Only reviewed actual fixtures appear. Fresh simulation seeds "
        "do not make these source-held-out games.",
        "Training counts include all retained candidates; "
        "held-out/coaching counts use the selected candidate.",
        "",
        "| Date | Game ID | Away | Home | Training | Held-out | Coaching | Failures |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['date']} | {row['game_id']} | {row['away_name']} | {row['home_name']} | "
            f"{row['training_runs']} | {row['heldout_runs']} | "
            f"{row['coaching_runs']} | {row['failed_runs']} |"
        )
    lines += [
        "",
        "## Team exposure and held-out assessments",
        "",
        "| Team | Actual selected fixtures | State | OFF gates | DEF gates |",
        "|---|---:|---|---|---|",
    ]
    for identity, entry in sorted(manifest["teams"].items(), key=lambda v: v[1]["name"]):
        assessed = heldout["per_source_team"][identity]
        counts = []
        for role in ("offense_assessment", "defense_assessment"):
            metrics = assessed.get(role, {}).get("metrics", {})
            counts.append(f"{sum(m['passed'] for m in metrics.values())}/{len(metrics)}")
        lines.append(
            f"| {entry['name']} | {entry['selected_games']} | {assessed['state']} | "
            f"{counts[0]} | {counts[1]} |"
        )
    contents = {
        "calibration-matchups.csv": stream.getvalue(),
        "calibration-matchups.md": "\n".join(lines) + "\n",
    }
    for name, content in contents.items():
        path = output / name
        if path.exists():
            if path.read_text() != content:
                raise ValueError(
                    "retained human/machine matchup usage differs from checked evidence"
                )
        else:
            with path.open("x") as target:
                target.write(content)
            path.chmod(0o600)
    return rows
