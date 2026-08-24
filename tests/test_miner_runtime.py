"""Runtime compatibility checks for the miner neuron."""

import inspect
import socket
import sys
from types import SimpleNamespace
from typing import Tuple  # noqa: UP035 - mirrors Bittensor's runtime contract
from unittest.mock import MagicMock, patch

import bittensor as bt
import pytest

from arctura_base.protocol import BaseSubnetSynapse
from neurons.miner import ArcturaMiner


def test_miner_init_wires_bittensor_and_axon(monkeypatch):
    config = SimpleNamespace(
        full_path="/tmp/arctura-miner",
        netuid=505,
        allow_agent_actions=True,
        subtensor=SimpleNamespace(network="test"),
    )
    wallet = MagicMock()
    subtensor = MagicMock()
    metagraph = MagicMock()
    axon = MagicMock()

    monkeypatch.setenv("ARCTURA_ENERGY_TAG", "renewable_verified")
    with (
        patch("neurons.miner.bt.logging"),
        patch("neurons.miner.bt.Wallet", return_value=wallet) as wallet_cls,
        patch("neurons.miner.bt.Subtensor", return_value=subtensor) as subtensor_cls,
        patch("neurons.miner.load_metagraph", return_value=metagraph) as load_graph,
        patch("neurons.miner.BaseRPCClient") as base_client_cls,
        patch("neurons.miner.bt.Axon", return_value=axon) as axon_cls,
    ):
        miner = ArcturaMiner(config=config)

    wallet_cls.assert_called_once_with(config=config)
    subtensor_cls.assert_called_once_with(config=config)
    load_graph.assert_called_once_with(subtensor, 505)
    base_client_cls.assert_called_once_with(allow_agent_actions=True)
    axon_cls.assert_called_once_with(wallet=wallet, config=config)
    axon.attach.assert_called_once_with(
        forward_fn=miner.forward,
        blacklist_fn=miner.blacklist,
        priority_fn=miner.priority,
    )


def test_miner_config_honors_v10_cli_flags(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "miner",
            "--wallet.name",
            "arctura_miner",
            "--wallet.hotkey",
            "default",
            "--subtensor.network",
            "test",
            "--netuid",
            "505",
            "--axon.port",
            "8191",
        ],
    )

    config = ArcturaMiner._build_config()

    assert config.wallet.name == "arctura_miner"
    assert config.subtensor.network == "test"
    assert config.netuid == 505
    assert config.axon.port == 8191


def test_forward_synapse_annotation_is_runtime_class():
    signature = inspect.signature(ArcturaMiner.forward)
    annotation = signature.parameters["synapse"].annotation
    assert annotation is BaseSubnetSynapse
    assert issubclass(annotation, bt.Synapse)


def test_blacklist_signature_matches_bittensor_axon_contract():
    signature = inspect.signature(ArcturaMiner.blacklist)
    assert signature.parameters["synapse"].annotation is BaseSubnetSynapse
    assert signature.return_annotation == Tuple[bool, str]  # noqa: UP006


def test_forward_refuses_invalid_payload_before_rpc():
    miner = object.__new__(ArcturaMiner)
    miner.base_client = None
    synapse = BaseSubnetSynapse(
        mandate_id="invalid",
        query_type="balance",
        mandate_payload={"address": "bad"},
    )

    result = miner.forward(synapse)

    assert result.base_state_hash is None
    assert result.merkle_proof is None
    assert result.confidence == 0.0


def test_forward_refuses_oversized_block_range_before_execute_mandate():
    class FakeBaseClient:
        execute_called = False

        def get_latest_block_number(self):
            return 1_000

        def execute_mandate(self, **kwargs):
            self.execute_called = True
            raise AssertionError("execute_mandate should not be called")

    base_client = FakeBaseClient()
    miner = object.__new__(ArcturaMiner)
    miner.base_client = base_client
    miner.config = SimpleNamespace(max_block_lookback=10)
    synapse = BaseSubnetSynapse(
        mandate_id="oversized",
        query_type="balance",
        base_block_range=(900, 900),
        mandate_payload={"address": "0x4200000000000000000000000000000000000006"},
    )

    result = miner.forward(synapse)

    assert base_client.execute_called is False
    assert result.base_state_hash is None
    assert result.merkle_proof is None
    assert result.confidence == 0.0


def test_forward_refuses_agent_action_without_operator_opt_in():
    class FakeBaseClient:
        execute_called = False

        def get_latest_block_number(self):
            return 1_000

        def execute_mandate(self, **kwargs):
            self.execute_called = True
            raise AssertionError("execute_mandate should not be called")

    base_client = FakeBaseClient()
    miner = object.__new__(ArcturaMiner)
    miner.base_client = base_client
    miner.config = SimpleNamespace(max_block_lookback=10, allow_agent_actions=False)
    synapse = BaseSubnetSynapse(
        mandate_id="agent-action",
        query_type="agent_action",
        base_block_range=(1_000, 1_000),
        mandate_payload={"action_type": "transfer", "action_args": {"amount": "1"}},
    )

    result = miner.forward(synapse)

    assert base_client.execute_called is False
    assert result.base_state_hash is None
    assert result.merkle_proof is None
    assert result.confidence == 0.0


