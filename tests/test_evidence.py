"""Sustained testnet evidence gate tests."""

from datetime import datetime, timedelta, timezone

import pytest

from arctura_base.evidence import evaluate_evidence, parse_timestamp


def test_evidence_passes_complete_48_hour_run():
    started = datetime(2026, 6, 17, tzinfo=timezone.utc)
    report = evaluate_evidence(
        started_at=started,
        now=started + timedelta(hours=49),
        miner_log="Arctura Base miner live\nMandate attested\n" * 2,
        validator_log="Arctura Base validator live\nWeights set\n",
        health_log='{"ok": true}\n' * 576,
        miner_restarts=0,
        validator_restarts=1,
    )

    assert report["ok"] is True
    assert all(report["checks"].values())
    assert report["metrics"]["health_passes"] == 576


@pytest.mark.parametrize(
    ("override", "failed_check"),
    [
        ({"now_offset": 47}, "duration"),
        (
            {"miner_log": "Arctura Base miner live\nTraceback (most recent call last)"},
            "no_fatal_errors",
        ),
        ({"validator_log": "Arctura Base validator live"}, "weight_commits"),
        ({"health_log": '{"ok": true}\n' * 10}, "health_samples"),
        ({"miner_restarts": 4}, "restart_budget"),
    ],
)
def test_evidence_fails_incomplete_or_unhealthy_run(override, failed_check):
    started = datetime(2026, 6, 17, tzinfo=timezone.utc)
    values = {
        "started_at": started,
        "now": started + timedelta(hours=49),
        "miner_log": "Arctura Base miner live\nMandate attested",
        "validator_log": "Arctura Base validator live\nWeights set",
        "health_log": '{"ok": true}\n' * 576,
        "miner_restarts": 0,
        "validator_restarts": 0,
    }
    now_offset = override.pop("now_offset", None)
    values.update(override)
    if now_offset is not None:
        values["now"] = started + timedelta(hours=now_offset)

    report = evaluate_evidence(**values)

    assert report["ok"] is False
    assert report["checks"][failed_check] is False


def test_parse_timestamp_requires_timezone():
    with pytest.raises(ValueError, match="timezone"):
        parse_timestamp("2026-06-19T00:00:00")
