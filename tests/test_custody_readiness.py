"""Custody readiness audit tests."""

import json
from pathlib import Path

from arctura_base.custody_readiness import audit_status, main

ROOT = Path(__file__).resolve().parents[1]
STATUS_EXAMPLE = ROOT / "deploy" / "custody" / "custody-status.example.json"


def green_status() -> dict:
    return {
        "schema_version": 1,
        "environment": "finney-mainnet",
        "reviewed_at": "2026-08-24T01:00:00Z",
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


def test_example_custody_status_fails_without_key_or_wallet_access() -> None:
    audit = audit_status(json.loads(STATUS_EXAMPLE.read_text(encoding="utf-8")))

    assert audit["audit_type"] == "custody_readiness_audit"
    assert audit["ok"] is False
    assert audit["checks"]["owner_coldkey_offline"] is False
    assert audit["checks"]["minimum_two_reviewers"] is False
    assert audit["checks"]["no_placeholders"] is False
    assert audit["safety"]["wallet_required"] is False
    assert audit["safety"]["secret_inspection_attempted"] is False
    assert audit["safety"]["on_chain_action_attempted"] is False


def test_green_custody_status_passes_without_inspecting_secrets() -> None:
    audit = audit_status(green_status())

    assert audit["ok"] is True
    assert all(audit["checks"].values())
    assert audit["findings"]["reviewer_count"] == 2


def test_custody_status_requires_two_reviewers() -> None:
    status = green_status()
    status["review"]["reviewers"] = ["operator"]

    audit = audit_status(status)

    assert audit["ok"] is False
    assert audit["checks"]["minimum_two_reviewers"] is False


def test_cli_writes_custody_audit(tmp_path) -> None:
    output = tmp_path / "custody-audit.json"

    exit_code = main(["--status", str(STATUS_EXAMPLE), "--output", str(output)])

    assert exit_code == 1
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["audit_type"] == "custody_readiness_audit"
    assert rendered["safety"]["wallet_required"] is False
