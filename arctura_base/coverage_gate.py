"""Evaluate launch-critical coverage reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

DEFAULT_MODULES = (
    "arctura_base/utils.py",
    "arctura_base/incentive.py",
    "arctura_base/payload_validation.py",
    "arctura_base/base_rpc.py",
    "neurons/miner.py",
    "neurons/validator.py",
)


def load_coverage_json(path: Path) -> dict[str, Any]:
    """Load coverage.py JSON output."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def evaluate_coverage_gate(
    coverage: dict[str, Any],
    *,
    modules: tuple[str, ...] = DEFAULT_MODULES,
    minimum_percent: float = 100.0,
) -> dict[str, Any]:
    """Return a machine-readable launch coverage gate report."""
    files = coverage.get("files", {})
    module_reports: list[dict[str, Any]] = []
    missing_modules: list[str] = []

    for module in modules:
        file_report = files.get(module)
        if file_report is None:
            missing_modules.append(module)
            module_reports.append(
                {
                    "module": module,
                    "covered_percent": 0.0,
                    "missing": "coverage entry missing",
                    "ok": False,
                }
            )
            continue
        summary = file_report.get("summary", {})
        covered_percent = float(summary.get("percent_covered", 0.0))
        module_reports.append(
            {
                "module": module,
                "covered_percent": round(covered_percent, 3),
                "missing_lines": file_report.get("missing_lines", []),
                "ok": covered_percent >= minimum_percent,
            }
        )

    return {
        "ok": all(item["ok"] for item in module_reports),
        "minimum_percent": minimum_percent,
        "missing_modules": missing_modules,
        "modules": module_reports,
        "safety": {
            "dry_run_only": True,
            "on_chain_action_attempted": False,
            "wallet_required": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate launch-critical coverage gate.")
    parser.add_argument("--coverage-json", type=Path, default=Path("coverage.json"))
    parser.add_argument("--minimum-percent", type=float, default=100.0)
    parser.add_argument("--module", action="append", dest="modules")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = evaluate_coverage_gate(
        load_coverage_json(args.coverage_json),
        modules=tuple(args.modules) if args.modules else DEFAULT_MODULES,
        minimum_percent=args.minimum_percent,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
