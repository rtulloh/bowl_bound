"""Audit pinned generated charts through normalized facts and the real resolver.

Source observations remain private: this gate verifies the candidate/model and
preserved baseline, not the truth of unavailable PBP. Local source/OOB and full
current-engine qualification remain separate required release evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from contextlib import suppress
from dataclasses import asdict, replace
from itertools import combinations, product
from pathlib import Path
from typing import Any

from bowl_bound.dice import GREEN_FACES, RED_FACES
from bowl_bound.models import (
    ChartColor,
    Defense,
    NormalizedCell,
    Play,
    Priority,
    ResultKind,
    TeamChart,
)
from bowl_bound.normalization import CELL_LEGEND
from bowl_bound.resolution import resolve_cells
from bowl_bound.team_csv import load_team

POLICY_SHA256 = "bbb35953b3812769bde39d5c567fc21dece00b0899cb037feaad0db7aa88280c"
POLICY_YARDS = (
    (0, -2, 0, 1, 2, -1),
    (0, -2, -1, 1, 2, 0),
    (0, 2, -3, 0, 1, 0),
    (0, -2, -1, 0, 1, 2),
    (0, -1, -2, 1, 2, 0),
    (0, 0, 0, -3, 1, 2),
    (0, 1, -1, -2, 3, -1),
    (0, 1, 1, -1, -2, 1),
    (0, 2, 2, 0, -3, -1),
)
WEIGHTS = Counter(r + g for r, g in product(RED_FACES, GREEN_FACES))
NUMERIC = {ResultKind.YARDS, ResultKind.NO_CHANGE}
EXPECTATIONS = "release/generated-chart-audit.json"
SOURCE_FIELDS = {"normalized_source_sha256", "source_review_sha256", "oob_review_sha256"}
DERIVED_FIELDS = {"candidate_sha256", "baseline_expectations_sha256", "baseline_catalog_sha256"}


class ChartAuditError(ValueError):
    """A generated release candidate is incomplete, stale or tactically invalid."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ChartAuditError(f"Missing or invalid chart audit input: {path.name}") from error
    if not isinstance(value, dict):
        raise ChartAuditError(f"Expected chart audit object: {path.name}")
    return value


def policy_effect(play: Play, formation: Defense) -> int:
    """Return an approved authored coefficient, not a football rule."""
    return POLICY_YARDS[play.value - 1][list(Defense).index(formation)]


def _policy_identity() -> str:
    fields = (
        "incomplete_delta",
        "interception_delta",
        "sack_delta",
        "scramble_delta",
        "breakaway_delta",
        "override_delta",
    )
    effects = [
        {
            "formation": f.value,
            "play": p.value,
            "yard_offset": policy_effect(p, f),
            **dict.fromkeys(fields, 0.0),
        }
        for p in Play
        for f in Defense
    ]
    profile = {
        "schema_version": 1,
        "origin": "authored-bb-yardage-v1",
        "source_hashes": [],
        "effects": effects,
    }
    return _sha(json.dumps(profile, sort_keys=True).encode())


def _facts(cell: NormalizedCell) -> dict[str, Any]:
    facts = asdict(cell)
    facts.pop("provenance")
    facts["rgb_color"] = cell.provenance.rgb_color if cell.provenance else None
    return facts


def _address(record: Any) -> str:
    return f"{record.defense.value}/{record.play.value}/{record.roll}"


def _defense_fingerprint(chart: TeamChart) -> str:
    return _digest(sorted((_address(r), _facts(r.cell)) for r in chart.defense))


def weighted_distributions(chart: TeamChart) -> dict[str, str]:
    """Fingerprint normalized outcomes under all 36 physical defensive pairs."""
    output = {}
    for play in Play:
        for formation in Defense:
            counts: Counter[str] = Counter()
            for r in chart.defense:
                if r.play is play and r.defense is formation:
                    counts[json.dumps(_facts(r.cell), sort_keys=True)] += WEIGHTS[r.roll]
            output[f"{formation.value}/{play.value}"] = _digest(sorted(counts.items()))
    return output


def baseline_record(root: Path, key: str) -> dict[str, Any]:
    """Build compact expected facts from an independently accepted baseline."""
    season, slug = key.split("/")
    chart, _ = load_team(root / "seasons" / season, slug)
    return {
        "nondefensive_sha256": {
            name: _sha((root / "seasons" / key / name).read_bytes())
            for name in ("offense.csv", "special.csv", "team.yaml")
        },
        "defense_semantics_sha256": _defense_fingerprint(chart),
        "explicit_numeric_zero": sorted(
            _address(r)
            for r in chart.defense
            if r.cell.kind is ResultKind.YARDS and r.cell.yards == 0
        ),
    }


