#!/usr/bin/env python3
"""Export Arctura launch evidence as Prometheus textfile metrics."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from arctura_base.evidence_collect import collect
from arctura_base.metrics_export import render_collector_error, render_prometheus, write_textfile


def default_output() -> Path:
    return Path.home() / ".local" / "share" / "arctura" / "metrics" / "arctura.prom"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write Arctura Prometheus textfile metrics.")
    parser.add_argument("--output", type=Path, default=default_output())
    parser.add_argument("--evidence-dir", type=Path, default=Path("runs/mainnet-evidence"))
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero if evidence collection fails or the launch gate is not yet green.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = collect(args.evidence_dir)
    except (KeyError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        content = render_collector_error(f"{type(exc).__name__}: {exc}")
        write_textfile(args.output, content)
        print(json.dumps({"ok": False, "metrics": str(args.output), "error": str(exc)}))
        return 2 if args.strict else 0

    write_textfile(args.output, render_prometheus(report))
    print(json.dumps({"ok": report["ok"], "metrics": str(args.output)}))
    return 0 if report["ok"] or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
