"""Dry-run readiness audit for hosted monitoring proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

PLACEHOLDER_MARKERS = ("REPLACE", "TODO", "TBD", "PLACEHOLDER", "example.com")
EXPECTED_DASHBOARD_UID = "arctura-launch-readiness"


def load_status(path: Path) -> dict[str, Any]:
    """Load a monitoring status JSON file."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _contains_placeholder(value: object) -> bool:
    rendered = json.dumps(value, sort_keys=True).upper()
    return any(marker.upper() in rendered for marker in PLACEHOLDER_MARKERS)


def _truthy_nested(status: dict[str, Any], section: str, field: str) -> bool:
    value = status.get(section, {})
    return isinstance(value, dict) and value.get(field) is True


def audit_status(status: dict[str, Any]) -> dict[str, Any]:
    """Return a non-mutating monitoring readiness audit."""
    grafana = status.get("grafana", {})
    checks = {
        "schema_version": status.get("schema_version") == 1,
        "prometheus_targets_healthy": _truthy_nested(status, "prometheus", "targets_healthy"),
        "node_exporter_textfile_collector": _truthy_nested(
            status, "prometheus", "node_exporter_textfile_collector"
        ),
        "arctura_metrics_seen": _truthy_nested(status, "prometheus", "arctura_metrics_seen"),
        "grafana_dashboard_imported": _truthy_nested(status, "grafana", "dashboard_imported"),
        "grafana_dashboard_uid": (
            isinstance(grafana, dict) and grafana.get("dashboard_uid") == EXPECTED_DASHBOARD_UID
        ),
        "grafana_export_or_screenshot_attached": _truthy_nested(
            status, "grafana", "export_or_screenshot_attached"
        ),
        "alertmanager_configured": _truthy_nested(status, "alertmanager", "configured"),
        "alertmanager_test_notification_delivered": _truthy_nested(
            status, "alertmanager", "test_notification_delivered"
        ),
        "no_placeholders": not _contains_placeholder(status),
    }
    findings = {
        "placeholder_present": _contains_placeholder(status),
        "dashboard_uid": grafana.get("dashboard_uid") if isinstance(grafana, dict) else None,
    }
    return {
        "audit_type": "monitoring_readiness_audit",
        "ok": all(checks.values()),
        "checks": checks,
        "findings": findings,
        "safety": {
            "dry_run_only": True,
            "docker_action_attempted": False,
            "aws_action_attempted": False,
            "network_probe_attempted": False,
            "wallet_required": False,
            "requires_separate_operator_approval": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Audit Arctura monitoring status JSON without probing services."
    )
    parser.add_argument(
        "--status",
        type=Path,
        default=Path("deploy/monitoring/monitoring-status.example.json"),
        help="Path to monitoring status JSON.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    report = audit_status(load_status(args.status))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
