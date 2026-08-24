"""AWS ASG tfvars readiness audit tests."""

import json
from pathlib import Path

from arctura_base.aws_readiness import audit_tfvars, main, parse_tfvars

ROOT = Path(__file__).resolve().parents[1]
TFVARS_EXAMPLE = ROOT / "deploy" / "aws" / "asg" / "terraform.tfvars.example"


def test_parse_tfvars_reads_strings_numbers_and_lists() -> None:
    values = parse_tfvars("""
        bt_netuid = 505
        miner_ami_id = "ami-1234567890abcdef0"
        security_group_ids = ["sg-1234567890abcdef0", "sg-11111111111111111"]
        """)

    assert values == {
        "bt_netuid": 505,
        "miner_ami_id": "ami-1234567890abcdef0",
        "security_group_ids": ["sg-1234567890abcdef0", "sg-11111111111111111"],
    }


def test_example_tfvars_audit_fails_placeholders_without_aws_actions() -> None:
    audit = audit_tfvars(TFVARS_EXAMPLE.read_text(encoding="utf-8"))

    assert audit["audit_type"] == "aws_asg_tfvars_readiness_audit"
    assert audit["ok"] is False
    assert audit["checks"]["bt_netuid_positive"] is False
    assert audit["checks"]["root_volume_size_gb_at_least_200"] is True
    assert audit["checks"]["no_placeholders"] is False
    assert "miner_ami_id" in audit["findings"]["placeholder_fields"]
    assert "security_group_ids" in audit["findings"]["placeholder_fields"]
    assert "subnet_ids" in audit["findings"]["placeholder_fields"]
    assert "alertmanager_webhook_url" in audit["findings"]["placeholder_fields"]
    assert audit["safety"]["aws_action_attempted"] is False
    assert audit["safety"]["terraform_action_attempted"] is False


def test_realistic_tfvars_audit_passes_without_calling_aws_or_terraform() -> None:
    audit = audit_tfvars("""
        bt_netuid = 505
        miner_ami_id = "ami-1234567890abcdef0"
        instance_profile_name = "arctura-ec2-runtime"
        security_group_ids = ["sg-1234567890abcdef0"]
        subnet_ids = ["subnet-1234567890abcdef0", "subnet-abcdef1234567890a"]
        alertmanager_webhook_url = "https://alerts.arctura.invalid/api/v2/alerts"
        miner_min_size = 1
        miner_desired_capacity = 2
        miner_max_size = 3
        miner_port = 8191
        root_volume_size_gb = 200
        """)

    assert audit["ok"] is True
    assert all(audit["checks"].values())


def test_tfvars_audit_rejects_small_root_volume() -> None:
    audit = audit_tfvars("""
        bt_netuid = 505
        miner_ami_id = "ami-1234567890abcdef0"
        instance_profile_name = "arctura-ec2-runtime"
        security_group_ids = ["sg-1234567890abcdef0"]
        subnet_ids = ["subnet-1234567890abcdef0", "subnet-abcdef1234567890a"]
        alertmanager_webhook_url = "https://alerts.arctura.invalid/api/v2/alerts"
        root_volume_size_gb = 100
        """)

    assert audit["ok"] is False
    assert audit["checks"]["root_volume_size_gb_at_least_200"] is False


def test_tfvars_audit_flags_secret_markers() -> None:
    audit = audit_tfvars("""
        bt_netuid = 505
        miner_ami_id = "ami-1234567890abcdef0"
        instance_profile_name = "arctura-ec2-runtime"
        security_group_ids = ["sg-1234567890abcdef0"]
        subnet_ids = ["subnet-1234567890abcdef0", "subnet-abcdef1234567890a"]
        alertmanager_webhook_url = "https://alerts.arctura.invalid/api/v2/alerts"
        # coldkey mnemonic should never be present here
        """)

    assert audit["ok"] is False
    assert audit["checks"]["no_secret_markers"] is False
    assert "coldkey" in audit["findings"]["secret_markers"]
    assert "mnemonic" in audit["findings"]["secret_markers"]


def test_cli_writes_aws_asg_audit(tmp_path) -> None:
    output = tmp_path / "audit.json"

    exit_code = main(["--tfvars", str(TFVARS_EXAMPLE), "--output", str(output)])

    assert exit_code == 1
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["audit_type"] == "aws_asg_tfvars_readiness_audit"
    assert rendered["safety"]["dry_run_only"] is True
