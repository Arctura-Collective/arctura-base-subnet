from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.update_subnet_cost_ticker import (
    build_payload,
    build_unavailable_payload,
    main,
    parse_tao_amount,
    run_burn_cost,
)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("Subnet burn cost: 773.1718 TAO", Decimal("773.1718")),
        ("Subnet burn cost: \u200e773.1718 τ\u200e", Decimal("773.1718")),
        ("cost now 1,234.5000 tao", Decimal("1234.5000")),
    ],
)
def test_parse_tao_amount(output: str, expected: Decimal) -> None:
    assert parse_tao_amount(output) == expected


def test_parse_tao_amount_rejects_missing_value() -> None:
    with pytest.raises(ValueError, match="No TAO amount"):
        parse_tao_amount("registration cost unavailable")


def test_build_payload_is_stable() -> None:
    payload = build_payload(
        cost_tao=Decimal("773.1718"),
        network="finney",
        command=["btcli", "subnet", "burn_cost", "--subtensor.network", "finney"],
        raw_output="Subnet burn cost: 773.1718 TAO",
        collected_at=datetime(2026, 8, 23, 22, 45, tzinfo=timezone.utc),
    )

    assert payload["ok"] is True
    assert payload["network"] == "finney"
    assert payload["cost_tao"] == "773.1718"
    assert payload["cost_label"] == "773.1718 TAO"
    assert payload["collected_at"] == "2026-08-23T22:45:00Z"
    assert "explicit operator approval" in str(payload["warning"])


def test_build_unavailable_payload_blocks_registration_use() -> None:
    payload = build_unavailable_payload(
        network="finney",
        command=["btcli", "subnet", "burn_cost", "--subtensor.network", "finney"],
        error="Burn-cost command unavailable: btcli",
        collected_at=datetime(2026, 8, 23, 22, 45, tzinfo=timezone.utc),
    )

    assert payload["ok"] is False
    assert payload["cost_tao"] is None
    assert payload["cost_label"] == "Unavailable"
    assert "Do not use this snapshot" in str(payload["warning"])
    assert payload["error"] == "Burn-cost command unavailable: btcli"


def test_run_burn_cost_reports_missing_command() -> None:
    with pytest.raises(RuntimeError, match="Burn-cost command unavailable"):
        run_burn_cost(["definitely-missing-btcli-for-test"])


def test_manual_raw_btcli_output_writes_payload_without_running_command(tmp_path) -> None:
    output = tmp_path / "subnet_launch_cost.json"

    exit_code = main(
        [
            "--output",
            str(output),
            "--network",
            "finney",
            "--command",
            "definitely-missing-btcli-for-test",
            "--raw-btcli-output",
            "Subnet burn cost: 812.5 TAO",
        ]
    )

    assert exit_code == 0
    rendered = output.read_text(encoding="utf-8")
    assert '"cost_tao": "812.5"' in rendered
    assert '"ok": true' in rendered
    assert "operator-provided btcli subnet burn_cost --subtensor.network finney" in rendered


def test_cost_page_renders_unavailable_payload_without_throwing() -> None:
    page = (Path(__file__).resolve().parents[1] / "docs" / "subnet-cost.html").read_text(
        encoding="utf-8"
    )

    assert "if (!data.ok)" in page
    assert "costEl.textContent = data.cost_label" in page
    assert "return;" in page
