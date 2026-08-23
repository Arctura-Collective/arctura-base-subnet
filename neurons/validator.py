"""
neurons/validator.py

Arctura Base subnet validator.

Issues BaseSubnetSynapse mandates to registered miners, scores their
attestations using Resonance BFT, and sets weights via Yuma Consensus.

Scoring cycle (every tempo period, ~72 minutes):
    1. Sync metagraph — get current miner UIDs and stake
    2. Generate a Base chain mandate (block range, query type)
    3. Query all miners simultaneously via bt.dendrite
    4. Fetch the reference Base block hash independently
    5. Score each response with Resonance BFT (4 dimensions + stewardship)
    6. Detect potential Sybil collisions
    7. Normalize scores and set Yuma Consensus weights on-chain

Usage:
    python neurons/validator.py \\
        --wallet.name validator \\
        --wallet.hotkey default \\
        --subtensor.network test \\
        --netuid 1

Arctura Council · Coreweaver · arctura.network/base
Apache-2.0
"""

from __future__ import annotations

import argparse
import os
import time
import uuid
from collections import defaultdict
from typing import Any

import bittensor as bt

from arctura_base.base_rpc import BaseRPCClient
from arctura_base.bittensor_runtime import load_metagraph
from arctura_base.incentive import (
    apply_stewardship_modifier,
    compute_calibration_accuracy,
    detect_hash_collision,
    normalize_weights,
    score_response,
)
from arctura_base.protocol import BaseSubnetSynapse


