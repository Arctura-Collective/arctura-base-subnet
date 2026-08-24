"""Validator-controlled P5 Stewardship provenance verification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERIFIED_STATUSES: frozenset[str] = frozenset({"verified", "active"})


@dataclass(frozen=True)
class StewardshipVerification:
    """Verified provenance record for one miner hotkey."""

    hotkey: str
    energy_tag: str
    status: str
    evidence: str = ""


def load_stewardship_verifications(path: str | Path | None) -> dict[str, StewardshipVerification]:
    """Load validator-owned stewardship verification records from JSON."""
    if not path:
        return {}

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    records = raw.get("verifications", [])
    if not isinstance(records, list):
        raise ValueError("stewardship verification file must contain a verifications list")

    verifications: dict[str, StewardshipVerification] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"verification record {index} must be an object")
        hotkey = str(record.get("hotkey", "")).strip()
        energy_tag = str(record.get("energy_tag", "")).strip().lower()
        status = str(record.get("status", "")).strip().lower()
        evidence = str(record.get("evidence", "")).strip()
        if not hotkey:
            raise ValueError(f"verification record {index} missing hotkey")
        if not energy_tag:
            raise ValueError(f"verification record {index} missing energy_tag")
        if not status:
            raise ValueError(f"verification record {index} missing status")
        verifications[hotkey] = StewardshipVerification(
            hotkey=hotkey,
            energy_tag=energy_tag,
            status=status,
            evidence=evidence,
        )

    return verifications


def is_stewardship_verified(
    hotkey: str,
    claimed_energy_tag: str,
    verifications: dict[str, StewardshipVerification | dict[str, Any]],
) -> bool:
    """Return True when a miner hotkey has verified matching provenance."""
    record = verifications.get(hotkey)
    if record is None:
        return False
    if isinstance(record, dict):
        record_tag = str(record.get("energy_tag", "")).strip().lower()
        record_status = str(record.get("status", "")).strip().lower()
    else:
        record_tag = record.energy_tag
        record_status = record.status

    return record_status in VERIFIED_STATUSES and record_tag == claimed_energy_tag.strip().lower()
