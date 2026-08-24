"""Validator weight-setting retry tests."""

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


class PreflightCooldownSubtensor:
    def __init__(self):
        self.calls = 0

    def get_uid_for_hotkey_on_subnet(self, hotkey, netuid):
        return 7

    def blocks_since_last_update(self, netuid, uid):
        return 10

    def weights_rate_limit(self, netuid):
        return 20

    def set_weights(self, **kwargs):
        self.calls += 1
        return True, "ok"


class PreflightReadySubtensor(PreflightCooldownSubtensor):
    def blocks_since_last_update(self, netuid, uid):
        return 21


class PreflightUnregisteredSubtensor(PreflightCooldownSubtensor):
    def get_uid_for_hotkey_on_subnet(self, hotkey, netuid):
        return None


class PreflightErrorSubtensor(PreflightCooldownSubtensor):
    def get_uid_for_hotkey_on_subnet(self, hotkey, netuid):
        raise RuntimeError("preflight unavailable")


class ObjectResultSubtensor(PreflightReadySubtensor):
    def set_weights(self, **kwargs):
        self.calls += 1
        return type("Result", (), {"success": True, "message": "ok"})()


class EmptyMessageSubtensor(PreflightReadySubtensor):
    def set_weights(self, **kwargs):
        self.calls += 1
        return type("Result", (), {"success": False, "message": ""})()


class RaisingSetWeightsSubtensor(PreflightReadySubtensor):
    def set_weights(self, **kwargs):
        self.calls += 1
        raise RuntimeError("submission failed")


class Hotkey:
    ss58_address = "validator-hotkey"


class Wallet:
    hotkey = Hotkey()


def test_set_weights_retries_after_failure():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = DummySubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = object()
    validator.WEIGHT_SET_RETRIES = 2
    validator.WEIGHT_SET_RETRY_SECONDS = 0

    assert validator._set_weights({1: 1.0}) is True
    assert validator.subtensor.calls == 2


def test_set_weights_skips_all_zero_scores():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = DummySubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = object()
    assert validator._set_weights({1: 0.0, 2: 0.0}) is False
    assert validator.subtensor.calls == 0


def test_set_weights_does_not_retry_chain_cooldown():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = CooldownSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = object()
    validator.WEIGHT_SET_RETRIES = 3
    assert validator._set_weights({1: 1.0}) is False
    assert validator.subtensor.calls == 1


def test_set_weights_preflights_rate_limit_without_retrying():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = PreflightCooldownSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = Wallet()
    validator.WEIGHT_SET_RETRIES = 3

    assert validator._set_weights({1: 1.0}) is False
    assert validator.subtensor.calls == 0


def test_set_weights_proceeds_when_preflight_rate_limit_passes():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = PreflightReadySubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = Wallet()
    validator.WEIGHT_SET_RETRIES = 3

    assert validator._set_weights({1: 1.0}) is True
    assert validator.subtensor.calls == 1


def test_weights_rate_limit_treats_unregistered_hotkey_as_limited():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = PreflightUnregisteredSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = Wallet()

    assert validator._weights_rate_limited() is True


def test_weights_rate_limit_allows_attempt_when_preflight_errors():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = PreflightErrorSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = Wallet()

    assert validator._weights_rate_limited() is False


def test_set_weights_accepts_object_result_success():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = ObjectResultSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = Wallet()
    validator.WEIGHT_SET_RETRIES = 1

    assert validator._set_weights({1: 1.0}) is True
    assert validator.subtensor.calls == 1


def test_set_weights_handles_empty_messages_and_final_failure():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = EmptyMessageSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = Wallet()
    validator.WEIGHT_SET_RETRIES = 1

    assert validator._set_weights({1: 1.0}) is False
    assert validator.subtensor.calls == 1


def test_set_weights_handles_submission_exceptions():
    validator = object.__new__(ArcturaValidator)
    validator.subtensor = RaisingSetWeightsSubtensor()
    validator.config = type("Config", (), {"netuid": 505})()
    validator.wallet = Wallet()
    validator.WEIGHT_SET_RETRIES = 1

    assert validator._set_weights({1: 1.0}) is False
    assert validator.subtensor.calls == 1
