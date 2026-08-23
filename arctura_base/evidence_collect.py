"""Collect systemd journals and evaluate the sustained testnet gate."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from arctura_base.evidence import evaluate_evidence, parse_timestamp

SERVICES = ("arctura-miner", "arctura-validator")
Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def parse_systemd_timestamp(value: str) -> datetime:
    """Parse either an ISO timestamp or systemd's display timestamp."""
    if not value or value.lower() == "n/a":
        raise ValueError("systemd timestamp is unavailable")
    try:
        return parse_timestamp(value)
    except ValueError:
        fields = value.split()
        if len(fields) != 4:
            raise ValueError(f"unsupported systemd timestamp: {value}") from None
        parsed = datetime.strptime(" ".join(fields[1:3]), "%Y-%m-%d %H:%M:%S")
        offsets = {"UTC": 0, "GMT": 0, "PST": -8, "PDT": -7}
        if fields[3] not in offsets:
            raise ValueError(f"unsupported systemd timezone: {fields[3]}") from None
        return parsed.replace(tzinfo=timezone(timedelta(hours=offsets[fields[3]])))


def service_properties(service: str, runner: Runner = run) -> dict[str, str]:
    result = runner(
        [
            "systemctl",
            "--user",
            "show",
            service,
            "--property=ActiveEnterTimestamp,NRestarts,ActiveState",
        ]
    )
    properties = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value
    if properties.get("ActiveState") != "active":
        raise RuntimeError(f"{service} is not active")
    for key in ("ActiveEnterTimestamp", "NRestarts"):
        if not properties.get(key):
            raise RuntimeError(f"{service} is missing {key}")
    return properties


def journal(service: str, started_at: datetime, runner: Runner = run) -> str:
    result = runner(
        [
            "journalctl",
            "--user",
            "-u",
            service,
            "--since",
            started_at.astimezone(timezone.utc).isoformat(),
            "--no-pager",
            "--output=cat",
        ]
    )
    return result.stdout


def collect(output_dir: Path, runner: Runner = run, now: datetime | None = None) -> dict:
    """Write journals and a gate report, returning the report."""
    properties = {service: service_properties(service, runner) for service in SERVICES}
    starts = {
        service: parse_systemd_timestamp(properties[service]["ActiveEnterTimestamp"])
        for service in SERVICES
    }
    started_at = max(starts.values())
    logs = {
        # Preserve each current activation marker while anchoring the minimum
        # uninterrupted duration to the later neuron start.
        "miner": journal("arctura-miner", starts["arctura-miner"], runner),
        "validator": journal("arctura-validator", starts["arctura-validator"], runner),
        "health": journal("arctura-health", started_at, runner),
    }
    collected_at = now or datetime.now(timezone.utc)
    report = evaluate_evidence(
        started_at=started_at,
        now=collected_at,
        miner_log=logs["miner"],
        validator_log=logs["validator"],
        health_log=logs["health"],
        miner_restarts=int(properties["arctura-miner"]["NRestarts"]),
        validator_restarts=int(properties["arctura-validator"]["NRestarts"]),
    )
    report["run"] = {
        "started_at": started_at.isoformat(),
        "collected_at": collected_at.isoformat(),
        "services": properties,
        "journal_started_at": {
            service: timestamp.isoformat() for service, timestamp in starts.items()
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for role, content in logs.items():
        (output_dir / f"{role}.log").write_text(content, encoding="utf-8")
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect the supervised testnet evidence bundle.")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/mainnet-evidence"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = collect(args.output_dir)
    except (KeyError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
