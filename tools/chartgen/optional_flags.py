"""Lossless optional provider annotations, separate from source completeness."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

OPTIONAL_FLAG_POLICY = "cfb-derived-optional-flags-v1"
AUTHORED_FLAG_POLICY = "authored-explicit-v1"
LEGACY_FLAG_POLICY = "legacy-unverified"
OPTIONAL_FIELDS = (
    "fumble_vec",
    "fumble_or_muff",
    "fumble_lost",
    "pos_fumble_lost",
    "def_fumble_lost",
    "fg_made",
    "xp_made",
    "qb_scramble",
)


def optional_boolean(value: Any, field: str) -> bool | None:
    """Parse only the declared optional vocabulary; blanks are not negatives."""
    if value is None:
        return None
    if type(value) is bool:
        return value
    if type(value) is int and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        token = value.strip().casefold()
        if not token:
            return None
        if token in {"true", "1"}:
            return True
        if token in {"false", "0"}:
            return False
    raise ValueError(f"optional flag {field} needs true/false/0/1 or blank/null")


@dataclass(frozen=True)
class OptionalFlagObservation:
    """Preserve the supplied scalar independently of its parsed annotation."""

    field: str
    supplied: bool
    raw: bool | int | str | None
    value: bool | None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> OptionalFlagObservation:
        """Validate exact field evidence rather than trusting a parsed receipt."""
        if not isinstance(value, Mapping) or set(value) != {"field", "supplied", "raw", "value"}:
            raise ValueError("optional flag evidence fields differ")
        observation = cls(**value)
        if observation.field not in OPTIONAL_FIELDS or type(observation.supplied) is not bool:
            raise ValueError("optional flag evidence field/presence differs")
        if observation.value is not None and type(observation.value) is not bool:
            raise ValueError("optional flag evidence value must be boolean or null")
        if not observation.supplied and (
            observation.raw is not None or observation.value is not None
        ):
            raise ValueError("absent optional flag evidence cannot contain a value")
        if optional_boolean(observation.raw, observation.field) is not observation.value:
            raise ValueError("optional flag evidence raw/parsed facts differ")
        return observation


def observe_optional_flags(row: Mapping[str, Any]) -> tuple[OptionalFlagObservation, ...]:
    """Record every admitted optional field, including absence and raw blanks."""
    return tuple(
        OptionalFlagObservation(
            field, field in row, row.get(field), optional_boolean(row.get(field), field)
        )
        for field in OPTIONAL_FIELDS
    )


def validate_optional_flags(
    policy: str, observations: Sequence[OptionalFlagObservation], source_sha256: str | None
) -> None:
    """Validate the observation domain without certifying provider completeness."""
    if not isinstance(policy, str) or policy not in {
        OPTIONAL_FLAG_POLICY,
        AUTHORED_FLAG_POLICY,
        LEGACY_FLAG_POLICY,
    }:
        raise ValueError("unsupported optional flag evidence policy")
    if source_sha256 is not None and (
        not isinstance(source_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None
    ):
        raise ValueError("optional flag evidence source receipt is malformed")
    if policy != OPTIONAL_FLAG_POLICY:
        if observations or source_sha256 is not None:
            raise ValueError(
                "authored/legacy optional flag evidence cannot claim provider observations"
            )
        return
    if not isinstance(observations, (tuple, list)) or any(
        not isinstance(item, OptionalFlagObservation) for item in observations
    ):
        raise ValueError("optional flag evidence needs typed observations")
    if tuple(item.field for item in observations) != OPTIONAL_FIELDS:
        raise ValueError("optional flag evidence needs exactly eight ordered observations")
    for item in observations:
        OptionalFlagObservation.from_dict(
            {"field": item.field, "supplied": item.supplied, "raw": item.raw, "value": item.value}
        )


def optional_measurement_missing_evidence(
    policy: str, observations: Sequence[OptionalFlagObservation], source_sha256: str | None
) -> tuple[str, ...]:
    """Keep annotations separate from independently reconciled measurement truth.

    Authored fixtures supply their synthetic facts. Provider completeness needs
    separate evidence; this parser does not invent it or its approval interface.
    """
    validate_optional_flags(policy, observations, source_sha256)
    if policy == AUTHORED_FLAG_POLICY:
        return ()
    if policy == LEGACY_FLAG_POLICY:
        return ("legacy_optional_flag_evidence",)
    return (
        *(("optional_flag_raw_receipt_missing",) if source_sha256 is None else ()),
        "provider_optional_measurement_completeness_unverified",
    )
