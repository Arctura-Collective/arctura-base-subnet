from __future__ import annotations

import json

from arctura_base.cloudwatch_metrics import DEFAULT_NAMESPACE, render_metric_data


def sample_report() -> dict:
    return {
        "ok": False,
        "checks": {"duration": False},
        "metrics": {
            "elapsed_hours": 1.25,
            "attestations": 2,
            "weight_commits": 1,
            "health_passes": 12,
            "miner_restarts": 0,
            "validator_restarts": 1,
            "fatal_counts": {
                "Traceback (most recent call last)": 0,
                "RuntimeError": 2,
            },
        },
        "run": {"collected_at": "2026-08-24T00:27:37Z"},
    }


def test_render_metric_data_contains_required_launch_metrics() -> None:
    payload = render_metric_data(sample_report(), environment="testnet-505")
    by_name = {metric["MetricName"]: metric for metric in payload}

    assert DEFAULT_NAMESPACE == "Arctura/Launch"
    assert set(by_name) == {
        "EvidenceGateOk",
        "EvidenceElapsedHours",
        "Attestations",
        "HealthPasses",
        "WeightCommits",
        "MinerRestarts",
        "ValidatorRestarts",
        "FatalMarkers",
    }
    assert by_name["EvidenceGateOk"]["Value"] == 0.0
    assert by_name["EvidenceElapsedHours"]["Value"] == 1.25
    assert by_name["EvidenceElapsedHours"]["Unit"] == "None"
    assert by_name["FatalMarkers"]["Value"] == 2.0
    assert by_name["ValidatorRestarts"]["Value"] == 1.0
    assert by_name["EvidenceGateOk"]["Dimensions"] == [
        {"Name": "Environment", "Value": "testnet-505"}
    ]
    assert by_name["EvidenceGateOk"]["Timestamp"] == "2026-08-24T00:27:37+00:00"


def test_metric_payload_is_aws_cli_json_list() -> None:
    payload = render_metric_data(sample_report())
    rendered = json.dumps(payload)

    assert rendered.startswith("[")
    assert "put-metric-data" not in rendered
    assert "aws cloudwatch" not in rendered