def audit_candidate(root: Path) -> dict[str, Any]:
    """Recompute release evidence; acceptance never trusts a saved green receipt."""
    pins, teams = _catalog(root)
    if not pins:
        return {"passed": True, "generated_teams": 0, "scope": "no generated charts"}
    expected = _json(root / EXPECTATIONS)
    if expected.get("schema_version") != 1 or not isinstance(expected.get("teams"), dict):
        raise ChartAuditError("Missing generated chart audit schema/team expectations")
    if set(expected["teams"]) != teams:
        raise ChartAuditError("Generated audit team inventory differs from shipped catalog")
    identity = expected.get("model_identity", {})
    _validate_identity(identity)
    review = expected.get("source_review", {})
    if (
        not isinstance(review, dict)
        or not SOURCE_FIELDS <= set(review) <= SOURCE_FIELDS | DERIVED_FIELDS
        or any(not _is_sha(value) for value in review.values())
    ):
        raise ChartAuditError(
            "Missing independently reviewed private source/OOB qualification hashes"
        )
    candidate_sha = _digest(pins)
    if review.get("candidate_sha256") != candidate_sha:
        raise ChartAuditError("Private source qualification is stale for this candidate catalog")
    if review.get("baseline_expectations_sha256") != _digest(expected["teams"]):
        raise ChartAuditError("Private source qualification is stale for baseline expectations")
    engine_sha = _engine_identity(root)
    reports = {}
    for key in sorted(teams):
        season, slug = key.split("/")
        baseline = expected["teams"][key]
        if not isinstance(baseline, dict):
            raise ChartAuditError(f"Missing baseline expectations: {key}")
        files = baseline.get("nondefensive_sha256", {})
        if set(files) != {"offense.csv", "special.csv", "team.yaml"}:
            raise ChartAuditError(f"Incomplete baseline nondefensive pins: {key}")
        for name, digest in files.items():
            if not _is_sha(digest) or pins[f"seasons/{key}/{name}"] != digest:
                raise ChartAuditError(f"Changed baseline nondefensive/OOB facts: {key}/{name}")
        try:
            chart, metadata = load_team(root / "seasons" / season, slug)
        except ValueError as error:
            raise ChartAuditError(f"Invalid strict chart/provenance codec: {key}") from error
        if metadata.source_sha256 != identity["source_sha256"]:
            raise ChartAuditError(f"Chart source identity disagrees with qualified model: {key}")
        restored = _restore_baseline(chart, baseline)
        if _defense_fingerprint(restored) != baseline.get("defense_semantics_sha256"):
            raise ChartAuditError(
                f"Unexpected baseline defense/response/priority/OOB change: {key}"
            )
        reports[key] = _audit_roles(chart, restored, key)
    return {
        "schema_version": 1,
        "passed": True,
        "generated_teams": len(teams),
        "physical_defensive_mass": sum(WEIGHTS.values()),
        "candidate_sha256": candidate_sha,
        "expectations_sha256": _sha((root / EXPECTATIONS).read_bytes()),
        "policy_sha256": POLICY_SHA256,
        "model_identity": identity,
        "engine_sha256": engine_sha,
        "auditor_sha256": _sha(Path(__file__).read_bytes()),
        "source_truth_revalidated": False,
        "source_review": review,
        "scope": "normalized defense mass; primary priority roles/classes; preserved baseline",
        "limits": "PBP/OOB truth and full supplemental/game/AI qualification are separate gates.",
        "teams": reports,
    }


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _validate_identity(identity: Any) -> None:
    fields = {"origin", "sha256", "authored_experimental", "tool_version", "source_sha256"}
    if (
        not isinstance(identity, dict)
        or set(identity) != fields
        or _policy_identity() != POLICY_SHA256
        or identity.get("origin") != "authored-bb-yardage-v1"
        or identity.get("sha256") != POLICY_SHA256
        or identity.get("authored_experimental") is not True
        or identity.get("tool_version") != "college-chartgen-v6"
        or not _is_sha(identity.get("source_sha256"))
    ):
        raise ChartAuditError("Missing or unsupported approved generated chart model identity")


