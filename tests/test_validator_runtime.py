"""Runtime compatibility checks for the validator neuron."""

import sys
from collections import defaultdict
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from arctura_base.protocol import BaseSubnetSynapse
from arctura_base.utils import build_merkle_proof
from neurons.validator import ArcturaValidator


def test_validator_init_wires_bittensor_runtime():
    config = SimpleNamespace(
        full_path="/tmp/arctura-validator",
        netuid=505,
        timeout=30.0,
        stewardship_verification_file="",
        subtensor=SimpleNamespace(network="test"),
    )
    wallet = MagicMock()
    subtensor = MagicMock()
    dendrite = MagicMock()
    metagraph = MagicMock()

    with (
        patch("neurons.validator.bt.logging"),
        patch("neurons.validator.bt.Wallet", return_value=wallet) as wallet_cls,
        patch("neurons.validator.bt.Subtensor", return_value=subtensor) as subtensor_cls,
        patch("neurons.validator.bt.Dendrite", return_value=dendrite) as dendrite_cls,
        patch("neurons.validator.load_metagraph", return_value=metagraph) as load_graph,
        patch("neurons.validator.BaseRPCClient") as base_client_cls,
        patch(
            "neurons.validator.load_stewardship_verifications", return_value={}
        ) as load_stewardship,
    ):
        validator = ArcturaValidator(config=config)

    wallet_cls.assert_called_once_with(config=config)
    subtensor_cls.assert_called_once_with(config=config)
    dendrite_cls.assert_called_once_with(wallet=wallet)
    load_graph.assert_called_once_with(subtensor, 505)
    base_client_cls.assert_called_once_with()
    load_stewardship.assert_called_once_with("")
    assert validator._CALIBRATION_WINDOW == 100
    assert validator._stewardship_verifications == {}


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


