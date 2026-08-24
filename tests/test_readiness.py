"""Aggregate mainnet readiness audit tests."""

import json
from datetime import datetime, timezone

from arctura_base.readiness import build_readiness_audit, main


def green_evidence() -> dict:
    return {
        "ok": True,
        "checks": {"duration": True, "weight_commits": True},
        "metrics": {"elapsed_hours": 48.5, "weight_commits": 2},
        "remaining": {"hours": 0.0, "health_samples": 0, "weight_commits": 0},
        "run": {"collected_at": "2026-08-24T00:00:00Z"},
    }


def fresh_cost() -> dict:
    return {
        "ok": True,
        "network": "finney",
        "cost_tao": "686.125",
        "collected_at": "2026-08-24T00:05:00Z",
    }


def green_audit(kind: str) -> dict:
    return {
        "audit_type": kind,
        "ok": True,
        "checks": {"ready": True},
        "safety": {
            "dry_run_only": True,
            "aws_action_attempted": False,
            "terraform_action_attempted": False,
            "on_chain_action_attempted": False,
        },
    }


def test_readiness_audit_passes_only_when_all_sections_are_green() -> None:
    report = build_readiness_audit(
        evidence_report=green_evidence(),
        cost_payload=fresh_cost(),
        aws_audit=green_audit("aws"),
        monitoring_audit=green_audit("monitoring"),
        custody_audit=green_audit("custody"),
        treasury_audit=green_audit("treasury"),
        now=datetime(2026, 8, 24, 0, 10, tzinfo=timezone.utc),
    )

    assert report["audit_type"] == "arctura_mainnet_readiness_audit"
    assert report["ok"] is True
    assert report["blockers"] == []
    assert report["next_actions"] == {}
    assert report["safety"]["on_chain_action_attempted"] is False
    assert report["safety"]["aws_action_attempted"] is False
    assert report["safety"]["terraform_action_attempted"] is False
    assert report["safety"]["wallet_required"] is False


def test_readiness_audit_reports_section_blockers() -> None:
    evidence = green_evidence()
    evidence["ok"] = False
    cost = fresh_cost()
    cost["ok"] = False
    aws = green_audit("aws")
    aws["ok"] = False
    monitoring = green_audit("monitoring")
    monitoring["ok"] = False
    custody = green_audit("custody")
    custody["ok"] = False

    report = build_readiness_audit(
        evidence_report=evidence,
        cost_payload=cost,
        aws_audit=aws,
        monitoring_audit=monitoring,
        custody_audit=custody,
        treasury_audit=green_audit("treasury"),
        now=datetime(2026, 8, 24, 0, 10, tzinfo=timezone.utc),
    )

    assert report["ok"] is False
    assert report["blockers"] == ["evidence", "burn_cost", "aws_asg", "monitoring", "custody"]
    assert set(report["next_actions"]) == set(report["blockers"])
    assert "two non-zero validator weight commits" in report["next_actions"]["evidence"]
    assert "trusted btcli shell" in report["next_actions"]["burn_cost"]
    assert "Alertmanager test delivery" in report["next_actions"]["monitoring"]
    assert "burn-cost payload is unavailable" in report["sections"]["burn_cost"]["errors"]


def test_readiness_audit_rejects_stale_cost_even_with_green_evidence() -> None:
    report = build_readiness_audit(
        evidence_report=green_evidence(),
        cost_payload=fresh_cost(),
        aws_audit=green_audit("aws"),
        monitoring_audit=green_audit("monitoring"),
        custody_audit=green_audit("custody"),
        treasury_audit=green_audit("treasury"),
        now=datetime(2026, 8, 24, 1, 0, tzinfo=timezone.utc),
    )

    assert report["ok"] is False
    assert report["blockers"] == ["burn_cost"]
    assert list(report["next_actions"]) == ["burn_cost"]
    assert any("stale" in error for error in report["sections"]["burn_cost"]["errors"])


