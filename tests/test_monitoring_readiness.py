"""Monitoring readiness audit tests."""

import json
from pathlib import Path

from arctura_base.monitoring_readiness import audit_status, main

ROOT = Path(__file__).resolve().parents[1]
STATUS_EXAMPLE = ROOT / "deploy" / "monitoring" / "monitoring-status.example.json"


def green_status() -> dict:
    return {
        "schema_version": 1,
        "environment": "finney-mainnet",
        "collected_at": "2026-08-24T01:00:00Z",
        "prometheus": {
            "targets_healthy": True,
            "node_exporter_textfile_collector": True,
            "arctura_metrics_seen": True,
            "status_export": "runs/mainnet-evidence/prometheus-targets-20260824.json",
        },
        "grafana": {
            "dashboard_imported": True,
            "dashboard_uid": "arctura-launch-readiness",
            "export_or_screenshot_attached": True,
            "evidence": "runs/mainnet-evidence/grafana-dashboard-20260824.png",
        },
        "alertmanager": {
            "configured": True,
            "test_notification_delivered": True,
            "receiver": "launch-ops",
            "evidence": "runs/mainnet-evidence/alertmanager-test-20260824.json",
        },
    }


def test_example_monitoring_status_fails_without_external_actions() -> None:
    audit = audit_status(json.loads(STATUS_EXAMPLE.read_text(encoding="utf-8")))

    assert audit["audit_type"] == "monitoring_readiness_audit"
    assert audit["ok"] is False
    assert audit["checks"]["prometheus_targets_healthy"] is False
    assert audit["checks"]["alertmanager_test_notification_delivered"] is False
    assert audit["checks"]["no_placeholders"] is False
    assert audit["safety"]["docker_action_attempted"] is False
    assert audit["safety"]["network_probe_attempted"] is False
    assert audit["safety"]["wallet_required"] is False


def test_green_monitoring_status_passes_without_probing_services() -> None:
    audit = audit_status(green_status())

    assert audit["ok"] is True
    assert all(audit["checks"].values())
    assert audit["safety"]["dry_run_only"] is True


def test_monitoring_status_rejects_wrong_dashboard_uid() -> None:
    status = green_status()
    status["grafana"]["dashboard_uid"] = "wrong-dashboard"

    audit = audit_status(status)

    assert audit["ok"] is False
    assert audit["checks"]["grafana_dashboard_uid"] is False


def test_cli_writes_monitoring_audit(tmp_path) -> None:
    output = tmp_path / "monitoring-audit.json"

    exit_code = main(["--status", str(STATUS_EXAMPLE), "--output", str(output)])

    assert exit_code == 1
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["audit_type"] == "monitoring_readiness_audit"
    assert rendered["safety"]["docker_action_attempted"] is False