def test_forward_returns_complete_attestation(monkeypatch):
    class FakeBaseClient:
        def get_latest_block_number(self):
            return 1_000

        def execute_mandate(self, **kwargs):
            return {
                "address": kwargs["payload"]["address"],
                "balance": 123,
                "block_number": 1_000,
                "_meta": {"block_hash": "ab" * 32, "duration_ms": 3},
            }

    monkeypatch.setenv("ARCTURA_ENERGY_TAG", "renewable_claimed")
    miner = object.__new__(ArcturaMiner)
    miner.base_client = FakeBaseClient()
    miner.config = SimpleNamespace(max_block_lookback=10, allow_agent_actions=False)
    synapse = BaseSubnetSynapse(
        mandate_id="valid-attestation",
        query_type="balance",
        base_block_range=(1_000, 1_000),
        mandate_payload={"address": "0x4200000000000000000000000000000000000006"},
    )

    result = miner.forward(synapse)

    assert result.base_state_hash is not None
    assert result.merkle_proof
    assert result.block_hash_anchor == "ab" * 32
    assert result.execution_trace["steps"] == [
        "rpc_fetch",
        "output_hash",
        "merkle_build",
        "block_anchor",
    ]
    assert result.execution_trace["block_number"] == 1_000
    assert result.confidence == 0.9
    assert result.energy_tag == "renewable_claimed"


def test_estimate_confidence_tracks_partial_steps():
    miner = object.__new__(ArcturaMiner)

    assert miner._estimate_confidence("balance", []) == 0.0
    assert miner._estimate_confidence("balance", ["rpc_fetch", "output_hash"]) == 0.45


def test_blacklist_rejects_unknown_and_zero_stake_callers():
    miner = object.__new__(ArcturaMiner)
    miner.config = SimpleNamespace(allow_non_validator=False)
    miner.metagraph = SimpleNamespace(
        hotkeys=["zero-stake"],
        S=[0.0],
        validator_permit=[True],
    )

    unknown = BaseSubnetSynapse()
    unknown.dendrite.hotkey = "unknown-hotkey"
    blocked, reason = miner.blacklist(unknown)
    assert blocked is True
    assert "Unregistered hotkey" in reason

    zero_stake = BaseSubnetSynapse()
    zero_stake.dendrite.hotkey = "zero-stake"
    blocked, reason = miner.blacklist(zero_stake)
    assert blocked is True
    assert "Zero-stake validator" in reason


def test_blacklist_requires_validator_permit():
    miner = object.__new__(ArcturaMiner)
    miner.config = type("Config", (), {"allow_non_validator": False})()
    miner.metagraph = type(
        "Metagraph",
        (),
        {"hotkeys": ["caller"], "S": [1.0], "validator_permit": [False]},
    )()
    synapse = BaseSubnetSynapse()
    synapse.dendrite.hotkey = "caller"

    blocked, reason = miner.blacklist(synapse)

    assert blocked is True
    assert "validator permit" in reason


def test_blacklist_allows_validators_and_operator_override():
    miner = object.__new__(ArcturaMiner)
    miner.config = SimpleNamespace(allow_non_validator=False)
    miner.metagraph = SimpleNamespace(
        hotkeys=["validator"],
        S=[1.0],
        validator_permit=[True],
    )
    synapse = BaseSubnetSynapse()
    synapse.dendrite.hotkey = "validator"

    assert miner.blacklist(synapse) == (False, "")

    miner.config.allow_non_validator = True
    miner.metagraph.validator_permit = [False]
    assert miner.blacklist(synapse) == (False, "")


def test_priority_returns_stake_or_zero_for_unknown_hotkey():
    miner = object.__new__(ArcturaMiner)
    miner.metagraph = SimpleNamespace(hotkeys=["known"], S=[12.5])

    known = BaseSubnetSynapse()
    known.dendrite.hotkey = "known"
    assert miner.priority(known) == 12.5

    unknown = BaseSubnetSynapse()
    unknown.dendrite.hotkey = "unknown"
    assert miner.priority(unknown) == 0.0


def test_port_guard_rejects_occupied_axon_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        with pytest.raises(RuntimeError, match="already in use"):
            ArcturaMiner._verify_port_available(port)


def test_port_guard_allows_free_axon_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]

    ArcturaMiner._verify_port_available(port)


def test_miner_run_starts_serves_syncs_and_closes(monkeypatch):
    miner = object.__new__(ArcturaMiner)
    miner.config = SimpleNamespace(axon=SimpleNamespace(port=8191), netuid=505)
    miner.axon = MagicMock()
    miner.subtensor = MagicMock()
    miner.metagraph = MagicMock()
    miner.metagraph.block.item.return_value = 123

    monkeypatch.setattr(ArcturaMiner, "_verify_port_available", MagicMock())

    def stop_after_first_sleep(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("neurons.miner.time.sleep", stop_after_first_sleep)

    miner.run()

    ArcturaMiner._verify_port_available.assert_called_once_with(8191)
    miner.axon.start.assert_called_once()
    miner.axon.serve.assert_called_once_with(netuid=505, subtensor=miner.subtensor)
    miner.metagraph.sync.assert_called_once_with(subtensor=miner.subtensor)
    miner.axon.stop.assert_called_once()
    miner.subtensor.close.assert_called_once()


def test_miner_main_constructs_and_runs():
    with patch("neurons.miner.ArcturaMiner") as miner_cls:
        from neurons.miner import main

        main()

    miner_cls.return_value.run.assert_called_once()
