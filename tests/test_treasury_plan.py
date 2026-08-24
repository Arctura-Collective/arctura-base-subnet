"""Treasury dry-run distribution planning tests."""

from decimal import Decimal
from pathlib import Path

import pytest

from arctura_base.treasury import build_distribution_plan, load_policy, main, validate_policy

POLICY_PATH = Path("deploy/treasury/emission_policy.example.json")


def test_example_policy_builds_unsigned_dry_run_plan():
    policy = load_policy(POLICY_PATH)

    plan = build_distribution_plan(
        policy,
        total_treasury_tao=Decimal("10"),
        allow_placeholders=True,
    )

    assert plan["plan_type"] == "unsigned_treasury_distribution_dry_run"
    assert plan["dry_run_only"] is True
    assert plan["safety"]["on_chain_action_attempted"] is False
    assert plan["safety"]["wallet_required"] is False
    assert plan["safety"]["requires_separate_multisig_approval"] is True
    assert [item["amount_tao"] for item in plan["allocations"]] == [
        "4.000000000",
        "3.000000000",
        "3.000000000",
    ]


def test_policy_rejects_placeholders_without_explicit_template_mode():
    policy = load_policy(POLICY_PATH)

    with pytest.raises(ValueError, match="placeholder"):
        validate_policy(policy)


def test_distribution_plan_rejects_bad_share_sum():
    policy = load_policy(POLICY_PATH)
    bad_policy = policy.__class__(
        schema_version=policy.schema_version,
        policy_name=policy.policy_name,
        dry_run_only=policy.dry_run_only,
        treasury_share_of_subnet_emissions=policy.treasury_share_of_subnet_emissions,
        min_signers=policy.min_signers,
        timelock_hours=policy.timelock_hours,
        allocations=(
            policy.allocations[0].__class__(
                name=policy.allocations[0].name,
                share=Decimal("0.99"),
                destination_kind=policy.allocations[0].destination_kind,
                destination="5F3sa2TJAWMqDhXG6jhV4N8ko9SxwGy8TpaNS1repoTEST000",
            ),
        ),
    )

    with pytest.raises(ValueError, match="shares must sum"):
        validate_policy(bad_policy)


def test_distribution_plan_rejects_non_dry_run_policy():
    policy = load_policy(POLICY_PATH)
    unsafe_policy = policy.__class__(
        schema_version=policy.schema_version,
        policy_name=policy.policy_name,
        dry_run_only=False,
        treasury_share_of_subnet_emissions=policy.treasury_share_of_subnet_emissions,
        min_signers=policy.min_signers,
        timelock_hours=policy.timelock_hours,
        allocations=policy.allocations,
    )

    with pytest.raises(ValueError, match="dry_run_only"):
        validate_policy(unsafe_policy, allow_placeholders=True)


def test_cli_writes_unsigned_plan(tmp_path):
    output = tmp_path / "plan.json"

    exit_code = main(
        [
            "--policy",
            str(POLICY_PATH),
            "--total-tao",
            "2.5",
            "--allow-placeholders",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    rendered = output.read_text(encoding="utf-8")
    assert "unsigned_treasury_distribution_dry_run" in rendered
    assert "on_chain_action_attempted" in rendered
