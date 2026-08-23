# Dependency Audit

Last reviewed: 2026-08-23

## Summary

The runtime should stay light: only dependencies that support Bittensor networking, Base RPC access, configuration, and operator output belong in the default install.

## Runtime Dependencies

| Package | Status | Purpose | Notes |
|---------|--------|---------|-------|
| `bittensor>=10.5.0,<11.0.0` | keep | subnet runtime, wallet, subtensor, axon/dendrite | `10.5.0` is verified against testnet netuid `505`; v11 removes neuron networking. |
| `web3>=6.0.0` | keep | Base RPC reads | Verified against public Base RPC. |
| `pydantic>=2.0.0` | keep | Bittensor synapse model compatibility | Already required by Bittensor; keep explicit for schemas. |
| `python-dotenv>=1.0.0` | keep | ignored local `.env` runtime config | Used by CLI and Base RPC client. |

## Removed

| Package | Reason |
|---------|--------|
| `torch>=2.0.0` | Bittensor v10 accepts plain UID/weight lists; the project no longer uses tensors. |
| `httpx>=0.24.0` | No runtime imports remain; the environment checker uses the standard library. |
| `rich>=13.0.0` | No runtime imports remain. |
| `merkletools>=1.0.3` | Unused and pulls `pysha3`, which fails to build on Python 3.12. Internal proof helpers live in `arctura_base/utils.py`. |
| `coincurve>=18.0.0` | Unused by current code path. Reintroduce only if signing or secp256k1 verification becomes part of the protocol. |

## Compatibility Notes

- `requirements.txt` should mirror `pyproject.toml` for runtime dependency intent.
- Python 3.12 compatibility currently requires avoiding `pysha3`.
- `websockets` may be downgraded by `web3` dependency resolution; rerun Bittensor startup checks after dependency updates.
- CI should prefer `pip install -e ".[dev]"` from `pyproject.toml`.

## License Risk

No new high-risk licenses were identified in the retained direct dependencies. Transitive dependencies should be reviewed before any production launch or grant submission.
