#!/usr/bin/env python3
"""Create a non-claiming evidence template for an authorized local testnet run."""

from __future__ import annotations

import argparse
from pathlib import Path

from arctura_base.evidence import write_testnet_evidence_template


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface for a bounded evidence template."""
    parser = argparse.ArgumentParser(
        description="Create a blank testnet evidence template; it records no run outcome."
    )
    parser.add_argument("--output", type=Path, required=True, help="New JSON template path.")
    parser.add_argument("--network", default="test", help="Bittensor network identifier.")
    parser.add_argument("--netuid", type=int, required=True, help="Bittensor subnet UID.")
    parser.add_argument("--run-id", help="Optional operator-supplied run identifier.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Write one non-overwriting evidence template and print its path."""
    args = build_parser().parse_args(argv)
    output_path = write_testnet_evidence_template(
        args.output, network=args.network, netuid=args.netuid, run_id=args.run_id
    )
    print(f"Created non-claiming evidence template: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
