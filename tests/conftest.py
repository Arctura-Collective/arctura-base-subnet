"""Test compatibility shims for optional heavyweight runtime dependencies."""

from __future__ import annotations

import sys
import types

if "bittensor" not in sys.modules:
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
    bittensor.config = _config
    bittensor.logging = _Logging()
    bittensor.subtensor = _ArgProvider()
    bittensor.wallet = _ArgProvider()
    bittensor.axon = _ArgProvider()
    sys.modules["bittensor"] = bittensor


if "torch" not in sys.modules:
    torch = types.ModuleType("torch")
    torch.int64 = "int64"
    torch.float32 = "float32"
    torch.tensor = lambda values, dtype=None: values
    sys.modules["torch"] = torch
