from __future__ import annotations

from datetime import datetime, timezone

from arctura_base.metrics_export import render_collector_error, render_prometheus, write_textfile


def sample_report() -> dict:
    return {
        "ok": False,
        "checks": {
            "duration": False,
            "attestations": True,
            "weight_commits": True,
        },
        "metrics": {
            "elapsed_hours": 1.25,
            "attestations": 2,
            "weight_commits": 1,
            "health_passes": 12,
            "miner_restarts": 0,
            "validator_restarts": 1,
            "fatal_counts": {
                "Traceback (most recent call last)": 0,
                "uncaught exception": 0,
            },
        },
        "run": {
            "started_at": "2026-08-23T15:34:42-07:00",
            "services": {
                "arctura-miner": {
                    "ActiveState": "active",
                    "ActiveEnterTimestamp": "2026-08-23T15:31:18-07:00",
                },
                "arctura-validator": {
                    "ActiveState": "active",
                    "ActiveEnterTimestamp": "2026-08-23T15:34:42-07:00",
                },
            },
        },
    }


def test_render_prometheus_contains_launch_metrics() -> None:
    rendered = render_prometheus(
        sample_report(),
        collected_at=datetime(2026, 8, 23, 23, 0, tzinfo=timezone.utc),
    )

    assert "arctura_evidence_collector_ok 1" in rendered
    assert "arctura_evidence_gate_ok 0" in rendered
    assert 'arctura_evidence_check_pass{check="duration"} 0' in rendered
    assert "arctura_evidence_elapsed_hours 1.25" in rendered
    assert "arctura_attestations_total 2" in rendered
    assert 'arctura_service_restarts_total{service="arctura-validator"} 1' in rendered
    assert 'arctura_service_active{service="arctura-miner"} 1' in rendered
    assert "arctura_evidence_started_at_seconds 1787524482" in rendered


def test_render_collector_error_sanitizes_label() -> None:
    rendered = render_collector_error('bad "service"\nfailed')

    assert "arctura_evidence_collector_ok 0" in rendered
    assert 'error="bad_service_failed"' in rendered


def test_write_textfile_replaces_existing_file(tmp_path) -> None:
    output = tmp_path / "metrics" / "arctura.prom"

    write_textfile(output, "first\n")
    write_textfile(output, "second\n")

    assert output.read_text(encoding="utf-8") == "second\n"


def test_render_prometheus_parses_systemd_display_timestamps() -> None:
    report = sample_report()
    miner = report["run"]["services"]["arctura-miner"]
    miner["ActiveEnterTimestamp"] = "Sun 2026-08-23 15:31:18 PDT"

    rendered = render_prometheus(report)

    assert 'arctura_service_started_at_seconds{service="arctura-miner"} 1787524278' in rendered
