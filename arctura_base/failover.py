"""Dry-run validator failover decision packets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

PACKET_TYPE = "validator_failover_decision_dry_run"


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _service_active(evidence: dict[str, Any], service: str) -> bool:
    services = evidence.get("run", {}).get("services", {})
    return bool(services.get(service, {}).get("ActiveState") == "active")


def _fatal_markers(evidence: dict[str, Any]) -> int:
    return sum(int(count) for count in evidence.get("metrics", {}).get("fatal_counts", {}).values())


def _standby_ready(probes: dict[str, Any]) -> bool:
    standby = probes.get("standby_validator", {})
    return bool(standby.get("healthy")) and bool(standby.get("operator_approved"))


def _probe_failures(probes: dict[str, Any]) -> int:
    primary = probes.get("primary_validator", {})
    return int(primary.get("consecutive_failures", 0))


def build_failover_decision(
    *,
    evidence: dict[str, Any],
    probes: dict[str, Any] | None = None,
    failure_threshold: int = 3,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a read-only validator failover decision packet."""
    if failure_threshold < 1:
        raise ValueError("failure_threshold must be at least 1")
    probes = probes or {}
    observed_at = created_at or datetime.now(timezone.utc)
    metrics = evidence.get("metrics", {})
    validator_active = _service_active(evidence, "arctura-validator")
    restart_count = int(metrics.get("validator_restarts", 0))
    fatal_count = _fatal_markers(evidence)
    probe_failures = _probe_failures(probes)
    standby_ready = _standby_ready(probes)

    reasons: list[str] = []
    if not validator_active:
        reasons.append("validator service is not active")
    if restart_count > 0:
        reasons.append("validator restart count is above zero")
    if fatal_count > 0:
        reasons.append("fatal journal markers are present")
    if probe_failures >= failure_threshold:
        reasons.append(
            f"primary validator probe failures reached threshold "
            f"({probe_failures}/{failure_threshold})"
        )

    if not reasons:
        recommendation = "hold"
    elif standby_ready and (
        not validator_active or fatal_count > 0 or probe_failures >= failure_threshold
    ):
        recommendation = "failover_ready"
    else:
        recommendation = "investigate"

    return {
        "schema_version": 1,
        "packet_type": PACKET_TYPE,
        "created_at": observed_at.isoformat().replace("+00:00", "Z"),
        "recommendation": recommendation,
        "reasons": reasons,
        "safety": {
            "dry_run_only": True,
            "on_chain_action_attempted": False,
            "aws_action_attempted": False,
            "service_restart_attempted": False,
            "requires_separate_operator_approval": True,
        },
        "inputs": {
            "evidence_collected_at": evidence.get("run", {}).get("collected_at"),
            "validator_active": validator_active,
            "validator_restarts": restart_count,
            "fatal_markers": fatal_count,
            "probe_failures": probe_failures,
            "failure_threshold": failure_threshold,
            "standby_ready": standby_ready,
        },
        "execution_boundary": (
            "This packet is advisory only. It does not stop services, change DNS, "
            "modify AWS Auto Scaling state, promote a standby validator, sign "
            "transactions, or move funds."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a dry-run validator failover decision.")
    parser.add_argument(
        "--evidence-report",
        type=Path,
        default=Path("runs/mainnet-evidence/report.json"),
        help="Path to an arctura-collect-evidence report.",
    )
    parser.add_argument(
        "--probe-snapshot",
        type=Path,
        help="Optional operator-provided validator probe snapshot JSON.",
    )
    parser.add_argument("--failure-threshold", type=int, default=3)
    parser.add_argument("--output", type=Path, help="Optional output path for the decision packet.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    decision = build_failover_decision(
        evidence=_load_json(args.evidence_report),
        probes=_load_json(args.probe_snapshot) if args.probe_snapshot else None,
        failure_threshold=args.failure_threshold,
    )
    rendered = json.dumps(decision, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if decision["recommendation"] == "hold" else 1


if __name__ == "__main__":
    raise SystemExit(main())
