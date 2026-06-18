"""Runtime compatibility checks for the miner neuron."""

import inspect

import bittensor as bt

from arctura_base.protocol import BaseSubnetSynapse
from neurons.miner import ArcturaMiner


def test_forward_synapse_annotation_is_runtime_class():
    signature = inspect.signature(ArcturaMiner.forward)
    annotation = signature.parameters["synapse"].annotation
    assert annotation is BaseSubnetSynapse
    assert issubclass(annotation, bt.Synapse)
