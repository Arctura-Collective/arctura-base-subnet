"""Runtime compatibility checks for the miner neuron."""

import inspect
from typing import Tuple

import bittensor as bt

from arctura_base.protocol import BaseSubnetSynapse
from neurons.miner import ArcturaMiner


def test_forward_synapse_annotation_is_runtime_class():
    signature = inspect.signature(ArcturaMiner.forward)
    annotation = signature.parameters["synapse"].annotation
    assert annotation is BaseSubnetSynapse
    assert issubclass(annotation, bt.Synapse)


def test_blacklist_signature_matches_bittensor_axon_contract():
    signature = inspect.signature(ArcturaMiner.blacklist)
    assert signature.parameters["synapse"].annotation is BaseSubnetSynapse
    assert signature.return_annotation == Tuple[bool, str]


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
