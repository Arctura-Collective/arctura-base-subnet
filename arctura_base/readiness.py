"""Aggregate non-mutating launch readiness audits."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from arctura_base.aws_readiness import audit_tfvars
from arctura_base.custody_readiness import audit_status as audit_custody_status
from arctura_base.evidence import parse_timestamp
from arctura_base.mainnet_approval import DEFAULT_MAX_COST_AGE_MINUTES
from arctura_base.monitoring_readiness import audit_status as audit_monitoring_status
from arctura_base.treasury import audit_policy, load_policy


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _safe_section(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return fn()
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "section": name,
        }


def _cost_section(
    *,
    cost_payload: dict[str, Any],
    now: datetime,
    max_cost_age_minutes: int,
) -> dict[str, Any]:
    collected_at = cost_payload.get("collected_at")
    age_minutes = None
    checks: dict[str, bool] = {
        "payload_available": cost_payload.get("ok") is True,
        "network_finney": cost_payload.get("network") == "finney",
        "cost_positive": False,
        "fresh": False,
    }
    errors: list[str] = []
    if collected_at:
        try:
            age_minutes = round(
                max(0.0, (now - parse_timestamp(str(collected_at))).total_seconds() / 60),
                3,
            )
            checks["fresh"] = age_minutes <= max_cost_age_minutes
        except ValueError:
            errors.append("burn-cost collected_at is not a valid timezone-aware timestamp")
            age_minutes = None
    else:
        errors.append("burn-cost collected_at is missing")

    try:
        checks["cost_positive"] = float(cost_payload.get("cost_tao", 0)) > 0
    except (TypeError, ValueError):
        checks["cost_positive"] = False
    if not checks["payload_available"]:
        errors.append("burn-cost payload is unavailable")
    if not checks["network_finney"]:
        errors.append("burn-cost payload must be for finney")
    if not checks["cost_positive"]:
        errors.append("cost_tao must be positive")
    if age_minutes is not None and not checks["fresh"]:
        errors.append(
            f"burn-cost payload is stale: {age_minutes:.1f} minutes old "
            f"(max {max_cost_age_minutes})"
        )
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "errors": errors,
        "network": cost_payload.get("network"),
        "cost_tao": cost_payload.get("cost_tao"),
        "collected_at": collected_at,
        "age_minutes": age_minutes,
        "max_age_minutes": max_cost_age_minutes,
    }


def build_readiness_audit(
    *,
    evidence_report: dict[str, Any],
    cost_payload: dict[str, Any],
    aws_audit: dict[str, Any],
    monitoring_audit: dict[str, Any],
    custody_audit: dict[str, Any],
    treasury_audit: dict[str, Any],
    now: datetime | None = None,
    max_cost_age_minutes: int = DEFAULT_MAX_COST_AGE_MINUTES,
) -> dict[str, Any]:
    """Build a dry-run aggregate launch readiness audit."""
    observed_at = now or datetime.now(timezone.utc)
    sections = {
        "evidence": {
            "ok": evidence_report.get("ok") is True,
            "checks": evidence_report.get("checks", {}),
            "metrics": evidence_report.get("metrics", {}),
            "remaining": evidence_report.get("remaining", {}),
            "collected_at": evidence_report.get("run", {}).get("collected_at"),
        },
        "burn_cost": _cost_section(
            cost_payload=cost_payload,
            now=observed_at,
            max_cost_age_minutes=max_cost_age_minutes,
        ),
        "aws_asg": aws_audit,
        "monitoring": monitoring_audit,
        "custody": custody_audit,
        "treasury": treasury_audit,
    }
    blockers = [name for name, section in sections.items() if not bool(section.get("ok"))]
    return {
        "schema_version": 1,
        "audit_type": "arctura_mainnet_readiness_audit",
        "created_at": observed_at.isoformat().replace("+00:00", "Z"),
        "ok": not blockers,
        "blockers": blockers,
        "sections": sections,
        "safety": {
            "dry_run_only": True,
            "on_chain_action_attempted": False,
            "aws_action_attempted": False,
            "terraform_action_attempted": False,
            "wallet_required": False,
            "requires_separate_operator_approval": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate Arctura launch readiness without external side effects."
    )
    parser.add_argument(
        "--evidence-report",
        type=Path,
        default=Path("runs/mainnet-evidence/report.json"),
    )
    parser.add_argument(
        "--cost-payload",
        type=Path,
        default=Path("docs/data/subnet_launch_cost.json"),
    )
    parser.add_argument(
        "--aws-tfvars",
        type=Path,
        default=Path("deploy/aws/asg/terraform.tfvars.example"),
    )
    parser.add_argument(
        "--treasury-policy",
        type=Path,
        default=Path("deploy/treasury/emission_policy.example.json"),
    )
    parser.add_argument(
        "--monitoring-status",
        type=Path,
        default=Path("deploy/monitoring/monitoring-status.example.json"),
    )
    parser.add_argument(
        "--custody-status",
        type=Path,
        default=Path("deploy/custody/custody-status.example.json"),
    )
    parser.add_argument("--max-cost-age-minutes", type=int, default=DEFAULT_MAX_COST_AGE_MINUTES)
    parser.add_argument("--allow-treasury-placeholders", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    evidence = _safe_section("evidence", lambda: _load_json(args.evidence_report))
    cost = _safe_section("burn_cost", lambda: _load_json(args.cost_payload))
    aws = _safe_section(
        "aws_asg",
        lambda: audit_tfvars(args.aws_tfvars.read_text(encoding="utf-8")),
    )
    treasury = _safe_section(
        "treasury",
        lambda: audit_policy(
            load_policy(args.treasury_policy),
            allow_placeholders=args.allow_treasury_placeholders,
        ),
    )
    monitoring = _safe_section(
        "monitoring",
        lambda: audit_monitoring_status(_load_json(args.monitoring_status)),
    )
    custody = _safe_section(
        "custody",
        lambda: audit_custody_status(_load_json(args.custody_status)),
    )
    report = build_readiness_audit(
        evidence_report=evidence,
        cost_payload=cost,
        aws_audit=aws,
        monitoring_audit=monitoring,
        custody_audit=custody,
        treasury_audit=treasury,
        max_cost_age_minutes=args.max_cost_age_minutes,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
