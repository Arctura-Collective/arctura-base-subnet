"""Runtime compatibility checks for the validator neuron."""

from types import SimpleNamespace

from arctura_base.protocol import BaseSubnetSynapse
from neurons.validator import ArcturaValidator


def test_validator_tempo_fallback_handles_none_config():
    class Config:
        tempo = None

    tempo = getattr(Config, "tempo", None) or ArcturaValidator.DEFAULT_TEMPO
    assert tempo == ArcturaValidator.DEFAULT_TEMPO


def test_active_miner_uids_only_include_serving_axons():
    validator = object.__new__(ArcturaValidator)
    validator.wallet = SimpleNamespace(hotkey=SimpleNamespace(ss58_address="validator"))
    validator.metagraph = SimpleNamespace(
        hotkeys=["offline", "miner", "validator"],
        S=[1.0, 1.0, 1.0],
        axons=[
            SimpleNamespace(is_serving=False),
            SimpleNamespace(is_serving=True),
            SimpleNamespace(is_serving=True),
        ],
    )

    assert validator._get_active_miner_uids() == [1]


def test_scoring_handles_fewer_responses_than_requested():
    validator = object.__new__(ArcturaValidator)
    validator.metagraph = SimpleNamespace(hotkeys=["miner-0", "miner-1"])
    validator._calibration_history = {}
    validator._CALIBRATION_WINDOW = 100
    missing = BaseSubnetSynapse(base_state_hash=None)

    scores = validator._score_all_responses(
        synapses=[missing],
        miner_uids=[0, 1],
        reference_hash="0xabc",
        response_block=1,
    )

    assert scores == {0: 0.0, 1: 0.0}
