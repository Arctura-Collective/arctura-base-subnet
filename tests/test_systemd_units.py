"""Deployment unit safety and restart policy tests."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEMD = ROOT / "deploy" / "systemd"


def test_neuron_units_restart_and_load_protected_environment():
    for name in ("arctura-miner.service", "arctura-validator.service"):
        unit = (SYSTEMD / name).read_text(encoding="utf-8")
        assert "EnvironmentFile=%h/.config/arctura-base-subnet.env" in unit
        assert "Restart=always" in unit
        assert "NoNewPrivileges=true" in unit
        assert "PrivateTmp=true" in unit
        assert '--subtensor.network "$BT_NETWORK"' in unit
        assert '--netuid "$BT_NETUID"' in unit


def test_health_timer_runs_frequently_and_persists():
    timer = (SYSTEMD / "arctura-health.timer").read_text(encoding="utf-8")
    service = (SYSTEMD / "arctura-health.service").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=5min" in timer
    assert "Persistent=true" in timer
    assert "arctura_base.cli preflight" in service
    assert "--json" in service


def test_metrics_timer_exports_prometheus_textfile():
    timer = (SYSTEMD / "arctura-metrics.timer").read_text(encoding="utf-8")
    service = (SYSTEMD / "arctura-metrics.service").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=1min" in timer
    assert "Persistent=true" in timer
    assert "EnvironmentFile=%h/.config/arctura-base-subnet.env" in service
    assert "scripts/export_prometheus_metrics.py" in service
    assert "NoNewPrivileges=true" in service
    assert "PrivateTmp=true" in service


def test_operator_example_contains_no_secret_values():
    example = (SYSTEMD / "operator.env.example").read_text(encoding="utf-8")
    assert "PRIVATE_KEY" not in example
    assert "MNEMONIC" not in example
    assert "ARCTURA_REPO=/absolute/path" in example
