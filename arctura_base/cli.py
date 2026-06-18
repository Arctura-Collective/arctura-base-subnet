"""Command line helpers for operating the Arctura Base subnet."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = os.environ.get("ARCTURA_NETWORK", "test")
DEFAULT_NETUID = os.environ.get("ARCTURA_NETUID", "1")
DEFAULT_MINER_WALLET = os.environ.get("ARCTURA_MINER_WALLET", "miner")
DEFAULT_VALIDATOR_WALLET = os.environ.get("ARCTURA_VALIDATOR_WALLET", "validator")
DEFAULT_HOTKEY = os.environ.get("ARCTURA_HOTKEY", "default")


def run_command(command: list[str], cwd: Path = REPO_ROOT) -> int:
    print("$ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=False).returncode


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--network", default=DEFAULT_NETWORK)
    parser.add_argument("--netuid", default=DEFAULT_NETUID)


def add_wallet_args(parser: argparse.ArgumentParser, default_wallet: str) -> None:
    parser.add_argument("--wallet", default=default_wallet)
    parser.add_argument("--hotkey", default=DEFAULT_HOTKEY)


def btcli_args(args: argparse.Namespace) -> list[str]:
    return [
        "--netuid",
        str(args.netuid),
        "--subtensor.network",
        args.network,
    ]


def command_metagraph(args: argparse.Namespace) -> int:
    return run_command(["btcli", "subnet", "metagraph", *btcli_args(args)])


def command_hyperparams(args: argparse.Namespace) -> int:
    return run_command(["btcli", "subnet", "hyperparameters", *btcli_args(args)])


def command_overview(args: argparse.Namespace) -> int:
    return run_command(
        [
            "btcli",
            "wallet",
            "overview",
            "--wallet.name",
            args.wallet,
            "--subtensor.network",
            args.network,
        ]
    )


def command_register(args: argparse.Namespace) -> int:
    return run_command(
        [
            "btcli",
            "subnet",
            "register",
            *btcli_args(args),
            "--wallet.name",
            args.wallet,
            "--wallet.hotkey",
            args.hotkey,
        ]
    )


def command_stake(args: argparse.Namespace) -> int:
    return run_command(
        [
            "btcli",
            "stake",
            "add",
            "--wallet.name",
            args.wallet,
            "--wallet.hotkey",
            args.hotkey,
            "--netuid",
            str(args.netuid),
            "--subtensor.network",
            args.network,
            "--amount",
            str(args.amount),
        ]
    )


def command_miner(args: argparse.Namespace) -> int:
    return run_command(
        [
            sys.executable,
            "neurons/miner.py",
            "--wallet.name",
            args.wallet,
            "--wallet.hotkey",
            args.hotkey,
            "--subtensor.network",
            args.network,
            "--netuid",
            str(args.netuid),
            "--axon.port",
            str(args.port),
            "--logging.info",
        ]
    )


def command_validator(args: argparse.Namespace) -> int:
    return run_command(
        [
            sys.executable,
            "neurons/validator.py",
            "--wallet.name",
            args.wallet,
            "--wallet.hotkey",
            args.hotkey,
            "--subtensor.network",
            args.network,
            "--netuid",
            str(args.netuid),
            "--timeout",
            str(args.timeout),
            "--logging.info",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arctura", description="Operate the Arctura Base subnet.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    metagraph = subparsers.add_parser("metagraph", help="Display subnet metagraph.")
    add_common_args(metagraph)
    metagraph.set_defaults(func=command_metagraph)

    hyperparams = subparsers.add_parser("hyperparams", help="Display subnet hyperparameters.")
    add_common_args(hyperparams)
    hyperparams.set_defaults(func=command_hyperparams)

    overview = subparsers.add_parser("overview", help="Show wallet overview.")
    overview.add_argument("--network", default=DEFAULT_NETWORK)
    overview.add_argument("--wallet", default=DEFAULT_MINER_WALLET)
    overview.set_defaults(func=command_overview)

    register = subparsers.add_parser("register", help="Register a wallet hotkey on the subnet.")
    add_common_args(register)
    add_wallet_args(register, DEFAULT_MINER_WALLET)
    register.set_defaults(func=command_register)

    stake = subparsers.add_parser("stake", help="Stake TAO to a wallet hotkey on the subnet.")
    add_common_args(stake)
    add_wallet_args(stake, DEFAULT_MINER_WALLET)
    stake.add_argument("--amount", type=float, required=True)
    stake.set_defaults(func=command_stake)

    miner = subparsers.add_parser("miner", help="Start the Arctura Base miner.")
    add_common_args(miner)
    add_wallet_args(miner, DEFAULT_MINER_WALLET)
    miner.add_argument("--port", default=os.environ.get("MINER_AXON_PORT", "8091"))
    miner.set_defaults(func=command_miner)

    validator = subparsers.add_parser("validator", help="Start the Arctura Base validator.")
    add_common_args(validator)
    add_wallet_args(validator, DEFAULT_VALIDATOR_WALLET)
    validator.add_argument("--timeout", default=os.environ.get("VALIDATOR_TIMEOUT", "30"))
    validator.set_defaults(func=command_validator)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
