"""Dry-run readiness audit for AWS Auto Scaling launch inputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PLACEHOLDER_PATTERNS = (
    re.compile(r"\bami-0{8,}\b"),
    re.compile(r"\bsg-0{8,}\b"),
    re.compile(r"\bsubnet-0{8,}\b"),
    re.compile(r"\bexample\.com\b", re.IGNORECASE),
    re.compile(r"\bREPLACE\b", re.IGNORECASE),
    re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE),
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
)
SECRET_MARKERS = ("coldkey", "mnemonic", "private_key", "secret_access_key", "seed_phrase")
ASSIGNMENT_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")
STRING_PATTERN = re.compile(r'"([^"]*)"')


def _strip_comment(line: str) -> str:
    """Remove simple HCL comments from one line."""
    in_quote = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == '"' and (index == 0 or line[index - 1] != "\\"):
            in_quote = not in_quote
        if not in_quote and char == "#":
            return line[:index]
        if not in_quote and line[index : index + 2] == "//":
            return line[:index]
        index += 1
    return line


def parse_tfvars(text: str) -> dict[str, Any]:
    """Parse the subset of Terraform tfvars syntax used by the ASG template."""
    values: dict[str, Any] = {}
    for line in text.splitlines():
        line = _strip_comment(line).strip()
        if not line:
            continue
        match = ASSIGNMENT_PATTERN.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        raw_value = raw_value.strip().rstrip(",")
        if raw_value.startswith("[") and raw_value.endswith("]"):
            values[key] = STRING_PATTERN.findall(raw_value)
        elif raw_value.startswith('"') and raw_value.endswith('"'):
            values[key] = raw_value[1:-1]
        elif raw_value.lower() in {"true", "false"}:
            values[key] = raw_value.lower() == "true"
        else:
            try:
                values[key] = int(raw_value)
            except ValueError:
                values[key] = raw_value
    return values


def _contains_placeholder(value: object) -> bool:
    rendered = json.dumps(value, sort_keys=True)
    return any(pattern.search(rendered) for pattern in PLACEHOLDER_PATTERNS)


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_string_list(value: object, *, minimum: int = 1) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= minimum
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and value > 0


def _minimum_int(value: object, minimum: int) -> bool:
    return isinstance(value, int) and value >= minimum


def audit_tfvars(text: str) -> dict[str, Any]:
    """Return a non-mutating AWS ASG readiness audit for Terraform tfvars."""
    values = parse_tfvars(text)
    alertmanager_webhook_url = values.get("alertmanager_webhook_url", "")
    miner_min_size = values.get("miner_min_size", 1)
    miner_desired_capacity = values.get("miner_desired_capacity", miner_min_size)
    miner_max_size = values.get("miner_max_size", 3)
    miner_port = values.get("miner_port", 8091)
    root_volume_size_gb = values.get("root_volume_size_gb", 200)
    lower_text = text.lower()
    secret_markers = [marker for marker in SECRET_MARKERS if marker in lower_text]

    checks = {
        "bt_netuid_positive": _positive_int(values.get("bt_netuid")),
        "miner_ami_id_present": _non_empty_string(values.get("miner_ami_id")),
        "instance_profile_present": _non_empty_string(values.get("instance_profile_name")),
        "security_groups_present": _non_empty_string_list(values.get("security_group_ids")),
        "subnets_present": _non_empty_string_list(values.get("subnet_ids"), minimum=2),
        "alertmanager_webhook_https": (
            isinstance(alertmanager_webhook_url, str)
            and alertmanager_webhook_url.startswith("https://")
        ),
        "alertmanager_webhook_api_path": (
            isinstance(alertmanager_webhook_url, str)
            and alertmanager_webhook_url.endswith("/api/v2/alerts")
        ),
        "miner_capacity_bounds": (
            isinstance(miner_min_size, int)
            and isinstance(miner_desired_capacity, int)
            and isinstance(miner_max_size, int)
            and 1 <= miner_min_size <= miner_desired_capacity <= miner_max_size
        ),
        "miner_port_valid": isinstance(miner_port, int) and 1024 <= miner_port <= 65535,
        "root_volume_size_gb_at_least_200": _minimum_int(root_volume_size_gb, 200),
        "no_placeholders": not _contains_placeholder(values),
        "no_secret_markers": not secret_markers,
    }
    return {
        "audit_type": "aws_asg_tfvars_readiness_audit",
        "ok": all(checks.values()),
        "checks": checks,
        "findings": {
            "placeholder_fields": [
                key for key, value in sorted(values.items()) if _contains_placeholder(value)
            ],
            "secret_markers": secret_markers,
            "parsed_fields": sorted(values),
        },
        "safety": {
            "dry_run_only": True,
            "aws_action_attempted": False,
            "terraform_action_attempted": False,
            "wallet_required": False,
            "requires_separate_operator_approval": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Audit Arctura AWS ASG terraform.tfvars without calling AWS or Terraform."
    )
    parser.add_argument(
        "--tfvars",
        type=Path,
        default=Path("deploy/aws/asg/terraform.tfvars.example"),
        help="Path to terraform.tfvars or terraform.tfvars.example.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    report = audit_tfvars(args.tfvars.read_text(encoding="utf-8"))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
