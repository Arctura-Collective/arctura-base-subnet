"""Dry-run treasury emission distribution planner.

This module deliberately does not import Bittensor wallet APIs, sign
transactions, submit extrinsics, or move funds. It converts a governance-approved
emission policy into an unsigned plan that multisig operators can review before
separate hardware-wallet approval.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DECIMAL_PLACES = Decimal("0.000000001")
PLACEHOLDER_MARKERS = ("REPLACE", "TODO", "TBD", "PLACEHOLDER")


@dataclass(frozen=True)
class Allocation:
    """One treasury allocation target."""

    name: str
    share: Decimal
    destination_kind: str
    destination: str


@dataclass(frozen=True)
class TreasuryPolicy:
    """Governance policy used to build an unsigned distribution plan."""

    schema_version: int
    policy_name: str
    dry_run_only: bool
    treasury_share_of_subnet_emissions: Decimal
    min_signers: int
    timelock_hours: int
    allocations: tuple[Allocation, ...]


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a decimal value") from exc
    if parsed.is_nan() or parsed < 0:
        raise ValueError(f"{field_name} must be a non-negative decimal value")
    return parsed


def _contains_placeholder(value: str) -> bool:
    upper_value = value.upper()
    return any(marker in upper_value for marker in PLACEHOLDER_MARKERS)


def load_policy(path: Path) -> TreasuryPolicy:
    """Load a treasury policy JSON file."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    allocations = tuple(
        Allocation(
            name=str(item["name"]),
            share=_decimal(item["share"], f"allocations.{index}.share"),
            destination_kind=str(item["destination_kind"]),
            destination=str(item["destination"]),
        )
        for index, item in enumerate(raw.get("allocations", []))
    )

    return TreasuryPolicy(
        schema_version=int(raw["schema_version"]),
        policy_name=str(raw["policy_name"]),
        dry_run_only=bool(raw["dry_run_only"]),
        treasury_share_of_subnet_emissions=_decimal(
            raw["treasury_share_of_subnet_emissions"],
            "treasury_share_of_subnet_emissions",
        ),
        min_signers=int(raw["min_signers"]),
        timelock_hours=int(raw["timelock_hours"]),
        allocations=allocations,
    )


def validate_policy(policy: TreasuryPolicy, *, allow_placeholders: bool = False) -> None:
    """Raise ValueError when a treasury policy is unsafe or internally invalid."""
    if policy.schema_version != 1:
        raise ValueError("schema_version must be 1")
    if not policy.policy_name:
        raise ValueError("policy_name is required")
    if not policy.dry_run_only:
        raise ValueError("policy must be dry_run_only=true")
    if policy.treasury_share_of_subnet_emissions != Decimal("0.18"):
        raise ValueError("treasury_share_of_subnet_emissions must equal 0.18")
    if policy.min_signers < 2:
        raise ValueError("min_signers must be at least 2")
    if policy.timelock_hours < 24:
        raise ValueError("timelock_hours must be at least 24")
    if not policy.allocations:
        raise ValueError("at least one allocation is required")

    share_sum = sum((allocation.share for allocation in policy.allocations), Decimal("0"))
    if share_sum not in {Decimal("1.00"), Decimal("1")}:
        raise ValueError(f"allocation shares must sum to 1.00, got {share_sum}")

    names = set()
    for allocation in policy.allocations:
        if not allocation.name:
            raise ValueError("allocation name is required")
        if allocation.name in names:
            raise ValueError(f"duplicate allocation name: {allocation.name}")
        names.add(allocation.name)
        if allocation.share <= 0:
            raise ValueError(f"allocation {allocation.name} share must be positive")
        if not allocation.destination_kind:
            raise ValueError(f"allocation {allocation.name} destination_kind is required")
        if not allocation.destination:
            raise ValueError(f"allocation {allocation.name} destination is required")
        if _contains_placeholder(allocation.destination) and not allow_placeholders:
            raise ValueError(
                f"allocation {allocation.name} destination still contains a placeholder"
            )