def test_build_mandate_rotates_query_payloads():
    validator = object.__new__(ArcturaValidator)
    validator.config = SimpleNamespace(tempo=120)
    validator.base_client = SimpleNamespace(get_latest_block_number=lambda: 21_000_000)

    for block, expected_query, expected_contract in (
        (300, "balance", None),
        (301, "state", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        (302, "balance", None),
    ):
        validator.metagraph = SimpleNamespace(block=SimpleNamespace(item=lambda block=block: block))

        mandate = validator._build_mandate()

        assert mandate.query_type == expected_query
        assert mandate.base_block_range == (21_000_000, 21_000_000)
        assert mandate.contract_address == expected_contract
        assert mandate.deadline_block == block + 30
        assert mandate.mandate_id


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


def test_active_miner_uids_handles_unregistered_validator_hotkey():
    validator = object.__new__(ArcturaValidator)
    validator.wallet = SimpleNamespace(hotkey=SimpleNamespace(ss58_address="missing"))
    validator.metagraph = SimpleNamespace(
        hotkeys=["miner"],
        S=[1.0],
        axons=[SimpleNamespace(is_serving=True)],
    )

    assert validator._get_active_miner_uids() == [0]


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


def test_sybil_penalty_applies_to_repeated_hashes():
    validator = object.__new__(ArcturaValidator)
    validator.metagraph = SimpleNamespace(hotkeys=["miner-0", "miner-1", "miner-2"])
    validator._calibration_history = defaultdict(list)
    validator._CALIBRATION_WINDOW = 100
    validator._stewardship_verifications = {}
    state_hash = "b" * 64
    synapses = [
        BaseSubnetSynapse(
            base_state_hash=state_hash,
            merkle_proof=build_merkle_proof(state_hash),
            block_hash_anchor="live",
            execution_trace={"steps": ["rpc_fetch", "output_hash", "merkle_build", "block_anchor"]},
            deadline_block=100,
            energy_tag="unknown",
        )
        for _ in range(3)
    ]

    scores = validator._score_all_responses(
        synapses=synapses,
        miner_uids=[0, 1, 2],
        reference_hash="live",
        response_block=100,
    )

    assert all(0 < score < 0.5 for score in scores.values())
    assert all(synapse.resonance_score == scores[index] for index, synapse in enumerate(synapses))


def test_update_calibration_keeps_rolling_window():
    validator = object.__new__(ArcturaValidator)
    validator._calibration_history = defaultdict(list)
    validator._CALIBRATION_WINDOW = 2

    validator._update_calibration("miner", reported_confidence=1.0, actual_base_score=1.0)
    validator._update_calibration("miner", reported_confidence=0.5, actual_base_score=1.0)
    validator._update_calibration("miner", reported_confidence=0.0, actual_base_score=1.0)

    assert len(validator._calibration_history["miner"]) == 2


def test_validator_run_handles_no_miners_then_shutdown(monkeypatch):
    validator = object.__new__(ArcturaValidator)
    validator.config = SimpleNamespace(netuid=505, tempo=1, timeout=30.0)
    validator.subtensor = MagicMock()
    validator.metagraph = MagicMock()
    validator.metagraph.block.item.return_value = 10
    validator.metagraph.sync.side_effect = [None, KeyboardInterrupt()]
    validator._get_active_miner_uids = MagicMock(return_value=[])

    monkeypatch.setattr("neurons.validator.time.sleep", MagicMock())

    validator.run()

    assert validator.metagraph.sync.call_count == 2
    validator.subtensor.close.assert_called_once()


def test_validator_run_queries_scores_sets_weights_and_shutdown(monkeypatch):
    validator = object.__new__(ArcturaValidator)
    validator.config = SimpleNamespace(netuid=505, tempo=1, timeout=30.0)
    validator.subtensor = MagicMock()
    validator.metagraph = SimpleNamespace(
        axons=["axon-1"],
        block=SimpleNamespace(item=MagicMock(return_value=100)),
        sync=MagicMock(),
    )
    validator.dendrite = MagicMock()
    validator.dendrite.query.return_value = [BaseSubnetSynapse(base_state_hash=None)]
    validator.base_client = MagicMock()
    validator.base_client.get_block_hash.return_value = "live"
    validator._get_active_miner_uids = MagicMock(return_value=[0])
    validator._build_mandate = MagicMock(
        return_value=BaseSubnetSynapse(
            mandate_id="mandate",
            base_block_range=(21_000_000, 21_000_000),
            query_type="balance",
        )
    )
    validator._score_all_responses = MagicMock(return_value={0: 0.5})
    validator._set_weights = MagicMock(return_value=True)

    def shutdown_sleep(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("neurons.validator.time.sleep", shutdown_sleep)

    validator.run()

    validator.dendrite.query.assert_called_once_with(
        axons=["axon-1"],
        synapse=validator._build_mandate.return_value,
        deserialize=False,
        timeout=30.0,
    )
    validator.base_client.get_block_hash.assert_called_once_with(21_000_000)
    validator._set_weights.assert_called_once_with({0: 0.5})
    validator.subtensor.close.assert_called_once()


def test_validator_run_handles_loop_error_then_shutdown(monkeypatch):
    validator = object.__new__(ArcturaValidator)
    validator.config = SimpleNamespace(netuid=505, tempo=1)
    validator.subtensor = SimpleNamespace(close=MagicMock())
    validator.metagraph = SimpleNamespace(sync=MagicMock(side_effect=RuntimeError("boom")))

    sleeps = iter([KeyboardInterrupt()])

    def sleep_then_shutdown(seconds):
        outcome = next(sleeps)
        if isinstance(outcome, BaseException):
            raise outcome

    monkeypatch.setattr("neurons.validator.time.sleep", sleep_then_shutdown)

    try:
        validator.run()
    except KeyboardInterrupt:
        pass

    validator.metagraph.sync.assert_called_once_with(subtensor=validator.subtensor)


def test_validator_main_constructs_and_runs():
    with patch("neurons.validator.ArcturaValidator") as validator_cls:
        from neurons.validator import main

        main()

    validator_cls.return_value.run.assert_called_once()
