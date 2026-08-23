from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from scripts.update_subnet_cost_ticker import build_payload, parse_tao_amount


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
