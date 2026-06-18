"""CLI parser and command construction tests."""

from arctura_base import cli


def test_parser_exposes_miner_defaults():
    args = cli.build_parser().parse_args(["miner"])
    assert args.network == "test"
    assert args.netuid == "1"
    assert args.wallet == "miner"
    assert args.hotkey == "default"
    assert args.port == "8091"


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
