from __future__ import annotations

from datetime import datetime, timezone

import pytest

from arctura_base.failover import PACKET_TYPE, build_failover_decision


def evidence(*, active: bool = True, restarts: int = 0, fatal: int = 0) -> dict:
    return {
        "metrics": {
            "validator_restarts": restarts,
            "fatal_counts": {
                "RuntimeError": fatal,
                "Traceback (most recent call last)": 0,
            },
        },
        "run": {
            "collected_at": "2026-08-24T00:00:00Z",
            "services": {
                "arctura-validator": {
                    "ActiveState": "active" if active else "failed",
                }
            },
        },
    }


def probes(*, failures: int = 0, standby: bool = False, approved: bool = False) -> dict:
    return {
        "primary_validator": {
            "healthy": failures == 0,
            "consecutive_failures": failures,
        },
        "standby_validator": {
            "healthy": standby,
            "operator_approved": approved,
        },
    }


def test_failover_decision_holds_when_validator_is_healthy() -> None:
    decision = build_failover_decision(
        evidence=evidence(),
        probes=probes(),
        created_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
    )

    assert decision["packet_type"] == PACKET_TYPE
    assert decision["recommendation"] == "hold"
    assert decision["reasons"] == []
    assert decision["safety"]["dry_run_only"] is True
    assert decision["safety"]["aws_action_attempted"] is False
    assert decision["safety"]["service_restart_attempted"] is False


def test_failover_ready_requires_failed_primary_and_ready_standby() -> None:
    decision = build_failover_decision(
        evidence=evidence(active=False),
        probes=probes(failures=3, standby=True, approved=True),
    )

    assert decision["recommendation"] == "failover_ready"
    assert "validator service is not active" in decision["reasons"]
    assert decision["inputs"]["standby_ready"] is True


def test_failover_investigates_when_standby_is_not_operator_approved() -> None:
    decision = build_failover_decision(
        evidence=evidence(),
        probes=probes(failures=3, standby=True, approved=False),
    )

    assert decision["recommendation"] == "investigate"
    assert decision["inputs"]["probe_failures"] == 3
    assert decision["inputs"]["standby_ready"] is False


def test_failover_investigates_restart_without_service_action() -> None:
    decision = build_failover_decision(evidence=evidence(restarts=1))

    assert decision["recommendation"] == "investigate"
    assert "validator restart count is above zero" in decision["reasons"]
    assert decision["safety"]["service_restart_attempted"] is False


def test_failover_rejects_bad_threshold() -> None:
    with pytest.raises(ValueError, match="failure_threshold"):
        build_failover_decision(evidence=evidence(), failure_threshold=0)
