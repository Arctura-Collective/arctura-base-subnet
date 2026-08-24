from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from arctura_base.mainnet_approval import (
    DEFAULT_CREATE_COMMAND,
    PACKET_TYPE,
    build_approval_packet,
    validate_inputs,
)


def green_evidence() -> dict:
    return {
        "ok": True,
        "checks": {
            "duration": True,
            "weight_commits": True,
            "health_samples": True,
            "restart_budget": True,
            "no_fatal_errors": True,
        },
        "metrics": {
            "elapsed_hours": 48.2,
            "attestations": 4,
            "weight_commits": 2,
            "health_passes": 578,
            "miner_restarts": 0,
            "validator_restarts": 0,
        },
        "run": {
            "started_at": "2026-08-21T00:00:00Z",
            "collected_at": "2026-08-23T00:12:00Z",
        },
    }


def fresh_cost() -> dict:
    return {
        "schema_version": 1,
        "ok": True,
        "network": "finney",
        "cost_tao": "686.125",
        "cost_label": "686.125 TAO",
        "source": "btcli subnet burn_cost --subtensor.network finney",
        "raw_output": "Subnet burn cost: 686.125 TAO",
        "collected_at": "2026-08-23T00:20:00Z",
    }


def test_build_approval_packet_records_non_signing_boundary() -> None:
    packet = build_approval_packet(
        evidence_report=green_evidence(),
        cost_payload=fresh_cost(),
        operator="owner-operator",
        reviewer="independent-reviewer",
        owner_wallet="owner",
        validator_wallet="validator",
        miner_wallet="miner",
        now=datetime(2026, 8, 23, 0, 30, tzinfo=timezone.utc),
    )

    assert packet["packet_type"] == PACKET_TYPE
    assert packet["dry_run_only"] is True
    assert packet["on_chain_action_attempted"] is False
    assert packet["wallet_required"] is False
    assert packet["requires_hardware_wallet_confirmation"] is True
    assert packet["requires_separate_final_operator_execution"] is True
    assert packet["launch_command"] == DEFAULT_CREATE_COMMAND
    assert packet["validated_inputs"]["burn_cost_tao"] == str(Decimal("686.125"))
    assert packet["validated_inputs"]["burn_cost_age_minutes"] == 10.0
    assert packet["evidence_metrics"]["weight_commits"] == 2


def test_approval_packet_rejects_red_evidence() -> None:
    evidence = green_evidence()
    evidence["ok"] = False

    with pytest.raises(ValueError, match="evidence report is not green"):
        validate_inputs(
            evidence_report=evidence,
            cost_payload=fresh_cost(),
            now=datetime(2026, 8, 23, 0, 30, tzinfo=timezone.utc),
        )


def test_approval_packet_rejects_unavailable_cost() -> None:
    cost = fresh_cost()
    cost["ok"] = False
    cost["cost_tao"] = None

    with pytest.raises(ValueError, match="burn-cost payload is unavailable"):
        validate_inputs(
            evidence_report=green_evidence(),
            cost_payload=cost,
            now=datetime(2026, 8, 23, 0, 30, tzinfo=timezone.utc),
        )


def test_approval_packet_rejects_stale_cost() -> None:
    with pytest.raises(ValueError, match="stale"):
        validate_inputs(
            evidence_report=green_evidence(),
            cost_payload=fresh_cost(),
            now=datetime(2026, 8, 23, 1, 0, 1, tzinfo=timezone.utc),
        )


def test_approval_packet_requires_human_fields() -> None:
    with pytest.raises(ValueError, match="reviewer is required"):
        build_approval_packet(
            evidence_report=green_evidence(),
            cost_payload=fresh_cost(),
            operator="owner-operator",
            reviewer=" ",
            owner_wallet="owner",
            validator_wallet="validator",
            miner_wallet="miner",
            now=datetime(2026, 8, 23, 0, 30, tzinfo=timezone.utc),
        )
