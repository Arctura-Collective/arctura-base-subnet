"""Tests for systemd evidence collection."""

import subprocess
from datetime import datetime, timezone

import pytest

from arctura_base.evidence_collect import collect, parse_systemd_timestamp


def completed(command, stdout):
    return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


def test_collect_writes_complete_evidence_bundle(tmp_path):
    started = "2026-06-17T00:00:00+00:00"

    def runner(command):
        if command[0] == "systemctl":
            return completed(
                command,
                f"ActiveEnterTimestamp={started}\nNRestarts=0\nActiveState=active\n",
            )
        service = command[command.index("-u") + 1]
        logs = {
            "arctura-miner": "Arctura Base miner live\nMandate attested\n",
            "arctura-validator": (
                "Arctura Base validator live\n"
                "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
                "Weights set | miners=1 | top_uid=1 | top_weight=0.750\n"
            ),
            "arctura-health": '{"ok": true}\n' * 576,
        }
        return completed(command, logs[service])

    report = collect(
        tmp_path,
        runner=runner,
        now=datetime(2026, 6, 19, 1, tzinfo=timezone.utc),
    )

    assert report["ok"] is True
    assert report["run"]["started_at"] == started
    assert (tmp_path / "miner.log").is_file()
    assert (tmp_path / "validator.log").is_file()
    assert (tmp_path / "health.log").is_file()
    assert (tmp_path / "report.json").is_file()


def test_collect_preserves_each_service_start_marker(tmp_path):
    starts = {
        "arctura-miner": "2026-06-16T23:55:00+00:00",
        "arctura-validator": "2026-06-17T00:00:00+00:00",
    }
    journal_since = {}

    def runner(command):
        service = command[command.index("-u") + 1] if "-u" in command else command[3]
        if command[0] == "systemctl":
            return completed(
                command,
                f"ActiveEnterTimestamp={starts[service]}\nNRestarts=0\nActiveState=active\n",
            )
        journal_since[service] = command[command.index("--since") + 1]
        logs = {
            "arctura-miner": "Arctura Base miner live\nMandate attested\n",
            "arctura-validator": (
                "Arctura Base validator live\n"
                "Weights set | miners=1 | top_uid=1 | top_weight=1.000\n"
                "Weights set | miners=1 | top_uid=1 | top_weight=0.750\n"
            ),
            "arctura-health": '{"ok": true}\n' * 576,
        }
        return completed(command, logs[service])

    report = collect(
        tmp_path,
        runner=runner,
        now=datetime(2026, 6, 19, 1, tzinfo=timezone.utc),
    )

    assert report["ok"] is True
    assert report["run"]["started_at"] == starts["arctura-validator"]
    assert journal_since["arctura-miner"] == starts["arctura-miner"]
    assert journal_since["arctura-validator"] == starts["arctura-validator"]


def test_collect_rejects_inactive_service(tmp_path):
    def runner(command):
        return completed(
            command,
            "ActiveEnterTimestamp=2026-06-17T00:00:00+00:00\nNRestarts=0\nActiveState=failed\n",
        )

    with pytest.raises(RuntimeError, match="not active"):
        collect(tmp_path, runner=runner)


def test_collect_rejects_missing_service_fields(tmp_path):
    def runner(command):
        return completed(command, "ActiveState=active\n")

    with pytest.raises(RuntimeError, match="missing ActiveEnterTimestamp"):
        collect(tmp_path, runner=runner)


def test_parse_systemd_display_timestamp():
    parsed = parse_systemd_timestamp("Fri 2026-06-20 12:34:56 PDT")

    assert parsed.isoformat() == "2026-06-20T12:34:56-07:00"


def test_parse_systemd_timestamp_rejects_unavailable_value():
    with pytest.raises(ValueError, match="unavailable"):
        parse_systemd_timestamp("n/a")
