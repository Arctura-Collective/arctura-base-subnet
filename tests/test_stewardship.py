"""P5 Stewardship provenance verification tests."""

import json

import pytest

from arctura_base.stewardship import (
    is_stewardship_verified,
    load_stewardship_verifications,
)


def test_load_stewardship_verifications_returns_empty_for_missing_path():
    assert load_stewardship_verifications("") == {}
    assert load_stewardship_verifications(None) == {}


def test_stewardship_verification_requires_hotkey_tag_and_active_status(tmp_path):
    path = tmp_path / "stewardship.json"
    path.write_text(
        json.dumps(
            {
                "verifications": [
                    {
                        "hotkey": "miner-hotkey",
                        "energy_tag": "renewable_verified",
                        "status": "verified",
                        "evidence": "certificate-id",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    verifications = load_stewardship_verifications(path)

    assert is_stewardship_verified(
        "miner-hotkey",
        "renewable_verified",
        verifications,
    )
    assert not is_stewardship_verified("miner-hotkey", "unknown", verifications)
    assert not is_stewardship_verified("other-hotkey", "renewable_verified", verifications)


def test_stewardship_verification_rejects_malformed_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"verifications": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="verifications list"):
        load_stewardship_verifications(path)
