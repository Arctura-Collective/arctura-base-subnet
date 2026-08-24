"""Static checks for the mainnet readiness tracker."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "docs" / "MAINNET_READINESS_TRACKER.md"


def test_tracker_maps_all_open_launch_issues_to_evidence():
    text = TRACKER.read_text(encoding="utf-8")

    for issue in ("#1", "#2", "#4", "#6", "#7"):
        assert issue in text
    for artifact in (
        "deploy/aws/asg/",
        "deploy/monitoring",
        "docs/KEY_ROTATION_AND_CUSTODY.md",
        "validator failover decision packet",
        "arctura-aws-asg-audit",
        "arctura-readiness-audit",
        "arctura-coverage-gate",
        "arctura-collect-evidence",
    ):
        assert artifact in text


def test_tracker_preserves_no_spend_authorization_boundary():
    text = TRACKER.read_text(encoding="utf-8")

    assert "No item in this document authorizes" in text
    assert "wallet creation" in text
    assert "TAO" in text
    assert "explicit operator approval" in text
    assert "within 30 minutes" in text


def test_tracker_lists_current_evidence_gate_requirements():
    text = TRACKER.read_text(encoding="utf-8")

    for requirement in (
        "ok: true",
        "zero miner and validator restarts",
        "zero fatal journal markers",
        "at least 48 hours",
        "at least 570 passing health samples",
        "at least two successful non-zero weight commits",
    ):
        assert requirement in text


def test_go_no_go_checklist_does_not_precheck_unproven_weight_commits():
    text = (ROOT / "docs" / "GO_NO_GO_CHECKLIST.md").read_text(encoding="utf-8")

    assert "- [ ] `neurons/validator.py` — submitted at least two non-zero testnet weights" in text
    assert "- [ ] Bittensor v10.5 testnet miner and validator complete one attestation" in text
    assert "273 tests on 2026-08-24" in text
    assert "arctura-readiness-audit" in text
