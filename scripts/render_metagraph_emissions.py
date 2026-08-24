#!/usr/bin/env python3
"""Render a manual Arctura metagraph emissions snapshot as Prometheus metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from arctura_base.metrics_export import render_metagraph_emissions, write_textfile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a manually collected metagraph/emissions snapshot."
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Optional Prometheus textfile output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    content = render_metagraph_emissions(json.loads(args.snapshot.read_text(encoding="utf-8")))
    if args.output:
        write_textfile(args.output, content)
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
