"""Validator weight-setting retry tests."""

import torch

from neurons.validator import ArcturaValidator


class DummySubtensor:
    def __init__(self):
        self.calls = 0

    def set_weights(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return False, "nonce too low"
        return True, "ok"


class CooldownSubtensor:
    def __init__(self):
        self.calls = 0

    def set_weights(self, **kwargs):
        self.calls += 1
        return False, "No attempt made. Perhaps it is too soon to commit weights!"


def test_set_weights_retries_after_failure(monkeypatch):
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = DummySubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = object()
    validator.WEIGHT_SET_RETRIES = 2
    validator.WEIGHT_SET_RETRY_SECONDS = 0

    monkeypatch.setattr(torch, "tensor", lambda values, dtype=None: values)

    assert validator._set_weights({1: 1.0}) is True
    assert validator.subtensor.calls == 2


def test_set_weights_skips_all_zero_scores(monkeypatch):
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = DummySubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = object()
    monkeypatch.setattr(torch, "tensor", lambda values, dtype=None: values)

    assert validator._set_weights({1: 0.0, 2: 0.0}) is False
    assert validator.subtensor.calls == 0


def test_set_weights_does_not_retry_chain_cooldown(monkeypatch):
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = CooldownSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = object()
    validator.WEIGHT_SET_RETRIES = 3
    monkeypatch.setattr(torch, "tensor", lambda values, dtype=None: values)

    assert validator._set_weights({1: 1.0}) is False
    assert validator.subtensor.calls == 1
