"""Runtime compatibility checks for the validator neuron."""

from neurons.validator import ArcturaValidator


def test_validator_tempo_fallback_handles_none_config():
    class Config:
        tempo = None

    tempo = getattr(Config, "tempo", None) or ArcturaValidator.DEFAULT_TEMPO
    assert tempo == ArcturaValidator.DEFAULT_TEMPO


def test_active_miner_uids_exclude_self_and_validator_permits():
    validator = object.__new__(ArcturaValidator)
    validator.wallet = type(
        "Wallet",
        (),
        {"hotkey": type("Hotkey", (), {"ss58_address": "validator-self"})()},
    )()
    validator.metagraph = type(
        "Metagraph",
        (),
        {
            "hotkeys": ["validator-self", "validator-peer", "miner-one", "miner-two"],
            "S": [1, 1, 1, 1],
            "validator_permit": [True, True, False, False],
        },
    )()

    assert validator._get_active_miner_uids() == [2, 3]
