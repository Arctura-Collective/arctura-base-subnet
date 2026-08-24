"""Create bounded testnet records and evaluate sustained launch evidence."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FATAL_MARKERS = (
    "Traceback (most recent call last)",
    "uncaught exception",
    "CRITICAL",
    "SystemExit",
    "KeyboardInterrupt",
    "RuntimeError",
    "bittensor.errors",
)
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
LOG_TIMESTAMP_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)")
TOP_WEIGHT_PATTERN = re.compile(r"\btop_weight=([0-9]+(?:\.[0-9]+)?)\b")


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and require timezone awareness."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def read_log(path: Path) -> str:
    """Read an exported journal as UTF-8 text."""
    return path.read_text(encoding="utf-8", errors="replace")


def log_from_marker(log: str, marker: str) -> str:
    """
    Return log content from the first live marker onward.

    If the marker is absent, return the full log so missing-start failures do
    not hide fatal startup errors.
    """
    marker_index = log.find(marker)
    if marker_index == -1:
        return log
    return log[marker_index:]


def _parse_log_timestamp(line: str) -> datetime | None:
    cleaned = ANSI_ESCAPE_PATTERN.sub("", line)
    match = LOG_TIMESTAMP_PATTERN.match(cleaned)
    if not match:
        return None
    for timestamp_format in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(match.group(1), timestamp_format)
        except ValueError:
            continue
    return None


def validator_cycle_latencies(validator_log: str) -> list[float]:
    """Return seconds from mandate issue to tempo completion for validator cycles."""
    started_at: datetime | None = None
    latencies: list[float] = []
    for line in validator_log.splitlines():
        timestamp = _parse_log_timestamp(line)
        if timestamp is None:
            continue
        if "Issuing mandate" in line:
            started_at = timestamp
        elif "Tempo complete" in line and started_at is not None:
            latencies.append(round(max(0.0, (timestamp - started_at).total_seconds()), 3))
            started_at = None
        elif "Validator loop error" in line:
            started_at = None
    return latencies


def nonzero_weight_commits(validator_log: str) -> int:
    """Count successful weight commits that explicitly report a positive top weight."""
    commits = 0
    for line in validator_log.splitlines():
        if "Weights set" not in line:
            continue
        match = TOP_WEIGHT_PATTERN.search(line)
        if match and float(match.group(1)) > 0:
            commits += 1
    return commits


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
    minimum_health_checks: int = 570,
    minimum_weight_commits: int = 2,
    maximum_restarts: int = 0,
) -> dict[str, Any]:
    """Return a machine-readable launch-gate report."""
    elapsed_hours = max(0.0, (now - started_at).total_seconds() / 3600)
    miner_live_marker = "Arctura Base miner live"
    validator_live_marker = "Arctura Base validator live"
    fatal_window = "\n".join(
        (
            log_from_marker(miner_log, miner_live_marker),
            log_from_marker(validator_log, validator_live_marker),
            health_log,
        )
    )
    fatal_counts = {marker: fatal_window.lower().count(marker.lower()) for marker in FATAL_MARKERS}
    attestations = miner_log.count("Mandate attested")
    weight_commits = nonzero_weight_commits(validator_log)
    weight_commit_markers = validator_log.count("Weights set")
    health_passes = health_log.count('"ok": true')
    cycle_latencies = validator_cycle_latencies(validator_log)

    checks = {
        "duration": elapsed_hours >= minimum_hours,
        "miner_started": miner_live_marker in miner_log,
        "validator_started": validator_live_marker in validator_log,
        "attestations": attestations > 0,
        "weight_commits": weight_commits >= minimum_weight_commits,
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
            "weight_commit_markers": weight_commit_markers,
            "health_passes": health_passes,
            "miner_restarts": miner_restarts,
            "validator_restarts": validator_restarts,
            "fatal_counts": fatal_counts,
            "validator_cycles": len(cycle_latencies),
            "validator_cycle_latest_seconds": cycle_latencies[-1] if cycle_latencies else 0,
            "validator_cycle_max_seconds": max(cycle_latencies) if cycle_latencies else 0,
        },
    }


def build_testnet_evidence_template(
    *, network: str, netuid: int, run_id: str | None = None
) -> dict[str, Any]:
    """Build a template without asserting a testnet outcome."""
    return {
        "schema_version": "1.0",
        "record_type": "testnet_run_evidence",
        "publication_state": "template",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": {
            "id": run_id,
            "network": network,
            "netuid": netuid,
            "started_at": None,
            "ended_at": None,
            "command": None,
            "code_revision": None,
        },
        "observations": {
            "miner_live": None,
            "validator_live_loop": None,
            "mandate_issued": None,
            "concurrent_miner_response": None,
            "weight_submission": None,
        },
        "artifacts": {
            "metagraph_or_explorer_url": None,
            "immutable_log_url": None,
            "artifact_hash": None,
        },
        "claim_boundary": (
            "This is an incomplete template, not evidence of a completed run. "
            "Do not publish it as an observed testnet or mainnet result."
        ),
        "completion_requirements": [
            "UTC-bounded start and end timestamps",
            "network and netuid",
            "executed method or command",
            "code revision",
            "observed results and stated limitations",
            "an immutable log, artifact hash, or network reference where available",
        ],
    }


def write_testnet_evidence_template(
    output_path: Path, *, network: str, netuid: int, run_id: str | None = None
) -> Path:
    """Write a template record, refusing to overwrite an existing artifact."""
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing evidence artifact: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            build_testnet_evidence_template(network=network, netuid=netuid, run_id=run_id),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the sustained testnet launch gate.")
    parser.add_argument("--started-at", required=True, help="Timezone-aware ISO-8601 run start.")
    parser.add_argument("--miner-log", type=Path, required=True)
    parser.add_argument("--validator-log", type=Path, required=True)
    parser.add_argument("--health-log", type=Path, required=True)
    parser.add_argument("--miner-restarts", type=int, required=True)
    parser.add_argument("--validator-restarts", type=int, required=True)
    parser.add_argument("--minimum-hours", type=float, default=48.0)
    parser.add_argument("--minimum-health-checks", type=int, default=570)
    parser.add_argument("--minimum-weight-commits", type=int, default=2)
    parser.add_argument("--maximum-restarts", type=int, default=0)
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
        minimum_weight_commits=args.minimum_weight_commits,
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
