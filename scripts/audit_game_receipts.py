"""Audit retained private JSON game receipts without replaying or importing the engine."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from tools import (
    game_audit,
    game_audit_clock,
    game_audit_commitment,
    game_audit_continuity,
    game_audit_envelope,
    game_audit_final_binding,
    game_audit_kickoff,
    game_audit_lookup,
    game_audit_pat,
    game_audit_penalty,
    game_audit_priority,
    game_audit_punt,
    game_audit_row_links,
    game_audit_supplemental,
)
from tools.game_audit import ReceiptAuditError, audit_receipt
from tools.game_audit_lookup import LookupInventory


def _verify_observer_bindings(
    observer: Path,
    priority_observer: Path,
    lookup_observer: Path,
    envelope_observer: Path,
    row_observer: Path,
    commitment_observer: Path,
    clock_observer: Path,
    continuity_observer: Path,
    pat_observer: Path,
    final_observer: Path,
    kickoff_observer: Path,
    supplemental_observer: Path,
    penalty_observer: Path,
    punt_observer: Path,
) -> None:
    """Check declared origins/bindings; this alone cannot attest loaded code bytes."""
    for module, expected, label in (
        (game_audit, observer, "observer"),
        (game_audit_priority, priority_observer, "priority observer"),
        (game_audit_lookup, lookup_observer, "lookup observer"),
        (game_audit_envelope, envelope_observer, "capture link observer"),
        (game_audit_row_links, row_observer, "row link observer"),
        (game_audit_commitment, commitment_observer, "ordinary commitment observer"),
        (game_audit_clock, clock_observer, "standard clock observer"),
        (game_audit_continuity, continuity_observer, "ordinary continuity observer"),
        (game_audit_pat, pat_observer, "PAT report observer"),
        (game_audit_final_binding, final_observer, "final row observer"),
        (game_audit_kickoff, kickoff_observer, "kickoff observer"),
        (game_audit_supplemental, supplemental_observer, "supplemental observer"),
        (game_audit_penalty, penalty_observer, "fixed penalty observer"),
        (game_audit_punt, punt_observer, "punt observer"),
    ):
        origin = getattr(module, "__file__", None)
        specification_origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if (
            not isinstance(origin, str)
            or not isinstance(specification_origin, str)
            or Path(origin).resolve() != expected
            or Path(specification_origin).resolve() != expected
        ):
            raise ValueError(f"unexpected actual loaded {label} origin")
    if audit_receipt is not game_audit.audit_receipt:
        raise ValueError("unexpected accounting observer binding")
    if game_audit.audit_priority is not game_audit_priority.audit_priority:
        raise ValueError("unexpected priority observer binding")
    if game_audit.audit_lookup is not game_audit_lookup.audit_lookup:
        raise ValueError("unexpected lookup observer binding")
    if game_audit.audit_capture_links is not game_audit_envelope.audit_capture_links:
        raise ValueError("unexpected capture link observer binding")
    if game_audit_envelope.audit_physical_draws is not game_audit_lookup.audit_physical_draws:
        raise ValueError("unexpected capture physical observer binding")
    if game_audit_envelope._same_fact is not game_audit_priority._same_fact:
        raise ValueError("unexpected capture equality helper binding")
    if game_audit_envelope._facts is not game_audit_lookup._facts:
        raise ValueError("unexpected capture fact helper binding")
    if game_audit_lookup._same_fact is not game_audit_priority._same_fact:
        raise ValueError("unexpected lookup equality helper binding")
    if LookupInventory is not game_audit_lookup.LookupInventory:
        raise ValueError("unexpected lookup inventory binding")
    if game_audit.audit_row_links is not game_audit_row_links.audit_row_links:
        raise ValueError("unexpected row observer binding")
    if game_audit_row_links.lookup is not game_audit_lookup:
        raise ValueError("unexpected row lookup module binding")
    if game_audit_row_links.envelope is not game_audit_envelope:
        raise ValueError("unexpected row envelope module binding")

    if (
        game_audit.audit_ordinary_commitments
        is not game_audit_commitment.audit_ordinary_commitments
    ):
        raise ValueError("unexpected ordinary commitment observer binding")
    if game_audit_commitment.priority is not game_audit_priority:
        raise ValueError("unexpected ordinary commitment priority module binding")

    if game_audit.audit_standard_clock is not game_audit_clock.audit_standard_clock:
        raise ValueError("unexpected standard clock observer binding")
    if game_audit_clock.priority is not game_audit_priority:
        raise ValueError("unexpected standard clock priority module binding")
    if game_audit.audit_ordinary_continuity is not game_audit_continuity.audit_ordinary_continuity:
        raise ValueError("unexpected ordinary continuity observer binding")
    if game_audit_continuity.commitment is not game_audit_commitment:
        raise ValueError("unexpected ordinary continuity commitment module binding")
    if game_audit.audit_pat_reports is not game_audit_pat.audit_pat_reports:
        raise ValueError("unexpected PAT report observer binding")
    if game_audit_pat.commitment is not game_audit_commitment:
        raise ValueError("unexpected PAT report commitment module binding")

    if game_audit.audit_kickoff_commands is not game_audit_kickoff.audit_kickoff_commands:
        raise ValueError("unexpected kickoff observer binding")
    if game_audit_kickoff.commitment is not game_audit_commitment:
        raise ValueError("unexpected kickoff commitment module binding")
    if (
        game_audit.audit_supplemental_commitments
        is not game_audit_supplemental.audit_supplemental_commitments
    ):
        raise ValueError("unexpected supplemental observer binding")
    if game_audit_supplemental.commitment is not game_audit_commitment:
        raise ValueError("unexpected supplemental commitment module binding")
    if game_audit_supplemental.priority is not game_audit_priority:
        raise ValueError("unexpected supplemental priority module binding")
    if game_audit_supplemental.LookupInventory is not game_audit_lookup.LookupInventory:
        raise ValueError("unexpected supplemental recovery inventory binding")

    if game_audit.audit_penalty_commitments is not game_audit_penalty.audit_penalty_commitments:
        raise ValueError("unexpected fixed penalty observer binding")
    if game_audit_penalty.commitment is not game_audit_commitment:
        raise ValueError("unexpected fixed penalty commitment module binding")
    if game_audit_penalty.priority is not game_audit_priority:
        raise ValueError("unexpected fixed penalty priority module binding")

    if game_audit.audit_punt_commitments is not game_audit_punt.audit_punt_commitments:
        raise ValueError("unexpected punt observer binding")
    if game_audit_punt.commitment is not game_audit_commitment:
        raise ValueError("unexpected punt commitment module binding")
    if game_audit_punt.kickoff is not game_audit_kickoff:
        raise ValueError("unexpected punt kickoff helper module binding")

    if game_audit.audit_final_row_binding is not game_audit_final_binding.audit_final_row_binding:
        raise ValueError("unexpected final row observer binding")
    if game_audit_final_binding.commitment is not game_audit_commitment:
        raise ValueError("unexpected final row commitment module binding")
    if game_audit_final_binding.envelope is not game_audit_envelope:
        raise ValueError("unexpected final row envelope module binding")


def main(argv: list[str] | None = None) -> int:
    """Write an immutable private report of available invariants and first failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lookup-inventory", type=Path)
    parser.add_argument("--lookup-inventory-sha256")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    observer = Path(__file__).resolve().parents[1] / "tools/game_audit.py"
    priority_observer = observer.with_name("game_audit_priority.py")
    lookup_observer = observer.with_name("game_audit_lookup.py")
    envelope_observer = observer.with_name("game_audit_envelope.py")
    row_observer = observer.with_name("game_audit_row_links.py")
    commitment_observer = observer.with_name("game_audit_commitment.py")
    clock_observer = observer.with_name("game_audit_clock.py")
    continuity_observer = observer.with_name("game_audit_continuity.py")
    pat_observer = observer.with_name("game_audit_pat.py")
    final_observer = observer.with_name("game_audit_final_binding.py")
    kickoff_observer = observer.with_name("game_audit_kickoff.py")
    supplemental_observer = observer.with_name("game_audit_supplemental.py")
    penalty_observer = observer.with_name("game_audit_penalty.py")
    punt_observer = observer.with_name("game_audit_punt.py")
    frozen_inventory = None
    inventory_info = None
    try:
        if "private-data" not in output.parts:
            raise ValueError("audit output must be inside private-data")
        _verify_observer_bindings(
            observer,
            priority_observer,
            lookup_observer,
            envelope_observer,
            row_observer,
            commitment_observer,
            clock_observer,
            continuity_observer,
            pat_observer,
            final_observer,
            kickoff_observer,
            supplemental_observer,
            penalty_observer,
            punt_observer,
        )
        if (args.lookup_inventory is None) != (args.lookup_inventory_sha256 is None):
            raise ValueError("lookup inventory requires both a file and explicit expected SHA256")
        if args.lookup_inventory is not None:
            expected = args.lookup_inventory_sha256
            if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
                raise ValueError("lookup inventory expected SHA256 must be lowercase hexadecimal")
            inventory_path = args.lookup_inventory.resolve()
            raw_inventory = inventory_path.read_bytes()
            digest = hashlib.sha256(raw_inventory).hexdigest()
            if digest != expected:
                raise ValueError("lookup inventory differs from expected SHA256")
            frozen_inventory = LookupInventory(json.loads(raw_inventory))
            inventory_info = dict(
                path=str(inventory_path),
                sha256=digest,
                expected_sha256=expected,
                source_unchanged=True,
                teams=frozen_inventory.team_count,
                cells=frozen_inventory.cell_count,
                scope=(
                    "Pinned typed data agreement only; "
                    "review authority and source truth not attested."
                ),
            )
        paths = []
        for selected in args.receipts:
            if selected.is_dir():
                paths.extend(sorted(selected.glob("game-*.json.gz")))
            elif selected.is_file():
                paths.append(selected)
            else:
                raise ValueError(f"missing receipt input: {selected.name}")
        paths = [path.resolve() for path in paths]
        if not paths or len(paths) != len(set(paths)):
            raise ValueError("receipt input must be nonempty with no duplicates")
        source_pins = {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                Path(__file__).resolve(),
                observer,
                priority_observer,
                lookup_observer,
                envelope_observer,
                row_observer,
                commitment_observer,
                clock_observer,
                continuity_observer,
                pat_observer,
                final_observer,
                kickoff_observer,
                supplemental_observer,
                penalty_observer,
                punt_observer,
            )
        }
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        print(f"Receipt audit rejected: {error}")
        return 2
    results: list[dict[str, Any]] = []
    for path in paths:
        item: dict[str, Any] = {"path": str(path), "sha256": None}
        try:
            raw = path.read_bytes()
            item["sha256"] = hashlib.sha256(raw).hexdigest()
            row = json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)
            audited = (
                audit_receipt(row)
                if frozen_inventory is None
                else audit_receipt(row, lookup_inventory=frozen_inventory)
            )
            item.update(status="partial_pass", audit=audited)
        except (ReceiptAuditError, KeyError, TypeError, ValueError, OSError, EOFError) as error:
            item.update(status="failed", error=str(error))
        results.append(item)
    unchanged = True
    source_errors = []
    for path, digest in source_pins.items():
        try:
            unchanged &= hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
        except OSError as error:
            unchanged = False
            source_errors.append(str(error))
    if inventory_info is not None:
        try:
            inventory_info["source_unchanged"] = (
                hashlib.sha256(Path(cast(str, inventory_info["path"])).read_bytes()).hexdigest()
                == inventory_info["expected_sha256"]
            )
        except OSError as error:
            inventory_info["source_unchanged"] = False
            source_errors.append(str(error))
    identity_error = None
    try:
        _verify_observer_bindings(
            observer,
            priority_observer,
            lookup_observer,
            envelope_observer,
            row_observer,
            commitment_observer,
            clock_observer,
            continuity_observer,
            pat_observer,
            final_observer,
            kickoff_observer,
            supplemental_observer,
            penalty_observer,
            punt_observer,
        )
    except ValueError as error:
        identity_error = str(error)
    initially_passed = [row for row in results if row["status"] == "partial_pass"]
    initial_reports_checked = sum(row["audit"]["reports_checked"] for row in initially_passed)
    observer_invalid = not unchanged or identity_error is not None
    inventory_invalid = inventory_info is not None and not inventory_info["source_unchanged"]
    if observer_invalid or inventory_invalid:
        reason = (
            "Current qualification invalid: observer source/origin/binding changed."
            if observer_invalid
            else "Current qualification invalid: pinned lookup inventory changed."
        )
        for item in initially_passed:
            item["initial_comparison"] = deepcopy(item["audit"])
            current = item["audit"]
            affected = (
                set(current["components"])
                if observer_invalid
                else {
                    "typed_lookup_agreement",
                    "ordinary_commitment",
                    "standard_clock",
                    "ordinary_continuity",
                    "pat_report_commitment",
                    "ordinary_kickoff_commitment",
                    "supplemental_commitment",
                    "accepted_previous_penalty_commitment",
                    "punt_fair_catch_commitment",
                }
            )
            for name in affected:
                current["components"][name] = "UNVERIFIED"
                counts = current["coverage"][name]
                current["coverage"][name] = dict(
                    checked=0, excluded=0, unknown=sum(counts.values())
                )
            if "ordinary_commitment" in affected:
                # Detailed initial successes belong solely to initial_comparison.
                current.pop("ordinary_commitment_counts", None)
            if "standard_clock" in affected:
                current.pop("standard_clock_counts", None)
            if "ordinary_continuity" in affected:
                current.pop("ordinary_continuity_counts", None)
            if "pat_report_commitment" in affected:
                current.pop("pat_report_counts", None)
            if "ordinary_kickoff_commitment" in affected:
                current.pop("kickoff_counts", None)
            if "punt_fair_catch_commitment" in affected:
                current.pop("punt_commitment_counts", None)
            if "accepted_previous_penalty_commitment" in affected:
                current.pop("penalty_commitment_counts", None)
            if "supplemental_commitment" in affected:
                current.pop("supplemental_commitment_counts", None)
            if "final_row_linkage" in affected:
                current.pop("final_row_binding", None)
            current["status"] = "failed"
            current["qualification_error"] = reason
            item.update(status="failed", error=reason)
    passed = [row for row in results if row["status"] == "partial_pass"]
    capabilities: dict[str, Any] = {}
    for item in passed:
        for name, counts in item["audit"]["coverage"].items():
            summary = capabilities.setdefault(
                name, dict(statuses={}, checked=0, excluded=0, unknown=0)
            )
            status = item["audit"]["components"][name]
            summary["statuses"][status] = summary["statuses"].get(status, 0) + 1
            for count in ("checked", "excluded", "unknown"):
                summary[count] += counts[count]
    report = {
        "observer_version": game_audit.OBSERVER_VERSION,
        "inventory_version": game_audit.INVENTORY_VERSION,
        "status": "partial_pass"
        if (
            len(passed) == len(results)
            and unchanged
            and identity_error is None
            and (inventory_info is None or inventory_info["source_unchanged"])
        )
        else "failed",
        "source_sha256": source_pins,
        "python": sys.version,
        "executable": sys.executable,
        "loaded_engine_modules": sorted(
            name for name in sys.modules if name == "bowl_bound" or name.startswith("bowl_bound.")
        ),
        "observer_source_unchanged": unchanged,
        "observer_source_error": "; ".join(source_errors) or None,
        "lookup_inventory": inventory_info,
        "observer_bindings_consistent": identity_error is None,
        "observer_binding_error": identity_error,
        "games_checked": len(results),
        "games_passed_available_invariants": len(passed),
        "games_passed_initial_comparison": len(initially_passed),
        "initial_reports_checked": initial_reports_checked,
        "games_failed": len(results) - len(passed),
        "reports_checked": sum(row["audit"]["reports_checked"] for row in passed),
        "capability_summary": capabilities,
        "capability_summary_scope": (
            "Passing available-invariant receipts only; failures retained separately."
        ),
        "results": results,
        "full_play_by_play_qualification": False,
        "accuracy_qualification": False,
        "remaining_ticket": "DATA-055",
    }
    target = output / "audit.json"
    with target.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    target.chmod(0o600)
    return 0 if report["status"] == "partial_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
