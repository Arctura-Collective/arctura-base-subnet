"""Evaluate sustained testnet logs against the mainnet launch gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FATAL_MARKERS = ("Traceback (most recent call last)", "uncaught exception", "CRITICAL")


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and require timezone awareness."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def read_log(path: Path) -> str:
    """Read an exported journal as UTF-8 text."""
    return path.read_text(encoding="utf-8", errors="replace")


def evaluate_evidence(
    *,
    started_at: datetime,
    now: datetime,
    miner_log: str,
    validator_log: str,
    health_log: str,
    miner_restarts: int,
    validator_restarts: int,
    minimum_hours: float = 48.0,
    minimum_health_checks: int = 500,
    maximum_restarts: int = 3,
) -> dict[str, Any]:
    """Return a machine-readable launch-gate report."""
    elapsed_hours = max(0.0, (now - started_at).total_seconds() / 3600)
    combined = "\n".join((miner_log, validator_log, health_log))
    fatal_counts = {marker: combined.lower().count(marker.lower()) for marker in FATAL_MARKERS}
    attestations = miner_log.count("Mandate attested")
    weight_commits = validator_log.count("Weights set")
    health_passes = health_log.count('"ok": true')

    checks = {
        "duration": elapsed_hours >= minimum_hours,
        "miner_started": "Arctura Base miner live" in miner_log,
        "validator_started": "Arctura Base validator live" in validator_log,
        "attestations": attestations > 0,
        "weight_commits": weight_commits > 0,
        "health_samples": health_passes >= minimum_health_checks,
        "restart_budget": max(miner_restarts, validator_restarts) <= maximum_restarts,
        "no_fatal_errors": not any(fatal_counts.values()),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "metrics": {
            "elapsed_hours": round(elapsed_hours, 3),
            "attestations": attestations,
            "weight_commits": weight_commits,
            "health_passes": health_passes,
            "miner_restarts": miner_restarts,
            "validator_restarts": validator_restarts,
            "fatal_counts": fatal_counts,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the sustained testnet launch gate.")
    parser.add_argument("--started-at", required=True, help="Timezone-aware ISO-8601 run start.")
    parser.add_argument("--miner-log", type=Path, required=True)
    parser.add_argument("--validator-log", type=Path, required=True)
    parser.add_argument("--health-log", type=Path, required=True)
    parser.add_argument("--miner-restarts", type=int, required=True)
    parser.add_argument("--validator-restarts", type=int, required=True)
    parser.add_argument("--minimum-hours", type=float, default=48.0)
    parser.add_argument("--minimum-health-checks", type=int, default=500)
    parser.add_argument("--maximum-restarts", type=int, default=3)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = evaluate_evidence(
        started_at=parse_timestamp(args.started_at),
        now=datetime.now(timezone.utc),
        miner_log=read_log(args.miner_log),
        validator_log=read_log(args.validator_log),
        health_log=read_log(args.health_log),
        miner_restarts=args.miner_restarts,
        validator_restarts=args.validator_restarts,
        minimum_hours=args.minimum_hours,
        minimum_health_checks=args.minimum_health_checks,
        maximum_restarts=args.maximum_restarts,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
