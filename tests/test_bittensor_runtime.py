"""Bittensor live-runtime resilience tests."""

import pytest

from arctura_base.bittensor_runtime import load_metagraph


class FlakySubtensor:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def metagraph(self, netuid):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("transient runtime trap")
        return {"netuid": netuid}


def test_load_metagraph_retries_transient_failure(monkeypatch):
    subtensor = FlakySubtensor(failures=2)
    sleeps = []
    monkeypatch.setattr("arctura_base.bittensor_runtime.time.sleep", sleeps.append)

    assert load_metagraph(subtensor, 505, attempts=3, retry_seconds=0.25) == {"netuid": 505}
    assert subtensor.calls == 3
    assert sleeps == [0.25, 0.25]


def test_load_metagraph_raises_after_retry_budget(monkeypatch):
    subtensor = FlakySubtensor(failures=3)
    monkeypatch.setattr("arctura_base.bittensor_runtime.time.sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="transient runtime trap"):
        load_metagraph(subtensor, 505, attempts=2, retry_seconds=0)
