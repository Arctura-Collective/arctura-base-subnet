"""Tests for testnet evidence templates and the sustained launch gate."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from arctura_base.evidence import (
    build_testnet_evidence_template,
    evaluate_evidence,
    log_from_marker,
    nonzero_weight_commits,
    parse_timestamp,
    validator_cycle_latencies,
    weight_cooldown_deferrals,
    write_testnet_evidence_template,
)


def test_template_records_scope_without_claiming_an_outcome():
    template = build_testnet_evidence_template(network="test", netuid=505, run_id="run-505-a")

    assert template["publication_state"] == "template"
    assert template["run"]["network"] == "test"
    assert template["run"]["netuid"] == 505
    assert template["run"]["id"] == "run-505-a"
    assert all(value is None for value in template["observations"].values())
    assert "not evidence" in template["claim_boundary"]


def test_template_writer_refuses_to_overwrite_an_existing_artifact(tmp_path):
    output = tmp_path / "evidence.json"
    write_testnet_evidence_template(output, network="test", netuid=505)

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["run"]["netuid"] == 505

    with pytest.raises(FileExistsError):
        write_testnet_evidence_template(output, network="test", netuid=505)


def test_evidence_passes_complete_48_hour_run():
    started = datetime(2026, 6, 17, tzinfo=timezone.utc)
    report = evaluate_evidence(
        started_at=started,
        now=started + timedelta(hours=49),
        miner_log="Arctura Base miner live\nMandate attested\n" * 2,
        validator_log=(
            "Arctura Base validator live\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=0.750\n"
        ),
        health_log='{"ok": true}\n' * 576,
        miner_restarts=0,
        validator_restarts=0,
    )

    assert report["ok"] is True
    assert all(report["checks"].values())
    assert report["metrics"]["health_passes"] == 576
    assert report["metrics"]["validator_cycles"] == 0


def test_log_from_marker_keeps_full_log_when_marker_is_missing():
    assert log_from_marker("Traceback\ninitializing", "live") == "Traceback\ninitializing"


def test_startup_traceback_before_live_marker_does_not_fail_gate():
    started = datetime(2026, 6, 17, tzinfo=timezone.utc)
    report = evaluate_evidence(
        started_at=started,
        now=started + timedelta(hours=49),
        miner_log=(
            "Traceback (most recent call last)\n"
            "websockets.exceptions.ConnectionClosedError\n"
            "Arctura Base miner live\n"
            "Mandate attested\n"
        ),
        validator_log=(
            "Traceback (most recent call last)\n"
            "websockets.exceptions.ConnectionClosedError\n"
            "Arctura Base validator live\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
        ),
        health_log='{"ok": true}\n' * 576,
        miner_restarts=0,
        validator_restarts=0,
    )

    assert report["checks"]["no_fatal_errors"] is True
    assert report["metrics"]["fatal_counts"]["Traceback (most recent call last)"] == 0


@pytest.mark.parametrize(
    ("override", "failed_check"),
    [
        ({"now_offset": 47}, "duration"),
        (
            {"miner_log": "Arctura Base miner live\nTraceback (most recent call last)"},
            "no_fatal_errors",
        ),
        (
            {
                "validator_log": (
                    "Arctura Base validator live\n"
                    "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
                )
            },
            "weight_commits",
        ),
        (
            {
                "validator_log": (
                    "Arctura Base validator live\n"
                    "Weights set | miners=1 | top_uid=1 | top_weight=0.000\n"
                    "Weights set | miners=1 | top_uid=1 | top_weight=0.000\n"
                )
            },
            "weight_commits",
        ),
        ({"health_log": '{"ok": true}\n' * 569}, "health_samples"),
        ({"miner_restarts": 1}, "restart_budget"),
    ],
)
def test_evidence_fails_incomplete_or_unhealthy_run(override, failed_check):
    started = datetime(2026, 6, 17, tzinfo=timezone.utc)
    values = {
        "started_at": started,
        "now": started + timedelta(hours=49),
        "miner_log": "Arctura Base miner live\nMandate attested",
        "validator_log": (
            "Arctura Base validator live\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
        ),
        "health_log": '{"ok": true}\n' * 576,
        "miner_restarts": 0,
        "validator_restarts": 0,
    }
    override = dict(override)
    now_offset = override.pop("now_offset", None)
    values.update(override)
    if now_offset is not None:
        values["now"] = started + timedelta(hours=now_offset)

    report = evaluate_evidence(**values)

    assert report["ok"] is False
    assert report["checks"][failed_check] is False


def test_validator_cycle_latencies_from_journal_markers():
    log = "\n".join(
        [
            "\x1b[34m2026-08-23 17:17:36.745\x1b[39m | INFO | Issuing mandate | id=abc",
            "\x1b[34m2026-08-23 17:17:39.115\x1b[39m | INFO | Tempo complete | sleeping 4320s",
            "2026-08-23 18:29:41.000 | INFO | Issuing mandate | id=def",
            "2026-08-23 18:29:45.250 | INFO | Tempo complete | sleeping 4320s",
        ]
    )

    assert validator_cycle_latencies(log) == [2.37, 4.25]


def test_nonzero_weight_commits_require_positive_top_weight():
    log = "\n".join(
        [
            "Weights set | miners=1 | top_uid=1 | top_weight=1.000",
            "Weights set | miners=1 | top_uid=1 | top_weight=0.000",
            "Weights set without explicit top weight",
        ]
    )

    assert nonzero_weight_commits(log) == 1


def test_weight_cooldown_deferrals_report_remaining_block_gap():
    log = "\n".join(
        [
            "Weight submission deferred by chain cooldown | "
            "uid=2 | blocks_since_last_update=20 | weights_rate_limit=100",
            "Weight submission deferred by chain cooldown | "
            "uid=2 | blocks_since_last_update=101 | weights_rate_limit=100",
        ]
    )

    assert weight_cooldown_deferrals(log) == [
        {
            "uid": 2,
            "blocks_since_last_update": 20,
            "weights_rate_limit": 100,
            "blocks_until_next_allowed": 81,
        },
        {
            "uid": 2,
            "blocks_since_last_update": 101,
            "weights_rate_limit": 100,
            "blocks_until_next_allowed": 0,
        },
    ]


def test_evidence_reports_validator_cycle_latency_metrics():
    started = datetime(2026, 6, 17, tzinfo=timezone.utc)
    report = evaluate_evidence(
        started_at=started,
        now=started + timedelta(hours=49),
        miner_log="Arctura Base miner live\nMandate attested\n",
        validator_log=(
            "Arctura Base validator live\n"
            "2026-08-23 17:17:36.000 | INFO | Issuing mandate | id=abc\n"
            "2026-08-23 17:17:39.500 | INFO | Tempo complete | sleeping 4320s\n"
            "Weight submission deferred by chain cooldown | "
            "uid=2 | blocks_since_last_update=20 | weights_rate_limit=100\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
            "Weights set | miners=1 | top_uid=1 | top_weight=0.750\n"
        ),
        health_log='{"ok": true}\n' * 576,
        miner_restarts=0,
        validator_restarts=0,
    )

    assert report["metrics"]["validator_cycles"] == 1
    assert report["metrics"]["validator_cycle_latest_seconds"] == 3.5
    assert report["metrics"]["validator_cycle_max_seconds"] == 3.5
    assert report["metrics"]["weight_commits"] == 2
    assert report["metrics"]["weight_commit_markers"] == 2
    assert report["metrics"]["weight_cooldown_deferrals"] == 1
    assert report["metrics"]["latest_weight_cooldown"] == {
        "uid": 2,
        "blocks_since_last_update": 20,
        "weights_rate_limit": 100,
        "blocks_until_next_allowed": 81,
    }


def test_parse_timestamp_requires_timezone():
    with pytest.raises(ValueError, match="timezone"):
        parse_timestamp("2026-06-19T00:00:00")
