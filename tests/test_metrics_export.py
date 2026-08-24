from __future__ import annotations

from datetime import datetime, timezone

import pytest

from arctura_base.metrics_export import (
    render_collector_error,
    render_metagraph_emissions,
    render_prometheus,
    write_textfile,
)


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
            "weight_commit_markers": 2,
            "weight_cooldown_deferrals": 1,
            "latest_weight_cooldown": {
                "uid": 2,
                "blocks_since_last_update": 20,
                "weights_rate_limit": 100,
                "blocks_until_next_allowed": 81,
            },
            "health_passes": 12,
            "miner_restarts": 0,
            "validator_restarts": 1,
            "validator_cycles": 3,
            "validator_cycle_latest_seconds": 2.37,
            "validator_cycle_max_seconds": 9.5,
            "fatal_counts": {
                "Traceback (most recent call last)": 0,
                "uncaught exception": 0,
            },
        },
        "remaining": {
            "hours": 47.012,
            "health_samples": 540,
            "weight_commits": 2,
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
    assert "arctura_weight_commit_markers_total 2" in rendered
    assert "arctura_weight_cooldown_deferrals_total 1" in rendered
    assert 'arctura_latest_weight_cooldown_blocks_since_last_update{uid="2"} 20' in rendered
    assert 'arctura_latest_weight_cooldown_rate_limit{uid="2"} 100' in rendered
    assert 'arctura_latest_weight_cooldown_blocks_until_allowed{uid="2"} 81' in rendered
    assert "arctura_remaining_launch_hours 47.012" in rendered
    assert "arctura_remaining_health_samples 540" in rendered
    assert "arctura_remaining_weight_commits 2" in rendered
    assert "arctura_validator_cycles_total 3" in rendered
    assert "arctura_validator_cycle_latest_seconds 2.37" in rendered
    assert "arctura_validator_cycle_max_seconds 9.5" in rendered
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


def test_render_metagraph_emissions_contains_network_and_treasury_metrics() -> None:
    rendered = render_metagraph_emissions(
        {
            "schema_version": 1,
            "network": "finney",
            "netuid": 505,
            "collected_at": "2026-08-24T00:00:00Z",
            "treasury_share": "0.18",
            "emissions": {
                "tao_per_day": "12.5",
                "alpha_per_day": "240",
            },
        }
    )

    assert 'arctura_metagraph_snapshot_available{netuid="505",network="finney"} 1' in rendered
    assert (
        'arctura_metagraph_snapshot_collected_at_seconds{netuid="505",network="finney"} 1787529600'
    ) in rendered
    assert 'arctura_network_emission_tao_per_day{netuid="505",network="finney"} 12.5' in rendered
    assert 'arctura_treasury_emission_tao_per_day{netuid="505",network="finney"} 2.25' in rendered
    assert 'arctura_network_emission_alpha_per_day{netuid="505",network="finney"} 240' in rendered


def test_render_metagraph_emissions_rejects_bad_snapshot() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        render_metagraph_emissions({"schema_version": 2})
