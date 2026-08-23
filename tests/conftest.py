"""Test compatibility shims for optional heavyweight runtime dependencies."""

from __future__ import annotations

import sys
import types
from importlib.util import find_spec

if find_spec("bittensor") is None:
    bittensor = types.ModuleType("bittensor")

    class Synapse:
        def __init__(self, **kwargs):
            self.dendrite = types.SimpleNamespace(hotkey="")
            for key, value in kwargs.items():
                setattr(self, key, value)

    class _Logging:
        def __call__(self, *args, **kwargs):
            return None

        def debug(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

        def warning(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

        def success(self, *args, **kwargs):
            return None

        def add_args(self, parser):
            return None

    class _ArgProvider:
        def add_args(self, parser):
            return None

    def _config(parser=None):
        return types.SimpleNamespace(
            wallet=types.SimpleNamespace(name="test", hotkey="default"),
            subtensor=types.SimpleNamespace(network="test"),
            netuid=1,
            timeout=30.0,
            full_path="",
        )

    bittensor.Synapse = Synapse
    bittensor.Config = _config
    bittensor.logging = _Logging()
    bittensor.Subtensor = _ArgProvider()
    bittensor.Wallet = _ArgProvider()
    bittensor.Axon = _ArgProvider()
    bittensor.Dendrite = _ArgProvider()
    sys.modules["bittensor"] = bittensor
