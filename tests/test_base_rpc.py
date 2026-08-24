"""tests/test_base_rpc.py — Base RPC client tests (mocked)."""

from unittest.mock import MagicMock, patch

import pytest

from arctura_base.base_rpc import BaseRPCClient


@pytest.fixture
def mock_client():
    with patch("arctura_base.base_rpc._Web3") as mock_web3:
        w3 = MagicMock()
        w3.is_connected.return_value = True
        w3.eth.chain_id = 8453
        mock_web3.return_value = w3
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.to_checksum_address.side_effect = lambda x: x
        client = BaseRPCClient(rpc_url="http://mock")
        client.w3 = w3
        yield client


def test_init_requires_web3_dependency():
    with patch("arctura_base.base_rpc._Web3", None):
        with pytest.raises(ImportError, match="web3 is required"):
            BaseRPCClient(rpc_url="http://mock")


def test_init_reads_allow_agent_actions_from_env(monkeypatch):
    monkeypatch.setenv("ARCTURA_ALLOW_AGENT_ACTIONS", "yes")

    with patch("arctura_base.base_rpc._Web3") as mock_web3:
        w3 = MagicMock()
        w3.is_connected.return_value = True
        w3.eth.chain_id = 8453
        mock_web3.return_value = w3
        mock_web3.HTTPProvider.return_value = MagicMock()

        client = BaseRPCClient(rpc_url="http://mock")

    assert client.allow_agent_actions is True


def test_verify_connection_rejects_disconnected_rpc():
    with patch("arctura_base.base_rpc._Web3") as mock_web3:
        w3 = MagicMock()
        w3.is_connected.return_value = False
        mock_web3.return_value = w3
        mock_web3.HTTPProvider.return_value = MagicMock()

        with pytest.raises(ConnectionError, match="Cannot connect"):
            BaseRPCClient(rpc_url="http://mock")


def test_verify_connection_warns_on_unexpected_chain_id():
    with (
        patch("arctura_base.base_rpc._Web3") as mock_web3,
        patch("arctura_base.base_rpc.bt.logging.warning") as warning,
    ):
        w3 = MagicMock()
        w3.is_connected.return_value = True
        w3.eth.chain_id = 1
        mock_web3.return_value = w3
        mock_web3.HTTPProvider.return_value = MagicMock()

        BaseRPCClient(rpc_url="http://mock")

    warning.assert_called_once()


def test_get_latest_block_number_casts_to_int(mock_client):
    mock_client.w3.eth.block_number = "21000000"

    assert mock_client.get_latest_block_number() == 21_000_000


def test_get_balance_native(mock_client):
    mock_client.w3.eth.get_balance.return_value = 1_000_000_000_000_000_000
    mock_client.w3.eth.block_number = 21_000_000
    result = mock_client.get_balance("0xAbc", block_number=21_000_000)
    assert result["balance"] == 1_000_000_000_000_000_000
    assert result["block_number"] == 21_000_000
    assert result["token"] is None


def test_get_balance_token_calls_erc20_balance_of(mock_client):
    balance_call = MagicMock()
    balance_call.call.return_value = 42
    contract = MagicMock()
    contract.functions.balanceOf.return_value = balance_call
    mock_client.w3.eth.contract.return_value = contract
    mock_client.w3.eth.block_number = 21_000_001

    result = mock_client.get_balance(
        "0xWallet",
        token_address="0xToken",
        block_number=None,
    )

    mock_client.w3.eth.contract.assert_called_once()
    contract.functions.balanceOf.assert_called_once_with("0xWallet")
    balance_call.call.assert_called_once_with(block_identifier="latest")
    assert result["balance"] == 42
    assert result["block_number"] == 21_000_001
    assert result["token"] == "0xToken"


def test_get_balance_preserves_explicit_block_zero(mock_client):
    mock_client.w3.eth.get_balance.return_value = 100
    result = mock_client.get_balance("0xAbc", block_number=0)
    mock_client.w3.eth.get_balance.assert_called_once_with("0xAbc", 0)
    assert result["block_number"] == 0


def test_get_events_serializes_logs_without_filter_args(mock_client):
    event = MagicMock()
    event.get_logs.return_value = [
        {
            "blockNumber": 7,
            "transactionHash": bytes.fromhex("22" * 32),
            "logIndex": 3,
            "args": {"from": "0xSender", "value": 10},
        }
    ]
    contract = MagicMock()
    contract.events.Transfer = event
    mock_client.w3.eth.contract.return_value = contract

    result = mock_client.get_events(
        contract_address="0xToken",
        abi=[{"type": "event"}],
        event_name="Transfer",
        from_block=5,
        to_block=7,
    )

    event.get_logs.assert_called_once_with(fromBlock=5, toBlock=7)
    assert result == {
        "event": "Transfer",
        "from_block": 5,
        "to_block": 7,
        "logs": [
            {
                "blockNumber": 7,
                "transactionHash": "22" * 32,
                "logIndex": 3,
                "args": {"from": "0xSender", "value": "10"},
            }
        ],
        "count": 1,
    }


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


