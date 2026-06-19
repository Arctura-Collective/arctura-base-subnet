# Mainnet Go / No-Go Checklist

Every item must be checked before running `btcli subnet create` on Finney.

## Capital
- [ ] Burn cost checked within last 30 minutes
- [ ] Owner coldkey balance ≥ burn cost + 20% buffer
- [ ] Validator hotkey funded for recycle_register
- [ ] Miner hotkey funded for recycle_register
- [ ] 30-day server cost budgeted

## Code
- [x] `arctura_base/protocol.py` — BaseSubnetSynapse tested locally
- [x] `neurons/miner.py` — successful mandates return valid `base_state_hash`
- [x] `neurons/miner.py` — returns valid `merkle_proof` (verify_merkle_proof passes)
- [x] `neurons/miner.py` — `block_hash_anchor` matches real Base block hash
- [x] `neurons/validator.py` — submitted non-zero testnet weights successfully
- [x] `pytest tests/ -v` passes with no failures (80 tests on 2026-06-19)
- [ ] No uncaught exceptions in 48h testnet run

## Network
- [x] Miner axon reachable by the testnet validator (testnet port 8191)
- [x] Validator is dendrite-only; no inbound axon is required by this architecture
- [ ] At least 1 external validator confirmed for post-launch
- [ ] Bittensor Discord announcement drafted (#subnet-owners)

## Operations
- [ ] Owner coldkey mnemonic stored offline in ≥2 separate locations
- [ ] Validator coldkey mnemonic stored offline
- [ ] Miner coldkey mnemonic stored offline
- [ ] Auto-restart configured (systemd or PM2) for both neurons
- [ ] Monitoring configured for axon uptime

User-level service templates and a five-minute preflight timer are provided in
`deploy/systemd/`. Check these items only after enabling them on the launch host
and reviewing the 48-hour journal with `arctura-evidence`.

## Final
- [ ] Go/no-go reviewed by at least one other person
- [ ] Command ready to paste (do not type fresh under pressure):
  ```bash
  btcli subnet create --wallet.name owner --subtensor.network finney
  ```
