"""Safety checks for custody and key-rotation documentation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_key_rotation_runbook_exists_and_blocks_unauthorized_signing():
    runbook = (ROOT / "docs" / "KEY_ROTATION_AND_CUSTODY.md").read_text(encoding="utf-8")

    assert "Emergency Hotkey Revocation" in runbook
    assert "arctura-custody-audit" in runbook
    assert "does not create wallets" in runbook
    assert "Owner Coldkey or Treasury Incident" in runbook
    assert "Forbidden Without Explicit Final Approval" in runbook
    assert "btcli subnet create --subtensor.network finney" in runbook


def test_mainnet_blockers_link_key_rotation_runbook():
    blockers = (ROOT / "MAINNET_LAUNCH_BLOCKERS.md").read_text(encoding="utf-8")

    assert "docs/KEY_ROTATION_AND_CUSTODY.md" in blockers
    assert "Key rotation and emergency custody procedure reviewed" in blockers
