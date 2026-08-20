"""Smoke tests for shell launcher environment defaults."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_start_miner_uses_documented_env_keys():
    script = (ROOT / "scripts" / "start_miner.sh").read_text(encoding="utf-8")
    assert 'NETWORK="${NETWORK:-${BT_NETWORK:-test}}"' in script
    assert 'NETUID="${NETUID:-${BT_NETUID:-1}}"' in script
    assert 'WALLET="${WALLET:-${BT_MINER_WALLET:-miner}}"' in script
    assert 'HOTKEY="${HOTKEY:-${BT_DEFAULT_HOTKEY:-default}}"' in script


def test_start_validator_uses_documented_env_keys():
    script = (ROOT / "scripts" / "start_validator.sh").read_text(encoding="utf-8")
    assert 'NETWORK="${NETWORK:-${BT_NETWORK:-test}}"' in script
    assert 'NETUID="${NETUID:-${BT_NETUID:-1}}"' in script
    assert 'WALLET="${WALLET:-${BT_VALIDATOR_WALLET:-validator}}"' in script
    assert 'HOTKEY="${HOTKEY:-${BT_DEFAULT_HOTKEY:-default}}"' in script
    assert 'TEMPO="${VALIDATOR_TEMPO:-360}"' in script
    assert '--tempo "${TEMPO}"' in script
