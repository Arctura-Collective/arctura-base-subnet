"""tests/test_base_rpc.py — Base RPC client tests (mocked)."""
import json
import pytest
from unittest.mock import MagicMock, patch
from arctura_base.base_rpc import BaseRPCClient


@pytest.fixture
def mock_client():
    with patch("arctura_base.base_rpc.Web3") as MockWeb3:
        w3 = MagicMock()
        w3.is_connected.return_value = True
        w3.eth.chain_id = 8453
        MockWeb3.return_value = w3
        MockWeb3.HTTPProvider.return_value = MagicMock()
        MockWeb3.to_checksum_address.side_effect = lambda x: x
        client = BaseRPCClient(rpc_url="http://mock")
        client.w3 = w3
        yield client


def test_get_balance_native(mock_client):
    mock_client.w3.eth.get_balance.return_value = 1_000_000_000_000_000_000
    mock_client.w3.eth.block_number = 21_000_000
    result = mock_client.get_balance("0xAbc", block_number=21_000_000)
    assert result["balance"] == 1_000_000_000_000_000_000
    assert result["block_number"] == 21_000_000
    assert result["token"] is None


def test_get_balance_preserves_explicit_block_zero(mock_client):
    mock_client.w3.eth.get_balance.return_value = 100
    result = mock_client.get_balance("0xAbc", block_number=0)
    mock_client.w3.eth.get_balance.assert_called_once_with("0xAbc", 0)
    assert result["block_number"] == 0


def test_get_events_forwards_filter_args(mock_client):
    event = MagicMock()
    event.get_logs.return_value = []
    contract = MagicMock()
    contract.events.Transfer = event
    mock_client.w3.eth.contract.return_value = contract

    result = mock_client.get_events(
        contract_address="0xToken",
        abi=[],
        event_name="Transfer",
        from_block=1,
        to_block=2,
        filter_args={"from": "0xSender"},
    )

    event.get_logs.assert_called_once_with(
        fromBlock=1,
        toBlock=2,
        argument_filters={"from": "0xSender"},
    )
    assert result["count"] == 0


def test_unknown_query_type_raises(mock_client):
    with pytest.raises(ValueError, match="Unknown query_type"):
        mock_client.execute_mandate(
            query_type="invalid_type",
            contract_address=None,
            block_range=(0, 0),
            payload={},
        )