class ArcturaValidator:
    """
    Arctura Base subnet validator.

    Manages the full scoring cycle: mandate generation → miner querying
    → Resonance BFT scoring → Yuma Consensus weight-setting.

    Validator quality is determined by:
        • Consistency of weight-setting (validators who miss tempos earn less)
        • Alignment with consensus (outlier weight-sets are discounted by Yuma)
        • Uptime (axon must be reachable for other validators to coordinate)
    """

    # Block time on Bittensor (~12 seconds)
    BLOCK_TIME_SECONDS = 12

    # Tempo period in blocks (default: 360 blocks = ~72 minutes)
    DEFAULT_TEMPO = 360
    WEIGHT_SET_RETRIES = 3
    WEIGHT_SET_RETRY_SECONDS = 5

    def __init__(self, config: Any | None = None) -> None:
        self.config = config or self._build_config()

        bt.logging(config=self.config, logging_dir=self.config.full_path)
        bt.logging.info("Initializing Arctura Base validator...")

        # Bittensor components
        self.wallet = bt.Wallet(config=self.config)
        self.subtensor = bt.Subtensor(config=self.config)
        self.dendrite = bt.Dendrite(wallet=self.wallet)
        self.metagraph = load_metagraph(self.subtensor, self.config.netuid)

        # Base chain client (for reference block hash verification)
        self.base_client = BaseRPCClient()

        # Calibration history: {hotkey: [accuracy_float, ...]}
        self._calibration_history: dict[str, list[float]] = defaultdict(list)
        self._CALIBRATION_WINDOW = 100  # rolling window

        bt.logging.info(
            f"Arctura Base validator initialized\n"
            f"  wallet:  {self.wallet}\n"
            f"  network: {self.config.subtensor.network}\n"
            f"  netuid:  {self.config.netuid}\n"
            f"  timeout: {self.config.timeout}s"
        )

    # ── Config ────────────────────────────────────────────────────────────

    @staticmethod
    def _build_config() -> Any:
        # Bittensor v10 disables CLI parsing by default. Neuron entry points
        # must honor their explicit wallet, network, netuid, and runtime flags.
        os.environ["BT_NO_PARSE_CLI_ARGS"] = "false"
        parser = argparse.ArgumentParser(
            description="Arctura Base subnet validator",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        bt.Subtensor.add_args(parser)
        bt.logging.add_args(parser)
        bt.Wallet.add_args(parser)

        parser.add_argument("--netuid", type=int, default=1, help="Bittensor subnet UID.")
        parser.add_argument(
            "--timeout", type=float, default=30.0, help="Timeout in seconds for miner responses."
        )
        parser.add_argument(
            "--tempo",
            type=int,
            default=int(os.environ.get("VALIDATOR_TEMPO", "360")),
            help="Validator scoring cadence in Bittensor blocks.",
        )

        config = bt.Config(parser)
        config.full_path = (
            f"~/.bittensor/validators/{config.wallet.name}"
            f"/{config.wallet.hotkey}/netuid{config.netuid}/validator"
        )
        return config

    # ── Mandate generation ────────────────────────────────────────────────

    def _build_mandate(self) -> BaseSubnetSynapse:
        """
        Generate a Base chain mandate for this tempo period.

        Phase 01: rotates through query types to diversify miner capability testing.
        Phase 02: pulls mandates from the on-chain mandate registry.

        Returns a fully-formed BaseSubnetSynapse ready to send to miners.
        """
        current_block = self.metagraph.block.item()
        latest_base = self.base_client.get_latest_block_number()

        # Deadline: current Bittensor block + tempo/4 blocks
        tempo = getattr(self.config, "tempo", None) or self.DEFAULT_TEMPO
        deadline_block = current_block + tempo // 4

        # Rotate mandate type to test different miner capabilities
        cycle = current_block % 3
        if cycle == 0:
            query_type = "balance"
            mandate_payload: dict[str, Any] = {
                "address": "0x4200000000000000000000000000000000000006",  # WETH on Base
            }
        elif cycle == 1:
            query_type = "state"
            mandate_payload = {
                "function_name": "totalSupply",
                "args": [],
                "abi": [
                    {
                        "name": "totalSupply",
                        "type": "function",
                        "inputs": [],
                        "outputs": [{"type": "uint256"}],
                        "stateMutability": "view",
                    }
                ],
            }
        else:
            query_type = "balance"
            mandate_payload = {
                "address": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",  # USDC on Base
            }

        return BaseSubnetSynapse(
            mandate_id=str(uuid.uuid4()),
            base_block_range=(latest_base, latest_base),
            contract_address=(
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC
                if query_type == "state"
                else None
            ),
            query_type=query_type,
            mandate_payload=mandate_payload,
            deadline_block=deadline_block,
        )

    # ── Scoring ───────────────────────────────────────────────────────────

    def _get_active_miner_uids(self) -> list[int]:
        """
        Return serving Axon UIDs, excluding this validator's own UID.

        A validator permit is not a reliable role signal: on small subnets a
        miner may also hold a permit. Excluding permitted UIDs can therefore
        remove every eligible miner from the scoring set.
        """
        try:
            my_uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
        except ValueError:
            my_uid = -1

        return [
            uid
            for uid in range(len(self.metagraph.S))
            if uid != my_uid and bool(self.metagraph.axons[uid].is_serving)
        ]

    def _get_historical_calibration(self, hotkey: str) -> float:
        """
        Return the rolling-window average calibration accuracy for a miner.
        Defaults to 0.5 (neutral) for new miners with no history.
        """
        history = self._calibration_history.get(hotkey, [])
        if not history:
            return 0.5
        return sum(history) / len(history)

    def _update_calibration(
        self, hotkey: str, reported_confidence: float, actual_base_score: float
    ) -> None:
        """Update calibration history for a miner after scoring."""
        accuracy = compute_calibration_accuracy(reported_confidence, actual_base_score)
        history = self._calibration_history[hotkey]
        history.append(accuracy)
        # Keep rolling window
        self._calibration_history[hotkey] = history[-self._CALIBRATION_WINDOW :]

    def _score_all_responses(
        self,
        synapses: list[BaseSubnetSynapse],
        miner_uids: list[int],
        reference_hash: str,
        response_block: int,
    ) -> dict[int, float]:
        """
        Score all miner responses with Resonance BFT.

        Returns:
            {uid: final_score} for all queried miners.
        """
        scores: dict[int, float] = {}

        # Sybil detection: collect all state hashes
        uid_hashes = {}
        for index, uid in enumerate(miner_uids):
            synapse = synapses[index] if index < len(synapses) else None
            uid_hashes[uid] = synapse.base_state_hash if synapse else None
        sybil_flagged = detect_hash_collision(uid_hashes)
        if sybil_flagged:
            bt.logging.warning(
                f"Potential Sybil behavior detected — UIDs sharing hash: {sybil_flagged}"
            )

        for index, uid in enumerate(miner_uids):
            synapse = synapses[index] if index < len(synapses) else None
            hotkey = self.metagraph.hotkeys[uid]

            if synapse is None or synapse.base_state_hash is None:
                bt.logging.warning(f"No response from uid={uid}")
                scores[uid] = 0.0
                continue

            calibration = self._get_historical_calibration(hotkey)

            base_score = score_response(
                synapse=synapse,
                live_block_hash=reference_hash,
                response_block=response_block,
                historical_calibration=calibration,
            )

            # Apply P5 Stewardship modifier
            final_score = apply_stewardship_modifier(base_score, synapse.energy_tag)

            # Apply Sybil penalty
            if uid in sybil_flagged:
                final_score *= 0.25
                bt.logging.warning(f"Sybil penalty applied to uid={uid}")

            # Update calibration history for next round
            self._update_calibration(hotkey, synapse.confidence, base_score)

            # Store Resonance score back on synapse for logging
            synapse.resonance_score = final_score
            scores[uid] = final_score

            bt.logging.info(
                f"uid={uid} | "
                f"base={base_score:.3f} | "
                f"energy={synapse.energy_tag} | "
                f"final={final_score:.3f}"
            )

        return scores

    # ── Weight setting ────────────────────────────────────────────────────

    def _set_weights(self, scores: dict[int, float]) -> bool:
        """Normalize scores and submit weights to Yuma Consensus on-chain."""
        uids = list(scores.keys())
        raw_weights = [scores[uid] for uid in uids]
        if not uids or sum(raw_weights) <= 0.0:
            bt.logging.warning("Skipping weight submission: no miner earned a positive score.")
            return False
        normalized = normalize_weights(raw_weights)

        for attempt in range(1, self.WEIGHT_SET_RETRIES + 1):
            try:
                result = self.subtensor.set_weights(
                    wallet=self.wallet,
                    netuid=self.config.netuid,
                    uids=uids,
                    weights=normalized,
                    wait_for_inclusion=True,
                )
                if isinstance(result, tuple):
                    success, msg = result
                else:
                    success = bool(getattr(result, "success", getattr(result, "is_success", False)))
                    msg = getattr(result, "error_message", "") or getattr(result, "message", "")
            except Exception as exc:
                success = False
                msg = str(exc)

            if success:
                top_uid = uids[normalized.index(max(normalized))]
                bt.logging.success(
                    f"Weights set | miners={len(uids)} | "
                    f"top_uid={top_uid} | top_weight={max(normalized):.3f}"
                )
                return True

            if "too soon to commit weights" in str(msg).lower():
                bt.logging.info(f"Weight submission deferred by chain cooldown: {msg}")
                return False

            if attempt < self.WEIGHT_SET_RETRIES:
                bt.logging.warning(
                    f"Weight-setting attempt {attempt}/{self.WEIGHT_SET_RETRIES} failed: {msg}. "
                    f"Retrying in {self.WEIGHT_SET_RETRY_SECONDS}s..."
                )
                time.sleep(self.WEIGHT_SET_RETRY_SECONDS)
            else:
                bt.logging.error(
                    f"Weight-setting failed after {self.WEIGHT_SET_RETRIES} attempts: {msg}"
                )
        return False

    # ── Run loop ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Enter the main validator loop."""
        bt.logging.info(f"Arctura Base validator live | netuid={self.config.netuid}")

        tempo = getattr(self.config, "tempo", None) or self.DEFAULT_TEMPO
        sleep_seconds = tempo * self.BLOCK_TIME_SECONDS  # ~72 minutes

        while True:
            try:
                # Sync metagraph
                self.metagraph.sync(subtensor=self.subtensor)
                response_block = self.metagraph.block.item()

                miner_uids = self._get_active_miner_uids()
                if not miner_uids:
                    bt.logging.warning("No miners registered yet — waiting.")
                    time.sleep(60)
                    continue

                # Build mandate and query all miners
                mandate = self._build_mandate()
                axons = [self.metagraph.axons[uid] for uid in miner_uids]

                bt.logging.info(
                    f"Issuing mandate | id={mandate.mandate_id[:8]}... "
                    f"type={mandate.query_type} | miners={len(miner_uids)}"
                )

                synapses = self.dendrite.query(
                    axons=axons,
                    synapse=mandate,
                    deserialize=False,
                    timeout=self.config.timeout,
                )

                # Fetch reference block hash independently (anti-fabrication)
                block_num = (
                    mandate.base_block_range[1] or self.base_client.get_latest_block_number()
                )
                reference_hash = self.base_client.get_block_hash(block_num)

                # Score responses
                scores = self._score_all_responses(
                    synapses=synapses,
                    miner_uids=miner_uids,
                    reference_hash=reference_hash,
                    response_block=response_block,
                )

                # Set weights
                if scores:
                    self._set_weights(scores)

                bt.logging.info(
                    f"Tempo complete | sleeping {sleep_seconds}s (~{sleep_seconds // 60} minutes)"
                )
                time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                bt.logging.info("Validator shutdown requested.")
                break
            except Exception as exc:
                bt.logging.error(f"Validator loop error: {exc}")
                time.sleep(60)

        close = getattr(self.subtensor, "close", None)
        if close is not None:
            close()


def main() -> None:
    """Console entry point for the Arctura Base validator."""
    ArcturaValidator().run()


if __name__ == "__main__":
    main()
