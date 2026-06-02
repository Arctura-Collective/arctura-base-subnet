"""
neurons/miner.py
Bittensor SDK v10 compatible miner for Arctura Network.

Key v10 changes from the v7.4.0 template:
- bt.config() replaced with argparse-based config via bt.config(parser)
- metagraph.sync() returns the metagraph (not a chainable object); active check is separate
- axon.serve / axon.start / axon.stop API unchanged at v10
- Python 3.10+ required
"""

import argparse
import time
import bittensor as bt

from arctura.protocol import ArcturaSynapse


def get_config() -> bt.config:
    parser = argparse.ArgumentParser(description="Arctura miner")
    parser.add_argument("--netuid", type=int, default=1, help="Subnet netuid")
    parser.add_argument("--wallet.name", type=str, default="default")
    parser.add_argument("--wallet.hotkey", type=str, default="default")
    parser.add_argument("--subtensor.network", type=str, default="test")
    parser.add_argument("--axon.port", type=int, default=8091)
    bt.logging.add_args(parser)
    bt.wallet.add_args(parser)
    bt.subtensor.add_args(parser)
    bt.axon.add_args(parser)
    config = bt.config(parser)
    return config


def forward(synapse: ArcturaSynapse) -> ArcturaSynapse:
    """
    Core miner logic. Replace this with Arctura's actual compute task.
    Currently echoes the prompt reversed as a placeholder.
    """
    bt.logging.info(f"Received prompt: {synapse.prompt!r}")
    synapse.response = synapse.prompt[::-1]  # TODO: replace with real task
    return synapse


def main():
    config = get_config()
    bt.logging(config=config)
    bt.logging.info(f"Config: {config}")

    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(config.netuid)

    bt.logging.info(f"Wallet: {wallet}")
    bt.logging.info(f"Hotkey SS58: {wallet.hotkey.ss58_address}")

    # Verify registration
    if wallet.hotkey.ss58_address not in metagraph.hotkeys:
        bt.logging.error(
            f"Hotkey {wallet.hotkey.ss58_address} not registered on netuid {config.netuid}. "
            "Register first: btcli subnet register"
        )
        return

    axon = bt.axon(wallet=wallet, config=config)
    axon.attach(forward_fn=forward)
    axon.serve(netuid=config.netuid, subtensor=subtensor)
    axon.start()

    bt.logging.info(f"Miner axon live on netuid {config.netuid} | port {config.axon.port}")

    step = 0
    try:
        while True:
            time.sleep(12)  # ~1 block
            step += 1

            # Resync metagraph every 100 blocks
            if step % 100 == 0:
                metagraph = subtensor.metagraph(config.netuid)
                if wallet.hotkey.ss58_address not in metagraph.hotkeys:
                    bt.logging.error("Miner deregistered. Exiting.")
                    break
                bt.logging.info(f"Metagraph resync at step {step}")

    except KeyboardInterrupt:
        bt.logging.info("Interrupted. Stopping axon.")
    finally:
        axon.stop()


if __name__ == "__main__":
    main()