def test_cli_writes_readiness_audit(tmp_path) -> None:
    evidence = tmp_path / "evidence.json"
    cost = tmp_path / "cost.json"
    tfvars = tmp_path / "terraform.tfvars"
    treasury = tmp_path / "treasury.json"
    monitoring = tmp_path / "monitoring.json"
    custody = tmp_path / "custody.json"
    output = tmp_path / "readiness.json"

    evidence.write_text(json.dumps(green_evidence()), encoding="utf-8")
    cost.write_text(json.dumps(fresh_cost()), encoding="utf-8")
    tfvars.write_text(
        """
        bt_netuid = 505
        miner_ami_id = "ami-1234567890abcdef0"
        instance_profile_name = "arctura-ec2-runtime"
        security_group_ids = ["sg-1234567890abcdef0"]
        subnet_ids = ["subnet-1234567890abcdef0", "subnet-abcdef1234567890a"]
        alertmanager_webhook_url = "https://alerts.arctura.invalid/api/v2/alerts"
        miner_min_size = 1
        miner_desired_capacity = 1
        miner_max_size = 2
        miner_port = 8191
        """,
        encoding="utf-8",
    )
    treasury.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "policy_name": "launch",
                "dry_run_only": True,
                "treasury_share_of_subnet_emissions": "0.18",
                "min_signers": 2,
                "timelock_hours": 24,
                "allocations": [
                    {
                        "name": "core",
                        "share": "1.00",
                        "destination_kind": "multisig_safe",
                        "destination": "safe-mainnet-approved",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monitoring.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "environment": "finney-mainnet",
                "collected_at": "2026-08-24T00:00:00Z",
                "prometheus": {
                    "targets_healthy": True,
                    "node_exporter_textfile_collector": True,
                    "arctura_metrics_seen": True,
                    "status_export": "runs/mainnet-evidence/prometheus-targets.json",
                },
                "grafana": {
                    "dashboard_imported": True,
                    "dashboard_uid": "arctura-launch-readiness",
                    "export_or_screenshot_attached": True,
                    "evidence": "runs/mainnet-evidence/grafana.png",
                },
                "alertmanager": {
                    "configured": True,
                    "test_notification_delivered": True,
                    "receiver": "launch-ops",
                    "evidence": "runs/mainnet-evidence/alertmanager.json",
                },
            }
        ),
        encoding="utf-8",
    )
    custody.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "environment": "finney-mainnet",
                "reviewed_at": "2026-08-24T00:00:00Z",
                "owner_coldkey": {
                    "offline": True,
                    "not_operational_hot_wallet": True,
                    "backups_two_physical_locations": True,
                    "evidence": "secure-review/owner-custody-record.json",
                },
                "validator_coldkey": {
                    "offline": True,
                    "evidence": "secure-review/validator-custody-record.json",
                },
                "miner_coldkey": {
                    "offline": True,
                    "evidence": "secure-review/miner-custody-record.json",
                },
                "runtime_hosts": {
                    "hotkeys_only": True,
                    "hotkey_revocation_path_documented": True,
                    "evidence": "secure-review/runtime-wallet-inventory.json",
                },
                "treasury": {
                    "multisig_or_governance_controlled": True,
                    "evidence": "secure-review/treasury-multisig-record.json",
                },
                "review": {
                    "reviewers": ["operator", "independent-reviewer"],
                    "wallet_names_reviewed": True,
                    "network_and_commands_reviewed": True,
                    "approval_packet_recorded": True,
                    "approval_packet": "secure-review/arctura-mainnet-approval.json",
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--evidence-report",
            str(evidence),
            "--cost-payload",
            str(cost),
            "--aws-tfvars",
            str(tfvars),
            "--treasury-policy",
            str(treasury),
            "--monitoring-status",
            str(monitoring),
            "--custody-status",
            str(custody),
            "--max-cost-age-minutes",
            "999999",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["ok"] is True
