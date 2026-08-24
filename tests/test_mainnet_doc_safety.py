"""Static safety checks for Finney/mainnet operator documentation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs"


def markdown_docs() -> list[Path]:
    return [ROOT / "README.md", *sorted(DOC_ROOT.glob("*.md"))]


def launch_public_docs() -> list[Path]:
    return [*markdown_docs(), *sorted(DOC_ROOT.glob("*.html"))]


def test_finney_command_docs_reference_current_readiness_gate() -> None:
    """Any markdown doc showing Finney commands must point at the launch gate."""

    offenders: list[str] = []
    required_gate_markers = (
        "arctura-readiness-audit",
        "GO_NO_GO_CHECKLIST",
        "MAINNET_READINESS_TRACKER",
        "Mainnet Go / No-Go",
    )

    for path in launch_public_docs():
        text = path.read_text(encoding="utf-8")
        if "btcli subnet create" not in text and "--subtensor.network finney" not in text:
            continue
        if not any(marker in text for marker in required_gate_markers):
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_historical_launch_docs_do_not_claim_current_mainnet_readiness() -> None:
    stale_claims = (
        "Ready for Finney Mainnet deployment",
        "63/63",
        "ready for Finney deployment",
        "instant deployment",
    )

    offenders: list[str] = []
    for path in markdown_docs():
        text = path.read_text(encoding="utf-8")
        for claim in stale_claims:
            if claim in text:
                offenders.append(f"{path.relative_to(ROOT)}: {claim}")

    assert offenders == []


def test_ec2_guidance_preserves_current_axon_architecture() -> None:
    aws_guide = (DOC_ROOT / "FINNEY_REGISTRATION_GUIDE.md").read_text(encoding="utf-8")

    assert "miner axon" in aws_guide
    assert "validator is dendrite-only" in aws_guide
    assert "No coldkeys" in aws_guide
    assert "200 GB gp3" in aws_guide
