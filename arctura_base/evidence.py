"""Utilities for creating bounded, non-claiming testnet evidence records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_testnet_evidence_template(
    *, network: str, netuid: int, run_id: str | None = None
) -> dict[str, Any]:
    """Build a machine-readable template without asserting a testnet outcome.

    Operators must complete the observation and artifact fields from an actual
    bounded run before treating a record as evidence. This function deliberately
    emits ``None`` for every operational result.
    """
    return {
        "schema_version": "1.0",
        "record_type": "testnet_run_evidence",
        "publication_state": "template",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": {
            "id": run_id,
            "network": network,
            "netuid": netuid,
            "started_at": None,
            "ended_at": None,
            "command": None,
            "code_revision": None,
        },
        "observations": {
            "miner_live": None,
            "validator_live_loop": None,
            "mandate_issued": None,
            "concurrent_miner_response": None,
            "weight_submission": None,
        },
        "artifacts": {
            "metagraph_or_explorer_url": None,
            "immutable_log_url": None,
            "artifact_hash": None,
        },
        "claim_boundary": (
            "This is an incomplete template, not evidence of a completed run. "
            "Do not publish it as an observed testnet or mainnet result."
        ),
        "completion_requirements": [
            "UTC-bounded start and end timestamps",
            "network and netuid",
            "executed method or command",
            "code revision",
            "observed results and stated limitations",
            "an immutable log, artifact hash, or network reference where available",
        ],
    }


def write_testnet_evidence_template(
    output_path: Path, *, network: str, netuid: int, run_id: str | None = None
) -> Path:
    """Write a template record, refusing to overwrite an existing artifact."""
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing evidence artifact: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            build_testnet_evidence_template(network=network, netuid=netuid, run_id=run_id),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_path
