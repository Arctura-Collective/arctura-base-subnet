"""Prometheus textfile metrics for Arctura launch monitoring."""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from arctura_base.evidence import parse_timestamp

LABEL_VALUE_PATTERN = re.compile(r"[^a-zA-Z0-9_.:-]+")


def _bool(value: object) -> float:
    return 1.0 if bool(value) else 0.0


def _format_value(value: float | int) -> str:
    number = float(value)
    if math.isfinite(number) and number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def _label_value(value: object) -> str:
    cleaned = LABEL_VALUE_PATTERN.sub("_", str(value))[:120]
    return cleaned.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "_")


def _sample(name: str, value: float | int, labels: dict[str, object] | None = None) -> str:
    if not labels:
        return f"{name} {_format_value(value)}"
    rendered = ",".join(f'{key}="{_label_value(label)}"' for key, label in sorted(labels.items()))
    return f"{name}{{{rendered}}} {_format_value(value)}"


def _timestamp_seconds(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(parse_timestamp(value).timestamp())
    except ValueError:
        fields = value.split()
        if len(fields) != 4:
            return 0
        try:
            parsed = datetime.strptime(" ".join(fields[1:3]), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return 0
        offsets = {"UTC": 0, "GMT": 0, "PST": -8, "PDT": -7}
        if fields[3] not in offsets:
            return 0
        aware = parsed.replace(tzinfo=timezone(timedelta(hours=offsets[fields[3]])))
        return int(aware.timestamp())


def _metric_number(value: object, field_name: str) -> float:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a decimal value") from exc
    if parsed.is_nan() or parsed < 0:
        raise ValueError(f"{field_name} must be a non-negative decimal value")
    return float(parsed)


def render_metagraph_emissions(snapshot: dict[str, Any]) -> str:
    """Render a manually collected metagraph/emissions snapshot as Prometheus metrics."""
    if int(snapshot.get("schema_version", 0)) != 1:
        raise ValueError("metagraph emissions snapshot schema_version must be 1")
    network = str(snapshot.get("network", "")).strip()
    netuid = str(snapshot.get("netuid", "")).strip()
    collected_at = str(snapshot.get("collected_at", "")).strip()
    if not network:
        raise ValueError("network is required")
    if not netuid:
        raise ValueError("netuid is required")
    if not collected_at:
        raise ValueError("collected_at is required")

    emissions = snapshot.get("emissions", {})
    labels: dict[str, object] = {"network": network, "netuid": netuid}
    lines = [
        "# HELP arctura_metagraph_snapshot_available Whether a metagraph emissions snapshot was rendered.",
        "# TYPE arctura_metagraph_snapshot_available gauge",
        _sample("arctura_metagraph_snapshot_available", 1, labels),
        "# HELP arctura_metagraph_snapshot_collected_at_seconds Unix timestamp for the metagraph emissions snapshot.",
        "# TYPE arctura_metagraph_snapshot_collected_at_seconds gauge",
        _sample(
            "arctura_metagraph_snapshot_collected_at_seconds",
            _timestamp_seconds(collected_at),
            labels,
        ),
    ]
    if "tao_per_day" in emissions:
        tao_per_day = _metric_number(emissions["tao_per_day"], "emissions.tao_per_day")
        lines.extend(
            [
                "# HELP arctura_network_emission_tao_per_day Observed subnet TAO emissions per day.",
                "# TYPE arctura_network_emission_tao_per_day gauge",
                _sample("arctura_network_emission_tao_per_day", tao_per_day, labels),
            ]
        )
        treasury_share = _metric_number(snapshot.get("treasury_share", "0.18"), "treasury_share")
        lines.extend(
            [
                "# HELP arctura_treasury_emission_tao_per_day Expected treasury TAO emissions per day using the configured treasury share.",
                "# TYPE arctura_treasury_emission_tao_per_day gauge",
                _sample(
                    "arctura_treasury_emission_tao_per_day",
                    tao_per_day * treasury_share,
                    labels,
                ),
            ]
        )
    if "alpha_per_day" in emissions:
        lines.extend(
            [
                "# HELP arctura_network_emission_alpha_per_day Observed subnet alpha emissions per day.",
                "# TYPE arctura_network_emission_alpha_per_day gauge",
                _sample(
                    "arctura_network_emission_alpha_per_day",
                    _metric_number(emissions["alpha_per_day"], "emissions.alpha_per_day"),
                    labels,
                ),
            ]
        )
    return "\n".join(lines) + "\n"


def render_prometheus(report: dict[str, Any], *, collected_at: datetime | None = None) -> str:
    """Render an evidence report as Prometheus textfile metrics."""
    observed_at = collected_at or datetime.now(timezone.utc)
    lines = [
        "# HELP arctura_evidence_collector_ok Whether the metrics exporter rendered a report.",
        "# TYPE arctura_evidence_collector_ok gauge",
        _sample("arctura_evidence_collector_ok", 1),
        "# HELP arctura_evidence_gate_ok Whether all launch evidence checks passed.",
        "# TYPE arctura_evidence_gate_ok gauge",
        _sample("arctura_evidence_gate_ok", _bool(report.get("ok"))),
        "# HELP arctura_evidence_collected_at_seconds Unix timestamp when metrics were rendered.",
        "# TYPE arctura_evidence_collected_at_seconds gauge",
        _sample("arctura_evidence_collected_at_seconds", int(observed_at.timestamp())),
    ]

    checks = report.get("checks", {})
    lines.extend(
        [
            "# HELP arctura_evidence_check_pass Launch evidence check result by check name.",
            "# TYPE arctura_evidence_check_pass gauge",
        ]
    )
    for name, passed in sorted(checks.items()):
        lines.append(_sample("arctura_evidence_check_pass", _bool(passed), {"check": name}))

    metrics = report.get("metrics", {})
    scalar_metrics = {
        "elapsed_hours": "arctura_evidence_elapsed_hours",
        "attestations": "arctura_attestations_total",
        "weight_commits": "arctura_weight_commits_total",
        "health_passes": "arctura_health_passes_total",
    }
    lines.extend(
        [
            "# HELP arctura_evidence_elapsed_hours Elapsed hours in the current evidence window.",
            "# TYPE arctura_evidence_elapsed_hours gauge",
            _sample("arctura_evidence_elapsed_hours", float(metrics.get("elapsed_hours", 0))),
            "# HELP arctura_attestations_total Attestations observed in the current evidence window.",
            "# TYPE arctura_attestations_total counter",
            _sample("arctura_attestations_total", int(metrics.get("attestations", 0))),
            "# HELP arctura_weight_commits_total Weight commits observed in the current evidence window.",
            "# TYPE arctura_weight_commits_total counter",
            _sample("arctura_weight_commits_total", int(metrics.get("weight_commits", 0))),
            "# HELP arctura_health_passes_total Passing health samples in the current evidence window.",
            "# TYPE arctura_health_passes_total counter",
            _sample("arctura_health_passes_total", int(metrics.get("health_passes", 0))),
            "# HELP arctura_validator_cycles_total Completed validator mandate cycles in the evidence window.",
            "# TYPE arctura_validator_cycles_total counter",
            _sample("arctura_validator_cycles_total", int(metrics.get("validator_cycles", 0))),
            "# HELP arctura_validator_cycle_latest_seconds Latest validator mandate cycle latency.",
            "# TYPE arctura_validator_cycle_latest_seconds gauge",
            _sample(
                "arctura_validator_cycle_latest_seconds",
                float(metrics.get("validator_cycle_latest_seconds", 0)),
            ),
            "# HELP arctura_validator_cycle_max_seconds Maximum validator mandate cycle latency in the evidence window.",
            "# TYPE arctura_validator_cycle_max_seconds gauge",
            _sample(
                "arctura_validator_cycle_max_seconds",
                float(metrics.get("validator_cycle_max_seconds", 0)),
            ),
        ]
    )
    # Keep the explicit mapping above near the HELP text; this guard catches
    # accidental metric-name drift in future edits.
    assert set(scalar_metrics) == {
        "elapsed_hours",
        "attestations",
        "weight_commits",
        "health_passes",
    }

    lines.extend(
        [
            "# HELP arctura_service_restarts_total Systemd restart count by neuron service.",
            "# TYPE arctura_service_restarts_total counter",
            _sample(
                "arctura_service_restarts_total",
                int(metrics.get("miner_restarts", 0)),
                {"service": "arctura-miner"},
            ),
            _sample(
                "arctura_service_restarts_total",
                int(metrics.get("validator_restarts", 0)),
                {"service": "arctura-validator"},
            ),
            "# HELP arctura_fatal_markers_total Fatal journal marker count by marker.",
            "# TYPE arctura_fatal_markers_total counter",
        ]
    )
    for marker, count in sorted(metrics.get("fatal_counts", {}).items()):
        lines.append(_sample("arctura_fatal_markers_total", int(count), {"marker": marker}))

    run = report.get("run", {})
    services = run.get("services", {})
    lines.extend(
        [
            "# HELP arctura_service_active Whether a systemd service is active.",
            "# TYPE arctura_service_active gauge",
            "# HELP arctura_service_started_at_seconds Unix timestamp for current service activation.",
            "# TYPE arctura_service_started_at_seconds gauge",
        ]
    )
    for service, props in sorted(services.items()):
        lines.append(
            _sample(
                "arctura_service_active",
                _bool(props.get("ActiveState") == "active"),
                {"service": service},
            )
        )
        lines.append(
            _sample(
                "arctura_service_started_at_seconds",
                _timestamp_seconds(props.get("ActiveEnterTimestamp")),
                {"service": service},
            )
        )

    lines.extend(
        [
            "# HELP arctura_evidence_started_at_seconds Unix timestamp for formal evidence window.",
            "# TYPE arctura_evidence_started_at_seconds gauge",
            _sample(
                "arctura_evidence_started_at_seconds", _timestamp_seconds(run.get("started_at"))
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def render_collector_error(error: str, *, collected_at: datetime | None = None) -> str:
    """Render a Prometheus-compatible failure report."""
    observed_at = collected_at or datetime.now(timezone.utc)
    return (
        "\n".join(
            [
                "# HELP arctura_evidence_collector_ok Whether the metrics exporter rendered a report.",
                "# TYPE arctura_evidence_collector_ok gauge",
                _sample("arctura_evidence_collector_ok", 0),
                "# HELP arctura_evidence_collector_error_info Last collector error label.",
                "# TYPE arctura_evidence_collector_error_info gauge",
                _sample("arctura_evidence_collector_error_info", 1, {"error": error}),
                "# HELP arctura_evidence_collected_at_seconds Unix timestamp when metrics were rendered.",
                "# TYPE arctura_evidence_collected_at_seconds gauge",
                _sample("arctura_evidence_collected_at_seconds", int(observed_at.timestamp())),
            ]
        )
        + "\n"
    )


def write_textfile(path: Path, content: str) -> Path:
    """Atomically write a Prometheus textfile collector payload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)
    return path
