"""
neurons/validator.py
Bittensor SDK v10 compatible validator for Arctura Network.

Key v10 changes from the v7.4.0 template:
- subtensor.set_weights() now returns ExtrinsicResponse, not bool
  → check response.is_success instead of `if response`
- mechid=0 param added to set_weights and metagraph calls (explicit, future-proof)
- dendrite.query() signature and async behavior unchanged at surface level
- bt.config() now requires parser argument
- Python 3.10+ required
"""

import argparse
import time
import torch
import bittensor as bt

from arctura.protocol import ArcturaSynapse


def get_config() -> bt.config:
    parser = argparse.ArgumentParser(description="Arctura validator")
    parser.add_argument("--netuid", type=int, default=1, help="Subnet netuid")
    parser.add_argument("--wallet.name", type=str, default="default")
    parser.add_argument("--wallet.hotkey", type=str, default="default")
    parser.add_argument("--subtensor.network", type=str, default="test")
    parser.add_argument("--query_interval", type=int, default=600, help="Seconds between scoring rounds")
    bt.logging.add_args(parser)
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.dendrite.add_args(parser)
    config = bt.config(parser)
    return config


def score_responses(responses: list[str | None]) -> torch.FloatTensor:
    """
    Scoring logic. Returns a float tensor aligned with `responses`.

    Current implementation: 1.0 if the miner returned a non-empty response, 0.0 otherwise.
    TODO: Replace with Arctura's actual quality metric.
    """
    return torch.FloatTensor([1.0 if r else 0.0 for r in responses])


def main():
    config = get_config()
    bt.logging(config=config)
    bt.logging.info(f"Config: {config}")

    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(config.netuid, mechid=0)
    dendrite = bt.dendrite(wallet=wallet)

    bt.logging.info(f"Validator hotkey: {wallet.hotkey.ss58_address}")

    if wallet.hotkey.ss58_address not in metagraph.hotkeys:
        bt.logging.error(
            f"Hotkey {wallet.hotkey.ss58_address} not registered on netuid {config.netuid}."
        )
        return

    bt.logging.info(f"Validator running on netuid {config.netuid}")

    while True:
        try:
            # Resync metagraph
            metagraph = subtensor.metagraph(config.netuid, mechid=0)
            uids = metagraph.uids.tolist()
            axons = [metagraph.axons[uid] for uid in uids]

            if not axons:
                bt.logging.warning("No miners found in metagraph. Waiting...")
                time.sleep(config.query_interval)
                continue

            # Query all miners
            synapse = ArcturaSynapse(prompt="arctura test query v10")
            responses: list[str | None] = dendrite.query(
                axons=axons,
                synapse=synapse,
                deserialize=True,
                timeout=12,
            )

            bt.logging.info(f"Queried {len(axons)} miners. Got {sum(1 for r in responses if r)} responses.")

            # Score and normalize
            scores = score_responses(responses)
            weights = torch.nn.functional.normalize(scores, p=1, dim=0)

            bt.logging.info(f"Scores:  {scores}")
            bt.logging.info(f"Weights: {weights}")

            # Set weights — v10: returns ExtrinsicResponse, check .is_success
            response = subtensor.set_weights(
                wallet=wallet,
                netuid=config.netuid,
                uids=uids,
                weights=weights.tolist(),
                wait_for_inclusion=False,
                mechid=0,
            )

            if response.is_success:
                bt.logging.info("Weights set successfully.")
            else:
                bt.logging.warning(f"set_weights failed: {response.message}")

        except Exception as e:
            bt.logging.error(f"Validator loop error: {e}")

        time.sleep(config.query_interval)


if __name__ == "__main__":
    main()
