"""Mandate payload validation tests."""

import pytest

from arctura_base.agentkit import SUPPORTED_AGENT_ACTIONS
from arctura_base.payload_validation import (
    normalize_block_range,
    validate_and_raise,
    validate_mandate_context,
    validate_mandate_payload,
)


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


def test_balance_payload_accepts_missing_optional_token_address():
    is_valid, error = validate_mandate_payload(
        "balance",
        {
            "address": "0x4200000000000000000000000000000000000006",
            "token_address": None,
        },
    )

    assert is_valid is True
    assert error is None


def test_events_payload_requires_abi_and_safe_event_name():
    is_valid, error = validate_mandate_payload(
        "events",
        {"event_name": "Transfer;DROP", "abi": [{"type": "event"}]},
    )
    assert is_valid is False
    assert "Invalid event name" in error


def test_events_payload_accepts_valid_event_name_and_abi():
    is_valid, error = validate_mandate_payload(
        "events",
        {"event_name": "Transfer", "abi": [{"type": "event"}]},
    )

    assert is_valid is True
    assert error is None


def test_events_payload_requires_non_empty_abi():
    is_valid, error = validate_mandate_payload(
        "events",
        {"event_name": "Transfer", "abi": []},
    )

    assert is_valid is False
    assert "ABI must be a non-empty list" in error


def test_state_payload_requires_non_empty_abi():
    is_valid, error = validate_mandate_payload(
        "state",
        {"function_name": "totalSupply", "abi": []},
    )
    assert is_valid is False
    assert "ABI must be a non-empty list" in error


def test_state_payload_accepts_valid_function_name_and_abi():
    is_valid, error = validate_mandate_payload(
        "state",
        {"function_name": "totalSupply", "abi": [{"type": "function"}]},
    )

    assert is_valid is True
    assert error is None


def test_state_payload_requires_safe_function_name():
    is_valid, error = validate_mandate_payload(
        "state",
        {"function_name": "totalSupply;DROP", "abi": [{"type": "function"}]},
    )

    assert is_valid is False
    assert "Invalid function name" in error


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


def test_mandate_context_rejects_agent_action_by_default():
    is_valid, error = validate_mandate_context(
        query_type="agent_action",
        block_range=(200, 200),
        contract_address=None,
        latest_block=200,
        max_block_lookback=100,
    )

    assert is_valid is False
    assert "disabled by default" in error


def test_mandate_context_allows_agent_action_only_with_operator_opt_in():
    is_valid, error = validate_mandate_context(
        query_type="agent_action",
        block_range=(200, 200),
        contract_address=None,
        latest_block=200,
        max_block_lookback=100,
        allow_agent_actions=True,
    )

    assert is_valid is True
    assert error is None


def test_normalize_block_range_maps_zero_zero_to_latest_block():
    assert normalize_block_range((0, 0), latest_block=123) == (123, 123)
    assert normalize_block_range((120, 0), latest_block=123) == (120, 120)


def test_normalize_block_range_rejects_bad_shape_types_and_negative_values():
    cases = (
        ((1, 2, 3), 200, "exactly two"),
        (("1", 2), 200, "must be integers"),
        ((-1, 2), 200, "non-negative"),
        ((1, 2), -1, "latest_block"),
    )
    for block_range, latest_block, expected in cases:
        with pytest.raises(ValueError, match=expected):
            normalize_block_range(block_range, latest_block=latest_block)


def test_mandate_context_rejects_reversed_future_and_oversized_ranges():
    for block_range, expected in (
        ((200, 100), "start must be <= end"),
        ((100, 201), "future Base blocks"),
        ((50, 100), "max_block_lookback"),
    ):
        is_valid, error = validate_mandate_context(
            query_type="balance",
            block_range=block_range,
            contract_address=None,
            latest_block=200,
            max_block_lookback=100,
        )
        assert is_valid is False
        assert expected in error


def test_mandate_context_rejects_unbounded_event_scan():
    is_valid, error = validate_mandate_context(
        query_type="events",
        block_range=(0, 0),
        contract_address="0x4200000000000000000000000000000000000006",
        latest_block=200,
        max_block_lookback=100,
    )

    assert is_valid is False
    assert "explicit bounded" in error


def test_mandate_context_rejects_bad_lookback_config():
    is_valid, error = validate_mandate_context(
        query_type="balance",
        block_range=(200, 200),
        contract_address=None,
        latest_block=200,
        max_block_lookback=0,
    )

    assert is_valid is False
    assert "max_block_lookback must be positive" in error


def test_mandate_context_requires_contract_for_events_and_state():
    for query_type in ("events", "state"):
        is_valid, error = validate_mandate_context(
            query_type=query_type,
            block_range=(199, 200),
            contract_address=None,
            latest_block=200,
            max_block_lookback=100,
        )

        assert is_valid is False
        assert f"contract_address required for {query_type} query" in error


def test_mandate_context_requires_valid_contract_for_state_queries():
    is_valid, error = validate_mandate_context(
        query_type="state",
        block_range=(199, 200),
        contract_address="not-an-address",
        latest_block=200,
        max_block_lookback=100,
    )

    assert is_valid is False
    assert "Invalid contract_address" in error


def test_mandate_context_rejects_contract_for_balance_query():
    is_valid, error = validate_mandate_context(
        query_type="balance",
        block_range=(200, 200),
        contract_address="0x4200000000000000000000000000000000000006",
        latest_block=200,
        max_block_lookback=100,
    )

    assert is_valid is False
    assert "contract_address must be omitted" in error


def test_mandate_context_accepts_latest_balance_query():
    is_valid, error = validate_mandate_context(
        query_type="balance",
        block_range=(0, 0),
        contract_address=None,
        latest_block=200,
        max_block_lookback=100,
    )

    assert is_valid is True
    assert error is None


def test_validate_mandate_payload_rejects_unknown_query_type_and_non_dict_payload():
    is_valid, error = validate_mandate_payload("unknown", {})
    assert is_valid is False
    assert "Unknown query_type" in error

    is_valid, error = validate_mandate_payload("balance", [])
    assert is_valid is False
    assert "Payload must be a dict" in error


def test_validate_and_raise_raises_value_error_for_invalid_payload():
    with pytest.raises(ValueError, match="Invalid EVM address"):
        validate_and_raise("balance", {"address": "not-an-address"})
