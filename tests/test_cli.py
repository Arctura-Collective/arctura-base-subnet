"""CLI parser and command construction tests."""

import importlib

from arctura_base import cli


def test_parser_exposes_miner_defaults():
    args = cli.build_parser().parse_args(["miner"])
    assert args.network == "test"
    assert args.netuid == "1"
    assert args.wallet == "miner"
    assert args.hotkey == "default"
    assert args.port == "8091"


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
