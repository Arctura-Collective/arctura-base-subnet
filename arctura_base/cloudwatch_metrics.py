"""Render launch evidence as AWS CloudWatch metric-data payloads."""

from __future__ import annotations

import argparse
import json
from datetime import timezone
from pathlib import Path
from typing import Any, cast

from arctura_base.evidence import parse_timestamp

DEFAULT_NAMESPACE = "Arctura/Launch"
DEFAULT_ENVIRONMENT = "finney-mainnet"


def _bool(value: object) -> float:
    return 1.0 if bool(value) else 0.0


def _number(value: object) -> float:
    if not isinstance(value, str | int | float):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _timestamp(report: dict[str, Any]) -> str | None:
    collected_at = report.get("run", {}).get("collected_at")
    if not collected_at:
        return None
    try:
        return parse_timestamp(str(collected_at)).astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def _metric(
    name: str,
    value: float,
    *,
    environment: str,
    unit: str = "Count",
    timestamp: str | None = None,
) -> dict[str, Any]:
    metric: dict[str, Any] = {
        "MetricName": name,
        "Dimensions": [{"Name": "Environment", "Value": environment}],
        "Unit": unit,
        "Value": value,
    }
    if timestamp:
        metric["Timestamp"] = timestamp
    return metric


def render_metric_data(
    report: dict[str, Any],
    *,
    environment: str = DEFAULT_ENVIRONMENT,
) -> list[dict[str, Any]]:
    """Return AWS CLI-compatible CloudWatch metric-data entries."""
    metrics = report.get("metrics", {})
    timestamp = _timestamp(report)
    return [
        _metric(
            "EvidenceGateOk", _bool(report.get("ok")), environment=environment, timestamp=timestamp
        ),
        _metric(
            "EvidenceElapsedHours",
            _number(metrics.get("elapsed_hours")),
            environment=environment,
            unit="None",
            timestamp=timestamp,
        ),
        _metric(
            "Attestations",
            _number(metrics.get("attestations")),
            environment=environment,
            timestamp=timestamp,
        ),
        _metric(
            "HealthPasses",
            _number(metrics.get("health_passes")),
            environment=environment,
            timestamp=timestamp,
        ),
        _metric(
            "WeightCommits",
            _number(metrics.get("weight_commits")),
            environment=environment,
            timestamp=timestamp,
        ),
        _metric(
            "MinerRestarts",
            _number(metrics.get("miner_restarts")),
            environment=environment,
            timestamp=timestamp,
        ),
        _metric(
            "ValidatorRestarts",
            _number(metrics.get("validator_restarts")),
            environment=environment,
            timestamp=timestamp,
        ),
        _metric(
            "FatalMarkers",
            sum(_number(value) for value in metrics.get("fatal_counts", {}).values()),
            environment=environment,
            timestamp=timestamp,
        ),
    ]


def load_report(path: Path) -> dict[str, Any]:
    """Load a collected evidence report from disk."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render a CloudWatch put-metric-data payload from an existing Arctura "
            "evidence report. This command does not call AWS."
        )
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("runs/mainnet-evidence/report.json"),
        help="Path to an existing arctura-collect-evidence report.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the metric-data JSON list. Defaults to stdout.",
    )
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--environment", default=DEFAULT_ENVIRONMENT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = render_metric_data(load_report(args.report), environment=args.environment)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(
            json.dumps(
                {
                    "ok": True,
                    "metric_data": str(args.output),
                    "publish_command": (
                        "aws cloudwatch put-metric-data "
                        f"--namespace {args.namespace} --metric-data file://{args.output}"
                    ),
                },
                sort_keys=True,
            )
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
