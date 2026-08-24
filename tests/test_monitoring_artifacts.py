"""Static checks for Prometheus and Grafana launch monitoring artifacts."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_prometheus_config_scrapes_node_exporter_textfile_metrics():
    config = (ROOT / "deploy" / "prometheus" / "prometheus.yml").read_text(encoding="utf-8")

    assert "job_name: arctura-node" in config
    assert "localhost:9100" in config
    assert "arctura-alerts.yml" in config
    assert 'regex: "arctura_.*"' in config


def test_alert_rules_cover_service_down_stale_metrics_and_weight_stall():
    rules = (ROOT / "deploy" / "prometheus" / "arctura-alerts.yml").read_text(encoding="utf-8")

    assert "ArcturaNeuronServiceDown" in rules
    assert "ArcturaMetricsStale" in rules
    assert "ArcturaWeightCommitStalled" in rules
    assert "arctura_weight_commits_total == 0" in rules


def test_grafana_dashboard_imports_and_references_exported_metrics():
    dashboard_path = ROOT / "deploy" / "grafana" / "arctura-launch-dashboard.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    serialized = json.dumps(dashboard)

    assert dashboard["uid"] == "arctura-launch-readiness"
    assert dashboard["title"] == "Arctura Launch Readiness"
    assert "DS_PROMETHEUS" in serialized
    for metric in (
        "arctura_evidence_gate_ok",
        "arctura_evidence_elapsed_hours",
        "arctura_evidence_check_pass",
        "arctura_health_passes_total",
        "arctura_attestations_total",
        "arctura_weight_commits_total",
        "arctura_service_active",
        "arctura_service_restarts_total",
    ):
        assert metric in serialized


def test_monitoring_docs_link_deployable_artifacts():
    docs = (ROOT / "docs" / "MONITORING_AND_METRICS.md").read_text(encoding="utf-8")

    assert "deploy/prometheus/prometheus.yml" in docs
    assert "deploy/prometheus/arctura-alerts.yml" in docs
    assert "deploy/grafana/arctura-launch-dashboard.json" in docs
    assert "deploy/monitoring/docker-compose.yml" in docs


def test_compose_monitoring_stack_wires_prometheus_node_exporter_and_grafana():
    compose = (ROOT / "deploy" / "monitoring" / "docker-compose.yml").read_text(encoding="utf-8")
    prometheus = (ROOT / "deploy" / "monitoring" / "prometheus.yml").read_text(encoding="utf-8")
    alertmanager = (ROOT / "deploy" / "monitoring" / "alertmanager.yml").read_text(encoding="utf-8")
    datasource = (
        ROOT
        / "deploy"
        / "monitoring"
        / "grafana"
        / "provisioning"
        / "datasources"
        / "prometheus.yml"
    ).read_text(encoding="utf-8")
    dashboards = (
        ROOT / "deploy" / "monitoring" / "grafana" / "provisioning" / "dashboards" / "arctura.yml"
    ).read_text(encoding="utf-8")

    assert "prom/prometheus" in compose
    assert "prom/alertmanager" in compose
    assert "prom/node-exporter" in compose
    assert "grafana/grafana" in compose
    assert "--collector.textfile.directory=/textfile" in compose
    assert "./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" in compose
    assert "../prometheus/arctura-alerts.yml" in compose
    assert "../grafana/arctura-launch-dashboard.json" in compose
    assert "alertmanager:9093" in prometheus
    assert "node-exporter:9100" in prometheus
    assert 'regex: "arctura_.*"' in prometheus
    assert "webhook_configs" in alertmanager
    assert "send_resolved: true" in alertmanager
    assert "http://prometheus:9090" in datasource
    assert "/var/lib/grafana/dashboards" in dashboards