def _catalog(root: Path) -> tuple[dict[str, str], set[str]]:
    pins = _json(root / "release/manifest.json").get("generated_sha256", {})
    if not isinstance(pins, dict):
        raise ChartAuditError("Generated catalog must be an exact pinned map")
    teams: dict[str, set[str]] = {}
    for name, digest in pins.items():
        match = re.fullmatch(
            r"seasons/(\d{4}/[a-z0-9][a-z0-9-]*)/(offense.csv|defense.csv|special.csv|team.yaml)",
            name,
        )
        provenance = re.fullmatch(r"seasons/(\d{4})/provenance/([a-z0-9][a-z0-9-]*)\.csv", name)
        if match:
            key, section = match.groups()
        elif provenance:
            key = "/".join(provenance.groups())
            section = "provenance.csv"
        else:
            raise ChartAuditError("Unexpected generated catalog resource")
        path = root / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ChartAuditError("Symlinked generated catalog input")
        if not path.is_file() or _sha(path.read_bytes()) != digest:
            raise ChartAuditError(f"Stale generated catalog pin: {key}/{section}")
        teams.setdefault(key, set()).add(section)
    sections = {"offense.csv", "defense.csv", "special.csv", "team.yaml", "provenance.csv"}
    if any(actual != sections for actual in teams.values()):
        raise ChartAuditError("Every generated team needs complete chart/provenance inputs")
    return pins, set(teams)


def _restore_baseline(chart: TeamChart, expected: dict[str, Any]) -> TeamChart:
    zeros = expected.get("explicit_numeric_zero")
    addresses = {_address(r) for r in chart.defense}
    if not isinstance(zeros, list) or len(set(zeros)) != len(zeros) or not set(zeros) <= addresses:
        raise ChartAuditError("Invalid baseline zero/blank expectations")
    records = []
    for r in chart.defense:
        cell = r.cell
        if cell.kind in NUMERIC:
            value = (cell.yards or 0) - policy_effect(r.play, r.defense)
            blank = value == 0 and cell.priority is Priority.NORMAL and _address(r) not in zeros
            color = ChartColor.WHITE if blank else ChartColor.RED if value < 0 else ChartColor.GREEN
            evidence = replace(cell.provenance, rgb_color=CELL_LEGEND[color].rgb_color)
            cell = replace(
                cell,
                kind=ResultKind.NO_CHANGE if blank else ResultKind.YARDS,
                yards=None if blank else value,
                chart_color=color,
                provenance=evidence,
            )
        records.append(replace(r, cell=cell))
    return replace(chart, defense=tuple(records))


def _primary(
    chart: TeamChart, play: Play, formation: Defense, offense: NormalizedCell
) -> tuple[int, dict[str, int]]:
    numeric_contribution = 0
    classes: Counter[str] = Counter()
    for r in chart.defense:
        if r.play is play and r.defense is formation:
            result = resolve_cells(offense, r.cell)
            classes[
                _digest((result.kind, result.operation, result.pending, result.out_of_bounds))
            ] += WEIGHTS[r.roll]
            if result.kind is ResultKind.YARDS:
                numeric_contribution += (result.yards or 0) * WEIGHTS[r.roll]
    return numeric_contribution, dict(classes)


def _audit_roles(chart: TeamChart, baseline: TeamChart, key: str) -> dict[str, Any]:
    distributions = weighted_distributions(chart)
    if all(len({distributions[f"{f.value}/{p.value}"] for f in Defense}) == 1 for p in Play):
        raise ChartAuditError(f"Equivalent formation probabilities: {key}")
    for gain in (4, 10, 18):
        offense = NormalizedCell(ResultKind.YARDS, None, yards=gain)
        contributions = {(p, f): _primary(chart, p, f, offense)[0] for p in Play for f in Defense}
        ordered = (
            (Play.ONE, (Defense.B, Defense.A, Defense.E)),
            (Play.THREE, (Defense.C, Defense.A, Defense.B)),
            (Play.FOUR, (Defense.A, Defense.F)),
            (Play.SIX, (Defense.D, Defense.A, Defense.F)),
            (Play.SEVEN, (Defense.D, Defense.F, Defense.E)),
            (Play.NINE, (Defense.E, Defense.F, Defense.B)),
            (Play.EIGHT, (Defense.A, Defense.F)),
        )
        for play, formations in ordered:
            values = [contributions[play, f] for f in formations]
            if any(a >= b for a, b in zip(values[:-1], values[1:], strict=True)):
                raise ChartAuditError(f"Missing declared role/tradeoff: {key}, play {play.value}")
        for first, second in combinations(Defense, 2):
            differences = [contributions[p, first] - contributions[p, second] for p in Play]
            if not (min(differences) < 0 < max(differences)):
                raise ChartAuditError(
                    f"Tactical dominance or inert formation: {key}, {first.value}/{second.value}"
                )
    # Every normalized actual offense cell is checked. Multiplicity cannot affect
    # equality: each cell's exact 36-pair primary class distribution must match.
    # Pending/supplemental kinds remain kinds, never zero-yard resolved outcomes.
    for play in Play:
        facts = {_digest(_facts(r.cell)): r.cell for r in chart.offense if r.play is play}
        for cell in facts.values():
            for formation in Defense:
                before = _primary(baseline, play, formation, cell)[1]
                after = _primary(chart, play, formation, cell)[1]
                if before != after:
                    raise ChartAuditError(
                        f"Unintended primary outcome class change: {key}, play {play.value}"
                    )
    return {
        "formation_counterplay": True,
        "primary_class_invariance": True,
        "distinct_weighted_defense_columns": len(set(distributions.values())),
    }


