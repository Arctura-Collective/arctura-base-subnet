"""CLI parser and command construction tests."""

import importlib
from types import SimpleNamespace

from arctura_base import cli


def test_parser_exposes_miner_defaults():
    importlib.reload(cli)
    args = cli.build_parser().parse_args(["miner"])
    assert args.network == "test"
    assert args.netuid in {"1", "505"}
    assert args.wallet in {"miner", "arctura_miner"}
    assert args.hotkey == "default"
    assert args.port in {"8091", "8191"}


def test_cli_help_uses_arctura_parser(capsys):
    try:
        cli.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out
    assert "Operate the Arctura Base subnet." in output
    assert "metagraph" in output


def test_cli_defaults_can_come_from_env(monkeypatch):
    monkeypatch.setenv("ARCTURA_NETWORK", "test")
    monkeypatch.setenv("ARCTURA_NETUID", "505")
    monkeypatch.setenv("ARCTURA_MINER_WALLET", "arctura_miner")
    monkeypatch.setenv("ARCTURA_HOTKEY", "default")

    reloaded = importlib.reload(cli)
    args = reloaded.build_parser().parse_args(["miner"])
    assert args.netuid == "505"
    assert args.wallet == "arctura_miner"

    importlib.reload(cli)


def test_cli_defaults_can_come_from_documented_bt_env(monkeypatch):
    for key in (
        "ARCTURA_NETWORK",
        "ARCTURA_NETUID",
        "ARCTURA_MINER_WALLET",
        "ARCTURA_VALIDATOR_WALLET",
        "ARCTURA_HOTKEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("BT_NETWORK", "test")
    monkeypatch.setenv("BT_NETUID", "505")
    monkeypatch.setenv("BT_MINER_WALLET", "arctura_miner")
    monkeypatch.setenv("BT_VALIDATOR_WALLET", "arctura_val")
    monkeypatch.setenv("BT_DEFAULT_HOTKEY", "default")

    reloaded = importlib.reload(cli)
    miner = reloaded.build_parser().parse_args(["miner"])
    validator = reloaded.build_parser().parse_args(["validator"])

    assert miner.netuid == "505"
    assert miner.wallet == "arctura_miner"
    assert validator.wallet == "arctura_val"


def test_finney_register_requires_explicit_confirmation(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "run_command", lambda command: calls.append(command) or 0)

    exit_code = cli.main(["register", "--network", "finney", "--netuid", "42"])

    assert exit_code == 2
    assert calls == []
    assert "--confirm-finney" in capsys.readouterr().err


def test_finney_register_runs_after_explicit_confirmation(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_command", lambda command: calls.append(command) or 0)

    exit_code = cli.main(["register", "--network", "finney", "--netuid", "42", "--confirm-finney"])

    assert exit_code == 0
    assert calls[0][0:3] == ["btcli", "subnet", "register"]


def test_finney_stake_requires_explicit_confirmation(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "run_command", lambda command: calls.append(command) or 0)

    exit_code = cli.main(["stake", "--network", "finney", "--netuid", "42", "--amount", "1"])

    assert exit_code == 2
    assert calls == []
    assert "--confirm-finney" in capsys.readouterr().err


def test_validator_command_propagates_tempo(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_command", lambda command: calls.append(command) or 0)

    assert cli.main(["validator", "--tempo", "120"]) == 0
    assert calls[0][calls[0].index("--tempo") + 1] == "120"


def test_register_command_uses_btcli(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "run_command", lambda command: calls.append(command) or 0)

    exit_code = cli.main(
        [
            "register",
            "--network",
            "test",
            "--netuid",
            "505",
            "--wallet",
            "arctura_miner",
            "--hotkey",
            "default",
        ]
    )

    assert exit_code == 0
    assert calls == [
        [
            "btcli",
            "subnet",
            "register",
            "--netuid",
            "505",
            "--subtensor.network",
            "test",
            "--wallet.name",
            "arctura_miner",
            "--wallet.hotkey",
            "default",
        ]
    ]


def test_preflight_reports_all_checks(monkeypatch, tmp_path):
    for wallet_name in ("miner", "validator"):
        hotkeys = tmp_path / wallet_name / "hotkeys"
        hotkeys.mkdir(parents=True)
        (hotkeys / "default").write_text("test", encoding="utf-8")

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 3
            self.w3 = SimpleNamespace(eth=SimpleNamespace(chain_id=8453))

        def get_latest_block_number(self):
            return 123

        def get_block_hash(self, block):
            assert block == 123
            return "0xabc"

    class FakeWallet:
        def __init__(self, name, **kwargs):
            self.hotkey = SimpleNamespace(ss58_address=f"{name}-address")

    closed = []
    fake_bt = SimpleNamespace(
        subtensor=lambda network: SimpleNamespace(
            metagraph=lambda netuid: SimpleNamespace(
                hotkeys=["miner-address", "validator-address"]
            ),
            close=lambda: closed.append(True),
        ),
        wallet=FakeWallet,
    )
    monkeypatch.setattr("arctura_base.base_rpc.BaseRPCClient", FakeClient)
    monkeypatch.setitem(__import__("sys").modules, "bittensor", fake_bt)

    args = cli.build_parser().parse_args(
        [
            "preflight",
            "--netuid",
            "505",
            "--miner-wallet",
            "miner",
            "--validator-wallet",
            "validator",
            "--wallet-path",
            str(tmp_path),
            "--timeout",
            "3",
        ]
    )
    result = cli.run_preflight(args)

    assert result["ok"] is True
    assert result["checks"]["base_rpc"]["block"] == 123
    assert result["checks"]["metagraph"]["uids"] == 2
    assert closed == [True]


def test_preflight_fails_when_wallets_are_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "arctura_base.base_rpc.BaseRPCClient",
        lambda timeout: SimpleNamespace(
            w3=SimpleNamespace(eth=SimpleNamespace(chain_id=8453)),
            get_latest_block_number=lambda: 123,
            get_block_hash=lambda block: "0xabc",
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "bittensor",
        SimpleNamespace(
            subtensor=lambda network: SimpleNamespace(
                metagraph=lambda netuid: SimpleNamespace(hotkeys=[])
            ),
            wallet=lambda name, **kwargs: SimpleNamespace(
                hotkey=SimpleNamespace(ss58_address=f"{name}-address")
            ),
        ),
    )
    args = cli.build_parser().parse_args(["preflight", "--wallet-path", str(tmp_path)])

    assert cli.run_preflight(args)["ok"] is False


def test_finney_preflight_rejects_base_sepolia(monkeypatch, tmp_path):
    for wallet_name in ("miner", "validator"):
        hotkeys = tmp_path / wallet_name / "hotkeys"
        hotkeys.mkdir(parents=True)
        (hotkeys / "default").write_text("test", encoding="utf-8")
    monkeypatch.setattr(
        "arctura_base.base_rpc.BaseRPCClient",
        lambda timeout: SimpleNamespace(
            w3=SimpleNamespace(eth=SimpleNamespace(chain_id=84532)),
            get_latest_block_number=lambda: 123,
            get_block_hash=lambda block: "0xabc",
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "bittensor",
        SimpleNamespace(
            subtensor=lambda network: SimpleNamespace(
                metagraph=lambda netuid: SimpleNamespace(
                    hotkeys=["miner-address", "validator-address"]
                )
            ),
            wallet=lambda name, **kwargs: SimpleNamespace(
                hotkey=SimpleNamespace(ss58_address=f"{name}-address")
            ),
        ),
    )
    args = cli.build_parser().parse_args(
        ["preflight", "--network", "finney", "--wallet-path", str(tmp_path)]
    )

    result = cli.run_preflight(args)

    assert result["ok"] is False
    assert result["checks"]["base_rpc"]["chain_id"] == 84532