def test_call_view_serializes_result_and_latest_block(mock_client):
    view_call = MagicMock()
    view_call.call.return_value = 123
    contract = MagicMock()
    contract.functions.totalSupply.return_value = view_call
    mock_client.w3.eth.contract.return_value = contract
    mock_client.w3.eth.block_number = 21_000_002

    result = mock_client.call_view(
        contract_address="0xToken",
        abi=[{"type": "function"}],
        function_name="totalSupply",
        args=[1, "2"],
    )

    contract.functions.totalSupply.assert_called_once_with(1, "2")
    view_call.call.assert_called_once_with(block_identifier="latest")
    assert result == {
        "function": "totalSupply",
        "args": ["1", "2"],
        "result": "123",
        "block_number": 21_000_002,
    }


def test_unknown_query_type_raises(mock_client):
    with pytest.raises(ValueError, match="Unknown query_type"):
        mock_client.execute_mandate(
            query_type="invalid_type",
            contract_address=None,
            block_range=(0, 0),
            payload={},
        )


def test_agent_action_disabled_by_default_before_adapter_import(mock_client, monkeypatch):
    called = False

    def fake_execute_agent_action(**kwargs):
        nonlocal called
        called = True
        return {"status": "should-not-run"}

    monkeypatch.setattr(
        "arctura_base.agentkit.execute_agent_action",
        fake_execute_agent_action,
    )

    with pytest.raises(PermissionError, match="disabled by default"):
        mock_client.execute_mandate(
            query_type="agent_action",
            contract_address=None,
            block_range=(21_000_000, 21_000_000),
            payload={"action_type": "transfer", "action_args": {}},
        )

    assert called is False


def test_execute_mandate_requires_contract_address_for_events_and_state(mock_client):
    for query_type, payload, expected in (
        ("events", {"abi": [], "event_name": "Transfer"}, "events query"),
        ("state", {"abi": [], "function_name": "totalSupply"}, "state query"),
    ):
        with pytest.raises(ValueError, match=expected):
            mock_client.execute_mandate(
                query_type=query_type,
                contract_address=None,
                block_range=(1, 2),
                payload=payload,
            )


def test_execute_mandate_dispatches_events_state_and_agent_action(mock_client, monkeypatch):
    mock_client.get_events = MagicMock(return_value={"events": []})
    mock_client.call_view = MagicMock(return_value={"state": "ok"})
    mock_client.get_block_hash = MagicMock(return_value="33" * 32)

    events_result = mock_client.execute_mandate(
        query_type="events",
        contract_address="0xToken",
        block_range=(1, 0),
        payload={"abi": [{"type": "event"}], "event_name": "Transfer"},
    )
    mock_client.get_events.assert_called_once_with(
        contract_address="0xToken",
        abi=[{"type": "event"}],
        event_name="Transfer",
        from_block=1,
        to_block=1,
        filter_args=None,
    )
    assert events_result["_meta"]["query_type"] == "events"

    state_result = mock_client.execute_mandate(
        query_type="state",
        contract_address="0xToken",
        block_range=(2, 3),
        payload={"abi": [{"type": "function"}], "function_name": "totalSupply"},
    )
    mock_client.call_view.assert_called_once_with(
        contract_address="0xToken",
        abi=[{"type": "function"}],
        function_name="totalSupply",
        args=[],
        block_number=3,
    )
    assert state_result["_meta"]["query_type"] == "state"

    def fake_execute_agent_action(**kwargs):
        return {"agent": kwargs}

    monkeypatch.setattr(
        "arctura_base.agentkit.execute_agent_action",
        fake_execute_agent_action,
    )
    mock_client.allow_agent_actions = True

    agent_result = mock_client.execute_mandate(
        query_type="agent_action",
        contract_address=None,
        block_range=(0, 0),
        payload={"action_type": "transfer", "action_args": {"amount": "1"}},
    )

    assert agent_result["agent"] == {
        "action_type": "transfer",
        "action_args": {"amount": "1"},
    }
    assert agent_result["_meta"]["query_type"] == "agent_action"


def test_execute_mandate_reuses_block_hash_for_fixed_block(mock_client):
    block = {"hash": bytes.fromhex("11" * 32)}
    mock_client.w3.eth.get_block.return_value = block
    mock_client.w3.eth.get_balance.return_value = 100

    for _ in range(2):
        result = mock_client.execute_mandate(
            query_type="balance",
            contract_address=None,
            block_range=(21_000_000, 21_000_000),
            payload={"address": "0xAbc"},
        )
        assert result["_meta"]["block_hash"] == "11" * 32

    mock_client.w3.eth.get_block.assert_called_once_with(21_000_000)
