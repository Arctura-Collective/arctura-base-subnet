"""Dry-run readiness audit for key custody and final approval proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

PLACEHOLDER_MARKERS = ("REPLACE", "TODO", "TBD", "PLACEHOLDER", "example.com")


def load_status(path: Path) -> dict[str, Any]:
    """Load a custody status JSON file."""
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _contains_placeholder(value: object) -> bool:
    rendered = json.dumps(value, sort_keys=True).upper()
    return any(marker.upper() in rendered for marker in PLACEHOLDER_MARKERS)


def _truthy_nested(status: dict[str, Any], section: str, field: str) -> bool:
    value = status.get(section, {})
    return isinstance(value, dict) and value.get(field) is True


def _minimum_reviewers(status: dict[str, Any], minimum: int = 2) -> bool:
    review = status.get("review", {})
    reviewers = review.get("reviewers") if isinstance(review, dict) else None
    return isinstance(reviewers, list) and len(reviewers) >= minimum


def audit_status(status: dict[str, Any]) -> dict[str, Any]:
    """Return a non-mutating custody readiness audit."""
    checks = {
        "schema_version": status.get("schema_version") == 1,
        "owner_coldkey_offline": _truthy_nested(status, "owner_coldkey", "offline"),
        "owner_not_operational_hot_wallet": _truthy_nested(
            status, "owner_coldkey", "not_operational_hot_wallet"
        ),
        "owner_backups_two_locations": _truthy_nested(
            status, "owner_coldkey", "backups_two_physical_locations"
        ),
        "validator_coldkey_offline": _truthy_nested(status, "validator_coldkey", "offline"),
        "miner_coldkey_offline": _truthy_nested(status, "miner_coldkey", "offline"),
        "servers_hold_hotkeys_only": _truthy_nested(status, "runtime_hosts", "hotkeys_only"),
        "hotkey_revocation_path_documented": _truthy_nested(
            status, "runtime_hosts", "hotkey_revocation_path_documented"
        ),
        "treasury_multisig_controlled": _truthy_nested(
            status, "treasury", "multisig_or_governance_controlled"
        ),
        "minimum_two_reviewers": _minimum_reviewers(status),
        "wallet_names_reviewed": _truthy_nested(status, "review", "wallet_names_reviewed"),
        "network_and_commands_reviewed": _truthy_nested(
            status, "review", "network_and_commands_reviewed"
        ),
        "approval_packet_recorded": _truthy_nested(status, "review", "approval_packet_recorded"),
        "no_placeholders": not _contains_placeholder(status),
    }
    review = status.get("review", {})
    reviewers = review.get("reviewers") if isinstance(review, dict) else None
    return {
        "audit_type": "custody_readiness_audit",
        "ok": all(checks.values()),
        "checks": checks,
        "findings": {
            "placeholder_present": _contains_placeholder(status),
            "reviewer_count": len(reviewers) if isinstance(reviewers, list) else 0,
        },
        "safety": {
            "dry_run_only": True,
            "wallet_required": False,
            "secret_inspection_attempted": False,
            "on_chain_action_attempted": False,
            "requires_separate_operator_approval": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Audit Arctura custody status JSON without inspecting keys."
    )
    parser.add_argument(
        "--status",
        type=Path,
        default=Path("deploy/custody/custody-status.example.json"),
        help="Path to custody status JSON.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    report = audit_status(load_status(args.status))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
