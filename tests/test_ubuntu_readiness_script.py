"""Static safety checks for the cloud-resume readiness checker."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readiness_checker_is_read_only_and_checks_core_tools():
    script = (ROOT / "scripts" / "check_ubuntu_readiness.sh").read_text(encoding="utf-8")
    assert "for command in python3 git docker btcli; do" in script
    assert "gh auth status" in script
    assert "docker compose version" in script
    assert "btcli subnet create" not in script
    assert "wallet new" not in script
    assert "systemctl restart" not in script


def test_readiness_checker_checks_environment_and_operational_logs():
    script = (ROOT / "scripts" / "check_ubuntu_readiness.sh").read_text(encoding="utf-8")
    assert '"$REPO_DIR/.env"' in script
    assert "burn_cost.log validator.log" in script
    assert "No transaction or signing action was performed." in script
