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
