# Mainnet Go / No-Go Checklist

Every item must be checked before running `btcli subnet create` on Finney.
Use [MAINNET_READINESS_TRACKER.md](MAINNET_READINESS_TRACKER.md) for the
issue-backed blocker list, external closure evidence, and non-mutating
verification commands.

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
- [ ] `neurons/validator.py` — submitted at least two non-zero testnet weights in the current evidence window
- [x] `pytest tests/ -q` passes with no failures (273 tests on 2026-08-24)
- [ ] Bittensor v10.5 testnet miner and validator complete one attestation and at least two non-zero weight commits in the current evidence window
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
- [x] Auto-restart configured with systemd for both neurons
- [x] Five-minute health timer configured for supervised testnet evidence
- [ ] Monitoring host selected for mainnet axon uptime

User-level service templates and a five-minute preflight timer are provided in
`deploy/systemd/`. Track the supervised testnet run in
[SYSTEMD_48H_CHECKLIST.md](SYSTEMD_48H_CHECKLIST.md). Check these items only
after enabling them on the launch host and reviewing the 48-hour journal with
`arctura-collect-evidence`.

## Final
- [ ] Go/no-go reviewed by at least one other person
- [ ] `arctura-readiness-audit` returns `ok: true` for the reviewed evidence,
  burn-cost, AWS tfvars, and treasury policy artifacts
- [ ] `arctura-mainnet-approval` packet generated from green evidence and a
  Finney burn-cost snapshot collected within 30 minutes
- [ ] Command ready to paste (do not type fresh under pressure):
  ```bash
  btcli subnet create --wallet.name owner --subtensor.network finney
  ```
