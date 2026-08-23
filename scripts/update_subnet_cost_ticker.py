#!/usr/bin/env python3
"""Update the static subnet launch cost ticker data."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_OUTPUT = Path("docs/data/subnet_launch_cost.json")
TAO_AMOUNT_PATTERN = re.compile(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:TAO|tao|τ)")


def parse_tao_amount(output: str) -> Decimal:
    """Extract the first TAO amount from btcli output."""
    cleaned = output.replace("\u200e", "").replace("\u200f", "")
    match = TAO_AMOUNT_PATTERN.search(cleaned)
    if not match:
        raise ValueError(f"No TAO amount found in output: {output!r}")
    try:
        return Decimal(match.group(1).replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid TAO amount in output: {output!r}") from exc


def build_payload(
    *,
    cost_tao: Decimal,
    network: str,
    command: list[str],
    raw_output: str,
    collected_at: datetime | None = None,
) -> dict[str, object]:
    """Build a stable JSON payload for the static ticker page."""
    observed_at = collected_at or datetime.now(timezone.utc)
    cost_text = format(cost_tao.normalize(), "f")
    return {
        "schema_version": 1,
        "ok": True,
        "network": network,
        "cost_tao": cost_text,
        "cost_label": f"{cost_text} TAO",
        "source": " ".join(command),
        "raw_output": raw_output.strip(),
        "collected_at": observed_at.isoformat().replace("+00:00", "Z"),
        "warning": (
            "Planning signal only. Re-check live burn cost within 30 minutes of any "
            "Finney registration and require explicit operator approval before spend."
        ),
    }


def run_burn_cost(command: list[str]) -> tuple[Decimal, str]:
    """Run btcli and return the parsed subnet registration cost."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode != 0:
        raise RuntimeError(output.strip() or f"Command failed with exit code {result.returncode}")
    return parse_tao_amount(output), output


def write_payload(output: Path, payload: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh static subnet launch-cost ticker data.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON output path.")
    parser.add_argument("--network", default="finney", help="Bittensor network to query.")
    parser.add_argument(
        "--command",
        nargs="+",
        help="Override the burn-cost command. Defaults to btcli subnet burn_cost.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command or ["btcli", "subnet", "burn_cost", "--subtensor.network", args.network]
    cost_tao, raw_output = run_burn_cost(command)
    payload = build_payload(
        cost_tao=cost_tao,
        network=args.network,
        command=command,
        raw_output=raw_output,
    )
    write_payload(args.output, payload)
    print(f"Wrote {args.output}: {payload['cost_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
