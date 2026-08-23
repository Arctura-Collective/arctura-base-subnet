"""Runtime compatibility checks for the miner neuron."""

import inspect
import socket
import sys
from typing import Tuple  # noqa: UP035 - mirrors Bittensor's runtime contract

import bittensor as bt
import pytest

from arctura_base.protocol import BaseSubnetSynapse
from neurons.miner import ArcturaMiner


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