def _engine_identity(root: Path) -> str:
    # Hash the code actually used, and reject a different supplied candidate core.
    source = Path(__file__).resolve().parents[1]
    for name, module in tuple(sys.modules.items()):
        if name == "bowl_bound" or name.startswith("bowl_bound."):
            expected = source / (name.replace(".", "/") + ".py")
            if name == "bowl_bound":
                expected = source / "bowl_bound/__init__.py"
            actual = getattr(module, "__file__", None)
            if actual is None or Path(actual).resolve() != expected.resolve():
                raise ChartAuditError("Foreign imported engine module cannot certify candidate")
    names = sorted(p.relative_to(source).as_posix() for p in (source / "bowl_bound").glob("*.py"))
    hashes = {}
    for name in names:
        digest = _sha((source / name).read_bytes())
        candidate = root / name
        if not candidate.is_file() or _sha(candidate.read_bytes()) != digest:
            raise ChartAuditError("Candidate engine differs from the audit's imported engine")
        hashes[name] = digest
    return _digest(hashes)


def build_expectations(root: Path, baseline_root: Path, qualification: Path) -> dict[str, Any]:
    """Export safe expectations after independent private source/OOB review.

    This never qualifies source truth or creates a passed audit. The supplied
    qualification hashes must refer to independently retained/reviewed evidence.
    """
    pins, keys = _catalog(root)
    baseline_pins, baseline_keys = _catalog(baseline_root)
    if baseline_keys != keys:
        raise ChartAuditError("Baseline and candidate generated team inventories differ")
    teams = {key: baseline_record(baseline_root, key) for key in sorted(keys)}
    source = _json(qualification)
    if set(source) != SOURCE_FIELDS | {"model_identity"}:
        raise ChartAuditError(
            "Unsupported qualification fields; export only approved SHA identities"
        )
    identity = source.pop("model_identity", None)
    _validate_identity(identity)
    if any(not _is_sha(value) for value in source.values()):
        raise ChartAuditError("Source qualification fields must be SHA-256 identities")
    source["candidate_sha256"] = _digest(pins)
    source["baseline_catalog_sha256"] = _digest(baseline_pins)
    source["baseline_expectations_sha256"] = _digest(teams)
    return {
        "schema_version": 1,
        "model_identity": identity,
        "source_review": source,
        "teams": teams,
    }


def main(argv: list[str] | None = None) -> int:
    """Compute an actual candidate report, or export baseline expectations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path)
    parser.add_argument("--baseline-root", type=Path)
    parser.add_argument("--qualification", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.baseline_root or args.qualification:
            if not args.baseline_root or not args.qualification:
                raise ChartAuditError(
                    "Baseline export requires both baseline root and qualification"
                )
            result = build_expectations(args.root, args.baseline_root, args.qualification)
            destination = args.root / EXPECTATIONS
            destination.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print("Exported baseline expectations; actual candidate audit still required")
        else:
            result = audit_candidate(args.root)
            if args.report:
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(
                    json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
            print(f"Generated chart audit passed: {result['generated_teams']} teams")
    except (ChartAuditError, OSError, ValueError, TypeError, KeyError) as error:
        if args.report:
            rejected = {
                "schema_version": 1,
                "passed": False,
                "reason": str(error),
                "policy_sha256": POLICY_SHA256,
                "source_truth_revalidated": False,
            }
            # Preserve identities that remain readable after the original error;
            # missing/broken inputs stay absent, never invented as zero hashes.
            with suppress(ChartAuditError, OSError):
                pins = _json(args.root / "release/manifest.json").get("generated_sha256")
                if isinstance(pins, dict):
                    rejected["candidate_sha256"] = _digest(pins)
            with suppress(OSError):
                rejected["expectations_sha256"] = _sha((args.root / EXPECTATIONS).read_bytes())
            with suppress(ChartAuditError, OSError):
                rejected["engine_sha256"] = _engine_identity(args.root)
            rejected["auditor_sha256"] = _sha(Path(__file__).read_bytes())
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(rejected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        print(f"Generated chart audit failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
