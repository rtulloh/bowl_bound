"""Local, evidence-checked corrections to source facts, never chart strengths.

Raw feeds remain immutable. Operators adjudicate a particular normalized event
against retained primary evidence; the normalized source records the original
facts, bounded changes, evidence identities and deterministic receipt.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .evidence import RECOVERY_POLICY, Event

_CORRECTABLE_FACTS = {
    "team",
    "opponent",
    "team_name",
    "opponent_name",
    "kind",
    "yards",
    "blocked_kick_yards",
    "fumble",
    "fumble_lost",
    "fumble_team",
    "fumble_count",
    "recovery_team",
    "recovery_team_2",
    "return_yards",
    "event_phase",
    "try_points",
    "try_scoring_team",
    "prior_touchdown_mention",
    "kick_good",
    "blocked",
    "touchdown",
    "no_play",
    "penalty",
    "penalty_declined",
    "penalty_yards",
    "penalty_side",
    "penalty_type",
    "out_of_bounds",
}
_CORRECTION_KEYS = {
    "season",
    "game_id",
    "event_id",
    "expected_event_sha256",
    "changes",
    "reason",
    "context",
    "evidence",
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _verify_evidence(evidence: Any, directory: Path) -> None:
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("source correction requires retained primary evidence")
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"url", "path", "sha256"}:
            raise ValueError("primary evidence needs URL, local path and SHA256")
        url = urlparse(item["url"]) if isinstance(item["url"], str) else None
        if url is None or url.scheme != "https" or not url.netloc:
            raise ValueError("primary evidence URL must be an identified HTTPS source")
        if not isinstance(item["path"], str) or not item["path"] or not _sha256(item["sha256"]):
            raise ValueError("primary evidence path/hash is malformed")
        path = directory / item["path"]
        try:
            content = path.read_bytes()
        except OSError as error:
            raise ValueError("primary evidence file is unavailable") from error
        if not content or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ValueError("primary evidence hash differs or file is empty")


def apply_adjudications(
    events: Sequence[Event],
    source: dict[str, Any],
    path: Path,
) -> tuple[list[Event], dict[str, Any]]:
    """Apply an exact-source correction manifest atomically in memory.

    This verifies identities and provenance, not the truth of an operator's
    football interpretation. Primary evidence and the human reason remain
    reviewable. No network request, raw-file write or chart parameter is used.
    """
    encoded = path.read_bytes()
    manifest = json.loads(encoded)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "raw_sha256", "corrections"}
        or manifest["schema_version"] != 1
    ):
        raise ValueError("unsupported source adjudication schema")
    if not _sha256(manifest["raw_sha256"]) or manifest["raw_sha256"] != source.get("raw_sha256"):
        raise ValueError("source hash differs from correction manifest")
    if "adjudication" in source:
        raise ValueError(
            "source already adjudicated; normalize the raw snapshot "
            "before applying a revised manifest"
        )
    corrections = manifest["corrections"]
    if not isinstance(corrections, list) or not corrections:
        raise ValueError("source adjudication requires explicit corrections")
    index = {(e.season, e.game_id, e.event_id): i for i, e in enumerate(events)}
    if len(index) != len(events):
        raise ValueError("duplicate event identity in source")
    updated, receipts, seen = list(events), [], set()
    manifest_hash = hashlib.sha256(encoded).hexdigest()
    for correction in corrections:
        if not isinstance(correction, dict) or set(correction) != _CORRECTION_KEYS:
            raise ValueError("source correction fields differ from schema")
        key = (correction["season"], correction["game_id"], correction["event_id"])
        if type(key[0]) is not int or not all(isinstance(v, str) and v for v in key[1:]):
            raise ValueError("source correction identity is malformed")
        if key in seen:
            raise ValueError("duplicate source correction identity")
        seen.add(key)
        if key not in index:
            raise ValueError("source correction names an unknown event")
        original = events[index[key]]
        if original.recovery_policy != RECOVERY_POLICY:
            raise ValueError("adjudication requires fresh physical-recovery normalization")
        if (
            not _sha256(correction["expected_event_sha256"])
            or _digest(original.to_dict()) != correction["expected_event_sha256"]
        ):
            raise ValueError("source event hash differs from correction manifest")
        changes = correction["changes"]
        if not isinstance(changes, dict) or not changes:
            raise ValueError("source correction needs explicit changes")
        if not set(changes) <= _CORRECTABLE_FACTS:
            raise ValueError(
                "unsupported correction field; source identity/text "
                "and model parameters are immutable"
            )
        if (
            not isinstance(correction["reason"], str)
            or not correction["reason"].strip()
            or not isinstance(correction["context"], dict)
        ):
            raise ValueError("source correction needs a reason and explicit context")
        _verify_evidence(correction["evidence"], path.parent)
        corrected = Event.from_dict(original.to_dict() | changes)
        names = {original.team: original.team_name, original.opponent: original.opponent_name}
        if (
            {corrected.team, corrected.opponent} != set(names)
            or corrected.team_name != names.get(corrected.team)
            or corrected.opponent_name != names.get(corrected.opponent)
        ):
            raise ValueError(
                "source correction changes historical matchup identities or their names"
            )
        owner = corrected.fumble_team or (
            corrected.team
            if corrected.kind in {"rush", "complete", "sack"} and corrected.event_phase != "try"
            else None
        )
        physical_loss = (
            corrected.recovery_team != owner
            if corrected.fumble and corrected.recovery_team is not None and owner is not None
            else None
        )
        if "fumble_lost" in changes and changes["fumble_lost"] != physical_loss:
            raise ValueError("adjudicated physical loss conflicts with known recovery/holder")
        corrected = Event.from_dict(corrected.to_dict() | {"fumble_lost": physical_loss})
        if "blocked_kick_yards" in changes:
            corrected = Event.from_dict(
                corrected.to_dict()
                | {
                    "location_evidence": (
                        *corrected.location_evidence,
                        "adjudication:" + manifest_hash,
                    )
                }
            )
        if "recovery_team" in changes or "recovery_team_2" in changes:
            corrected = Event.from_dict(
                corrected.to_dict()
                | {
                    "recovery_confidence": "primary-adjudicated"
                    if corrected.recovery_team is not None
                    else "unknown",
                    "recovery_evidence": (
                        *corrected.recovery_evidence,
                        "adjudication:" + manifest_hash,
                    ),
                }
            )
        if corrected == original:
            raise ValueError("source correction has no changed facts")
        updated[index[key]] = corrected
        receipts.append(
            correction
            | {
                "original": json.loads(json.dumps(original.to_dict())),
                "corrected_sha256": _digest(corrected.to_dict()),
            }
        )
    return updated, source | {
        "adjudication": {
            "schema_version": 1,
            "policy": "primary-evidence-source-facts-v1",
            "manifest_filename": path.name,
            "manifest_sha256": manifest_hash,
            "corrections": receipts,
        }
    }
