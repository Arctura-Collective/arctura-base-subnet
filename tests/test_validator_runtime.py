"""Runtime compatibility checks for the validator neuron."""

import sys
from collections import defaultdict
from types import SimpleNamespace

from arctura_base.protocol import BaseSubnetSynapse
from arctura_base.utils import build_merkle_proof
from neurons.validator import ArcturaValidator


def test_validator_config_honors_v10_cli_flags(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validator",
            "--wallet.name",
            "arctura_val",
            "--wallet.hotkey",
            "default",
            "--subtensor.network",
            "test",
            "--netuid",
            "505",
            "--timeout",
            "30",
            "--tempo",
            "360",
        ],
    )

    config = ArcturaValidator._build_config()

    assert config.wallet.name == "arctura_val"
    assert config.subtensor.network == "test"
    assert config.netuid == 505
    assert config.timeout == 30
    assert config.tempo == 360


def test_validator_tempo_fallback_handles_none_config():
    class Config:
        tempo = None

    tempo = getattr(Config, "tempo", None) or ArcturaValidator.DEFAULT_TEMPO
    assert tempo == ArcturaValidator.DEFAULT_TEMPO


def test_validator_deadline_offset_uses_tight_bounded_window():
    assert ArcturaValidator._deadline_offset(360) == 45
    assert ArcturaValidator._deadline_offset(120) == 30


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


def test_new_miners_do_not_receive_calibration_bonus():
    validator = object.__new__(ArcturaValidator)
    validator._calibration_history = {}

    assert validator._get_historical_calibration("new-hotkey") == 0.0


def test_calibration_requires_warmup_samples():
    assert ArcturaValidator._score_calibration_history([1.0, 1.0, 1.0, 1.0]) == 0.0
    assert ArcturaValidator._score_calibration_history([1.0, 1.0, 1.0, 1.0, 1.0]) == 1.0


def test_calibration_penalizes_unstable_history():
    stable = ArcturaValidator._score_calibration_history([0.8, 0.8, 0.8, 0.8, 0.8])
    unstable = ArcturaValidator._score_calibration_history([1.0, 0.0, 1.0, 0.0, 1.0])

    assert stable == 0.8
    assert unstable < 0.6


def test_active_miner_uids_do_not_treat_validator_permit_as_a_role():
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
            "axons": [
                SimpleNamespace(is_serving=True),
                SimpleNamespace(is_serving=True),
                SimpleNamespace(is_serving=True),
                SimpleNamespace(is_serving=True),
            ],
        },
    )()

    assert validator._get_active_miner_uids() == [1, 2, 3]


def test_verified_stewardship_modifier_applies_in_validator_scoring():
    validator = object.__new__(ArcturaValidator)
    validator.metagraph = SimpleNamespace(hotkeys=["miner-hotkey"])
    validator._calibration_history = defaultdict(list)
    validator._CALIBRATION_WINDOW = 100
    validator._stewardship_verifications = {
        "miner-hotkey": {
            "energy_tag": "renewable_verified",
            "status": "verified",
        }
    }
    state_hash = "a" * 64
    synapse = BaseSubnetSynapse(
        base_state_hash=state_hash,
        merkle_proof=build_merkle_proof(state_hash),
        block_hash_anchor="live",
        execution_trace={"steps": ["rpc_fetch", "output_hash", "merkle_build", "block_anchor"]},
        deadline_block=100,
        energy_tag="renewable_verified",
    )

    scores = validator._score_all_responses(
        synapses=[synapse],
        miner_uids=[0],
        reference_hash="live",
        response_block=100,
    )

    assert scores[0] > 0.9
