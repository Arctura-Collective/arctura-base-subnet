# ARCTURA Base Testnet Run Plan

This plan verifies ARCTURA Base end-to-end on testnet netuid `505` without disturbing the older template loop.

## Isolation

- Existing template loop may occupy ports `8091` and `8092`.
- ARCTURA Base uses alternate ports:
  - miner axon: `8191`
  - validator process: no axon port yet
- Local runtime config lives in ignored `.env`.
- Do not commit `.env`, logs, process IDs, or wallet material.

## Preflight

```bash
cd /mnt/c/Users/virtu/ARCTURA/arctura-base-subnet
/home/brimstone/gbrain-work/subnet-template-venv/bin/python -m pytest tests/ -v
/home/brimstone/gbrain-work/subnet-template-venv/bin/python - <<'PY'
from arctura_base.base_rpc import BaseRPCClient
client = BaseRPCClient(timeout=10)
block = client.get_latest_block_number()
print("base_latest_block", block)
print("base_block_hash_prefix", client.get_block_hash(block)[:18])
PY
```

Expected:

- tests pass
- Base RPC returns a block number and block hash prefix
- `git status --ignored --short .env` shows `.env` as ignored

## Bounded Startup Checks

Miner:

```bash
timeout 90s /home/brimstone/gbrain-work/subnet-template-venv/bin/python neurons/miner.py \
  --wallet.name arctura_miner \
  --wallet.hotkey default \
  --subtensor.network test \
  --netuid 505 \
  --axon.port 8191 \
  --logging.info
```

Success signal:

```text
Arctura Base miner live
axon: Axon(..., 8191, ..., started, ['Synapse', 'BaseSubnetSynapse'])
```

Validator:

```bash
timeout 180s /home/brimstone/gbrain-work/subnet-template-venv/bin/python neurons/validator.py \
  --wallet.name arctura_val \
  --wallet.hotkey default \
  --subtensor.network test \
  --netuid 505 \
  --timeout 5 \
  --tempo 360 \
  --logging.info
```

Success signals:

```text
Arctura Base validator live | netuid=505
Issuing mandate | id=... type=... | miners=...
```

Expected if miner is not running concurrently:

```text
No response from uid=...
```

That verifies validator initialization and mandate issuance, but not full miner response flow.

## Concurrent End-to-End Run

Run miner first in one terminal:

```bash
cd /mnt/c/Users/virtu/ARCTURA/arctura-base-subnet
/home/brimstone/gbrain-work/subnet-template-venv/bin/python neurons/miner.py \
  --wallet.name arctura_miner \
  --wallet.hotkey default \
  --subtensor.network test \
  --netuid 505 \
  --axon.port 8191 \
  --logging.info
```

Run validator in another terminal:

```bash
cd /mnt/c/Users/virtu/ARCTURA/arctura-base-subnet
/home/brimstone/gbrain-work/subnet-template-venv/bin/python neurons/validator.py \
  --wallet.name arctura_val \
  --wallet.hotkey default \
  --subtensor.network test \
  --netuid 505 \
  --timeout 10 \
  --tempo 360 \
  --logging.info
```

## Success Criteria

Minimum proof:

- miner reaches live axon state
- validator reaches live loop
- validator issues a mandate
- miner receives the `BaseSubnetSynapse`
- miner returns `base_state_hash`, `merkle_proof`, `block_hash_anchor`, `execution_trace`
- validator assigns a non-zero score for at least one miner

Preferred proof:

- same mandate output hashes deterministically across repeated runs at the same Base block
- no uncaught exceptions
- no wallet or `.env` material in logs
- resource footprint is recorded for the run

## Current Known Results

- Miner bounded startup reached live state on port `8191`.
- Validator bounded startup reached live loop and issued a mandate.
- Validator observed no responses because the ARCTURA Base miner was not running concurrently.
- Validator weight setting can report `No attempt made. Perhaps it is too soon to commit weights!`; this is expected during short bounded runs.
