"""Build a non-signing final approval packet for Finney subnet launch."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from arctura_base.evidence import parse_timestamp

PACKET_TYPE = "unsigned_mainnet_launch_approval_packet"
DEFAULT_CREATE_COMMAND = "btcli subnet create --wallet.name owner --subtensor.network finney"
DEFAULT_MAX_COST_AGE_MINUTES = 30


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a decimal value") from exc
    if parsed.is_nan() or parsed < 0:
        raise ValueError(f"{field_name} must be a non-negative decimal value")
    return parsed


def _require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _cost_age_minutes(cost_payload: dict[str, Any], now: datetime) -> float:
    collected_at = parse_timestamp(str(cost_payload["collected_at"]))
    return max(0.0, (now - collected_at).total_seconds() / 60)


def validate_inputs(
    *,
    readiness_report: dict[str, Any],
    evidence_report: dict[str, Any],
    cost_payload: dict[str, Any],
    now: datetime,
    max_cost_age_minutes: int = DEFAULT_MAX_COST_AGE_MINUTES,
) -> dict[str, Any]:
    """Return validated input facts or raise ValueError."""
    if readiness_report.get("ok") is not True:
        raise ValueError("aggregate readiness report is not green; refusing approval packet")
    if evidence_report.get("ok") is not True:
        raise ValueError("evidence report is not green; refusing approval packet")
    if cost_payload.get("ok") is not True:
        raise ValueError("burn-cost payload is unavailable; refusing approval packet")
    if cost_payload.get("network") != "finney":
        raise ValueError("burn-cost payload must be for finney")

    age_minutes = _cost_age_minutes(cost_payload, now)
    if age_minutes > max_cost_age_minutes:
        raise ValueError(
            f"burn-cost payload is stale: {age_minutes:.1f} minutes old "
            f"(max {max_cost_age_minutes})"
        )

    burn_cost_tao = _decimal(cost_payload.get("cost_tao"), "cost_tao")
    if burn_cost_tao <= 0:
        raise ValueError("cost_tao must be positive")

    return {
        "burn_cost_tao": str(burn_cost_tao),
        "burn_cost_collected_at": str(cost_payload["collected_at"]),
        "burn_cost_age_minutes": round(age_minutes, 3),
        "readiness_created_at": readiness_report.get("created_at"),
        "readiness_blockers": readiness_report.get("blockers", []),
        "evidence_collected_at": evidence_report.get("run", {}).get("collected_at"),
        "evidence_started_at": evidence_report.get("run", {}).get("started_at"),
    }


def build_approval_packet(
    *,
    readiness_report: dict[str, Any],
    evidence_report: dict[str, Any],
    cost_payload: dict[str, Any],
    operator: str,
    reviewer: str,
    owner_wallet: str,
    validator_wallet: str,
    miner_wallet: str,
    command: str = DEFAULT_CREATE_COMMAND,
    now: datetime | None = None,
    max_cost_age_minutes: int = DEFAULT_MAX_COST_AGE_MINUTES,
) -> dict[str, Any]:
    """Build a machine-readable approval packet without signing or spending."""
    observed_at = now or datetime.now(timezone.utc)
    facts = validate_inputs(
        readiness_report=readiness_report,
        evidence_report=evidence_report,
        cost_payload=cost_payload,
        now=observed_at,
        max_cost_age_minutes=max_cost_age_minutes,
    )
    return {
        "schema_version": 1,
        "packet_type": PACKET_TYPE,
        "created_at": observed_at.isoformat().replace("+00:00", "Z"),
        "network": "finney",
        "dry_run_only": True,
        "on_chain_action_attempted": False,
        "wallet_required": False,
        "requires_hardware_wallet_confirmation": True,
        "requires_separate_final_operator_execution": True,
        "operator": _require_text(operator, "operator"),
        "reviewer": _require_text(reviewer, "reviewer"),
        "wallets": {
            "owner": _require_text(owner_wallet, "owner_wallet"),
            "validator": _require_text(validator_wallet, "validator_wallet"),
            "miner": _require_text(miner_wallet, "miner_wallet"),
        },
        "launch_command": _require_text(command, "command"),
        "validated_inputs": facts,
        "readiness_sections": sorted(readiness_report.get("sections", {})),
        "evidence_checks": evidence_report.get("checks", {}),
        "evidence_metrics": evidence_report.get("metrics", {}),
        "approval_boundary": (
            "This packet records readiness review only. It does not create a subnet, "
            "sign an extrinsic, stake, register hotkeys, move funds, or approve "
            "treasury transactions."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a non-signing final approval packet for Finney launch."
    )
    parser.add_argument(
        "--readiness-report",
        type=Path,
        default=Path("runs/mainnet-evidence/readiness.json"),
        help="Green aggregate arctura-readiness-audit report.",
    )
    parser.add_argument(
        "--evidence-report",
        type=Path,
        default=Path("runs/mainnet-evidence/report.json"),
        help="Green arctura-collect-evidence report.",
    )
    parser.add_argument(
        "--cost-payload",
        type=Path,
        default=Path("docs/data/subnet_launch_cost.json"),
        help="Fresh Finney burn-cost ticker payload.",
    )
    parser.add_argument("--operator", required=True, help="Final operator approver name/id.")
    parser.add_argument("--reviewer", required=True, help="Independent reviewer name/id.")
    parser.add_argument("--owner-wallet", required=True)
    parser.add_argument("--validator-wallet", required=True)
    parser.add_argument("--miner-wallet", required=True)
    parser.add_argument("--command", default=DEFAULT_CREATE_COMMAND)
    parser.add_argument("--max-cost-age-minutes", type=int, default=DEFAULT_MAX_COST_AGE_MINUTES)
    parser.add_argument("--output", type=Path, help="Optional packet output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet = build_approval_packet(
        readiness_report=_load_json(args.readiness_report),
        evidence_report=_load_json(args.evidence_report),
        cost_payload=_load_json(args.cost_payload),
        operator=args.operator,
        reviewer=args.reviewer,
        owner_wallet=args.owner_wallet,
        validator_wallet=args.validator_wallet,
        miner_wallet=args.miner_wallet,
        command=args.command,
        max_cost_age_minutes=args.max_cost_age_minutes,
    )
    rendered = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
