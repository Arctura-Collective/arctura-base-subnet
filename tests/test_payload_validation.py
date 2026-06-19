"""Mandate payload validation tests."""

import pytest

from arctura_base.agentkit import SUPPORTED_AGENT_ACTIONS
from arctura_base.payload_validation import validate_mandate_payload


def test_balance_payload_accepts_valid_address():
    is_valid, error = validate_mandate_payload(
        "balance",
        {"address": "0x4200000000000000000000000000000000000006"},
    )
    assert is_valid is True
    assert error is None


def test_balance_payload_rejects_invalid_address():
    is_valid, error = validate_mandate_payload("balance", {"address": "not-an-address"})
    assert is_valid is False
    assert "Invalid EVM address" in error


def test_events_payload_requires_abi_and_safe_event_name():
    is_valid, error = validate_mandate_payload(
        "events",
        {"event_name": "Transfer;DROP", "abi": [{"type": "event"}]},
    )
    assert is_valid is False
    assert "Invalid event name" in error


def test_state_payload_requires_non_empty_abi():
    is_valid, error = validate_mandate_payload(
        "state",
        {"function_name": "totalSupply", "abi": []},
    )
    assert is_valid is False
    assert "ABI must be a non-empty list" in error


@pytest.mark.parametrize("action_type", sorted(SUPPORTED_AGENT_ACTIONS))
def test_agent_action_payload_accepts_adapter_supported_actions(action_type):
    is_valid, error = validate_mandate_payload(
        "agent_action",
        {"action_type": action_type, "action_args": {}},
    )
    assert is_valid is True
    assert error is None


def test_agent_action_payload_rejects_unimplemented_action():
    is_valid, error = validate_mandate_payload(
        "agent_action",
        {"action_type": "swap", "action_args": {}},
    )
    assert is_valid is False
    assert "Unknown action_type" in error