def audit_policy(policy: TreasuryPolicy, *, allow_placeholders: bool = False) -> dict[str, Any]:
    """Return a non-mutating governance readiness audit for a treasury policy."""
    allocation_names = [allocation.name for allocation in policy.allocations]
    duplicate_names = sorted(
        {name for name in allocation_names if allocation_names.count(name) > 1}
    )
    placeholder_allocations = [
        allocation.name
        for allocation in policy.allocations
        if _contains_placeholder(allocation.destination)
    ]
    share_sum = sum((allocation.share for allocation in policy.allocations), Decimal("0"))
    checks = {
        "schema_version": policy.schema_version == 1,
        "policy_name": bool(policy.policy_name),
        "dry_run_only": policy.dry_run_only is True,
        "treasury_share": policy.treasury_share_of_subnet_emissions == Decimal("0.18"),
        "min_signers": policy.min_signers >= 2,
        "timelock": policy.timelock_hours >= 24,
        "allocations_present": bool(policy.allocations),
        "allocation_shares_sum": share_sum in {Decimal("1.00"), Decimal("1")},
        "allocation_names_unique": not duplicate_names,
        "allocation_destinations_present": all(
            bool(allocation.destination) for allocation in policy.allocations
        ),
        "allocation_destinations_final": allow_placeholders or not placeholder_allocations,
    }
    return {
        "audit_type": "treasury_policy_readiness_audit",
        "policy_name": policy.policy_name,
        "ok": all(checks.values()),
        "checks": checks,
        "findings": {
            "duplicate_allocation_names": duplicate_names,
            "placeholder_allocations": placeholder_allocations,
            "share_sum": str(share_sum),
        },
        "requirements": {
            "dry_run_only": True,
            "treasury_share_of_subnet_emissions": "0.18",
            "min_signers_at_least": 2,
            "timelock_hours_at_least": 24,
            "placeholder_destinations_allowed": allow_placeholders,
        },
        "safety": {
            "on_chain_action_attempted": False,
            "wallet_required": False,
            "requires_separate_multisig_approval": True,
        },
    }


def build_distribution_plan(
    policy: TreasuryPolicy,
    *,
    total_treasury_tao: Decimal,
    allow_placeholders: bool = False,
) -> dict[str, Any]:
    """Build an unsigned dry-run distribution plan."""
    validate_policy(policy, allow_placeholders=allow_placeholders)
    if total_treasury_tao <= 0:
        raise ValueError("total_treasury_tao must be positive")

    allocations: list[dict[str, str]] = []
    allocated = Decimal("0")
    for index, allocation in enumerate(policy.allocations):
        if index == len(policy.allocations) - 1:
            amount = total_treasury_tao - allocated
        else:
            amount = (total_treasury_tao * allocation.share).quantize(
                DECIMAL_PLACES,
                rounding=ROUND_DOWN,
            )
            allocated += amount

        allocations.append(
            {
                "name": allocation.name,
                "share": str(allocation.share),
                "amount_tao": str(amount.quantize(DECIMAL_PLACES)),
                "destination_kind": allocation.destination_kind,
                "destination": allocation.destination,
            }
        )

    return {
        "plan_type": "unsigned_treasury_distribution_dry_run",
        "policy_name": policy.policy_name,
        "dry_run_only": True,
        "total_treasury_tao": str(total_treasury_tao.quantize(DECIMAL_PLACES)),
        "treasury_share_of_subnet_emissions": str(policy.treasury_share_of_subnet_emissions),
        "min_signers": policy.min_signers,
        "timelock_hours": policy.timelock_hours,
        "safety": {
            "on_chain_action_attempted": False,
            "wallet_required": False,
            "requires_separate_multisig_approval": True,
        },
        "allocations": allocations,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Build an unsigned dry-run Arctura treasury distribution plan."
    )
    parser.add_argument("--policy", type=Path, required=True, help="Treasury policy JSON file.")
    parser.add_argument(
        "--total-tao",
        help="Treasury intake amount in TAO. Required unless --audit-only is used.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the generated unsigned distribution plan JSON.",
    )
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Allow placeholder destinations when validating example policies.",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Render a non-mutating policy readiness audit instead of a distribution plan.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    policy = load_policy(args.policy)
    if args.audit_only:
        output = audit_policy(policy, allow_placeholders=args.allow_placeholders)
    else:
        if args.total_tao is None:
            raise ValueError("--total-tao is required unless --audit-only is used")
        output = build_distribution_plan(
            policy,
            total_treasury_tao=_decimal(args.total_tao, "total_tao"),
            allow_placeholders=args.allow_placeholders,
        )
    rendered = json.dumps(output, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
