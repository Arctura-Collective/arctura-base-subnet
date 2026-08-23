"""Command line helpers for operating the Arctura Base subnet."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = os.environ.get("ARCTURA_NETWORK", os.environ.get("BT_NETWORK", "test"))
DEFAULT_NETUID = os.environ.get("ARCTURA_NETUID", os.environ.get("BT_NETUID", "1"))
DEFAULT_MINER_WALLET = os.environ.get(
    "ARCTURA_MINER_WALLET", os.environ.get("BT_MINER_WALLET", "miner")
)
DEFAULT_VALIDATOR_WALLET = os.environ.get(
    "ARCTURA_VALIDATOR_WALLET", os.environ.get("BT_VALIDATOR_WALLET", "validator")
)
DEFAULT_HOTKEY = os.environ.get("ARCTURA_HOTKEY", os.environ.get("BT_DEFAULT_HOTKEY", "default"))
DEFAULT_WALLET_PATH = Path(os.path.expanduser("~/.bittensor/wallets"))


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


def finney_confirmed(args: argparse.Namespace, action: str) -> bool:
    """Require an explicit acknowledgment for TAO-moving Finney commands."""
    if args.network != "finney" or getattr(args, "confirm_finney", False):
        return True
    print(
        f"Refusing to {action} on Finney without --confirm-finney. "
        "Recheck wallet, netuid, amount, and live chain state.",
        file=sys.stderr,
    )
    return False


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
    if not finney_confirmed(args, "register"):
        return 2
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
    if not finney_confirmed(args, "stake"):
        return 2
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
            "--tempo",
            str(args.tempo),
            "--logging.info",
        ]
    )


def run_preflight(args: argparse.Namespace) -> dict[str, Any]:
    """Check Base RPC and Bittensor registration without starting neurons."""
    from arctura_base.base_rpc import BaseRPCClient

    result: dict[str, Any] = {
        "ok": True,
        "network": args.network,
        "netuid": int(args.netuid),
        "checks": {},
    }
    checks: dict[str, Any] = result["checks"]

    try:
        client = BaseRPCClient(timeout=args.timeout)
        block = client.get_latest_block_number()
        chain_id = int(client.w3.eth.chain_id)
        checks["base_rpc"] = {
            "ok": args.network != "finney" or chain_id == 8453,
            "chain_id": chain_id,
            "block": block,
            "block_hash": client.get_block_hash(block),
        }
        if not checks["base_rpc"]["ok"]:
            checks["base_rpc"]["error"] = "Finney launch requires Base mainnet chain_id 8453."
            result["ok"] = False
    except Exception as exc:
        checks["base_rpc"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        result["ok"] = False

    wallet_path = Path(args.wallet_path).expanduser()
    wallets = {}
    for role, name in (("miner", args.miner_wallet), ("validator", args.validator_wallet)):
        hotkey_file = wallet_path / name / "hotkeys" / args.hotkey
        wallets[role] = {"name": name, "hotkey": args.hotkey, "exists": hotkey_file.is_file()}
        if not hotkey_file.is_file():
            result["ok"] = False
    checks["wallets"] = wallets

    subtensor = None
    try:
        import bittensor as bt

        subtensor = bt.subtensor(network=args.network)
        metagraph = subtensor.metagraph(int(args.netuid))
        registered = {}
        for role, name in (("miner", args.miner_wallet), ("validator", args.validator_wallet)):
            address = bt.wallet(
                name=name, hotkey=args.hotkey, path=str(wallet_path)
            ).hotkey.ss58_address
            registered[role] = {"registered": address in metagraph.hotkeys}
            if address not in metagraph.hotkeys:
                result["ok"] = False
        checks["metagraph"] = {
            "ok": all(item["registered"] for item in registered.values()),
            "uids": len(metagraph.hotkeys),
            "wallets": registered,
        }
    except Exception as exc:
        checks["metagraph"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        result["ok"] = False
    finally:
        close = getattr(subtensor, "close", None)
        if close is not None:
            close()

    return result


def command_preflight(args: argparse.Namespace) -> int:
    result = run_preflight(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        print(f"Arctura preflight: {status} | network={args.network} netuid={args.netuid}")
        for name, check in result["checks"].items():
            check_ok = check.get("ok", all(v.get("exists", False) for v in check.values()))
            print(f"  {'PASS' if check_ok else 'FAIL'} {name}")
    return 0 if result["ok"] else 1


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
    register.add_argument("--confirm-finney", action="store_true")
    register.set_defaults(func=command_register)

    stake = subparsers.add_parser("stake", help="Stake TAO to a wallet hotkey on the subnet.")
    add_common_args(stake)
    add_wallet_args(stake, DEFAULT_MINER_WALLET)
    stake.add_argument("--amount", type=float, required=True)
    stake.add_argument("--confirm-finney", action="store_true")
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
    validator.add_argument("--tempo", default=os.environ.get("VALIDATOR_TEMPO", "360"))
    validator.set_defaults(func=command_validator)

    preflight = subparsers.add_parser(
        "preflight", help="Check Base RPC, wallets, and Bittensor registration."
    )
    add_common_args(preflight)
    preflight.add_argument("--miner-wallet", default=DEFAULT_MINER_WALLET)
    preflight.add_argument("--validator-wallet", default=DEFAULT_VALIDATOR_WALLET)
    preflight.add_argument("--hotkey", default=DEFAULT_HOTKEY)
    preflight.add_argument("--wallet-path", default=str(DEFAULT_WALLET_PATH))
    preflight.add_argument("--timeout", type=int, default=10)
    preflight.add_argument("--json", action="store_true")
    preflight.set_defaults(func=command_preflight)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
