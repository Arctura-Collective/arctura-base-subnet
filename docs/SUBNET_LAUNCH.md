# Subnet Launch Guide

Complete walkthrough: wallet setup → local chain → testnet → Finney mainnet.

## Phase 0 — Wallets & Capital

```bash
# Check live burn cost FIRST — it changes daily
btcli subnet burn_cost --subtensor.network finney

# Create wallets
bash scripts/setup_wallets.sh finney
```

Minimum TAO: **burn cost + 20% buffer + validator/miner recycle fees**.  
Keep ≥100 TAO liquid. Check [taostats.io/subnets](https://taostats.io/subnets) for live cost.

## Phase 1 — Local Chain

```bash
# Start local subtensor (requires Docker)
git clone https://github.com/opentensor/subtensor && cd subtensor
bash scripts/run/subtensor.sh -e local --no-purge

# Register locally
btcli subnet create --wallet.name owner --subtensor.network local
btcli subnet recycle_register --netuid 1 --wallet.name validator --subtensor.network local
btcli subnet recycle_register --netuid 1 --wallet.name miner    --subtensor.network local

# Run both neurons (separate terminals)
bash scripts/start_miner.sh    --network local --netuid 1
bash scripts/start_validator.sh --network local --netuid 1
```

## Phase 2 — Testnet

```bash
# Free testnet TAO from Bittensor Discord #testnet-faucet
btcli subnet create --wallet.name owner --subtensor.network test
# Note your netuid from output

bash scripts/start_miner.sh    --network test --netuid N
bash scripts/start_validator.sh --network test --netuid N
bash scripts/check_metagraph.sh test N
```

Run for **48+ hours** before proceeding. Confirm non-zero weights in metagraph.

### Supervised 48-hour run

Install the user-level systemd units on the Linux host that owns the Bittensor
wallets. Keep the operator environment file private; it contains deployment
paths and may later contain a private RPC URL.

```bash
mkdir -p ~/.config/systemd/user ~/.config
cp deploy/systemd/arctura-*.service deploy/systemd/arctura-health.timer \
  ~/.config/systemd/user/
cp deploy/systemd/operator.env.example ~/.config/arctura-base-subnet.env
chmod 600 ~/.config/arctura-base-subnet.env
# Edit ARCTURA_REPO, ARCTURA_PYTHON, network, netuid, and wallet names.

systemctl --user daemon-reload
systemctl --user enable --now arctura-miner arctura-validator arctura-health.timer
loginctl enable-linger "$USER"
```

Verify restart and monitoring state:

```bash
systemctl --user status arctura-miner arctura-validator arctura-health.timer
journalctl --user -u arctura-miner -u arctura-validator --since "48 hours ago"
journalctl --user -u arctura-health --since "48 hours ago"
systemctl --user show arctura-miner arctura-validator \
  --property=NRestarts,ActiveEnterTimestamp
```

The 48-hour gate passes only when both neurons remained active, health checks
continued succeeding, at least one non-zero weight commit is present, and the
logs contain no uncaught exceptions. Do not infer success from process state
alone.

## Phase 3 — Mainnet Registration

See [GO_NO_GO_CHECKLIST.md](GO_NO_GO_CHECKLIST.md) before running any of these.

```bash
# Final burn cost check (run this within 30 minutes of registering)
btcli subnet burn_cost --subtensor.network finney

# Register — this burns TAO
btcli subnet create --wallet.name owner --subtensor.network finney
# RECORD YOUR NETUID

# Register neurons
btcli subnet recycle_register --netuid N --wallet.name validator --subtensor.network finney
btcli subnet recycle_register --netuid N --wallet.name miner    --subtensor.network finney

# Verify
btcli subnet metagraph --netuid N --subtensor.network finney

# Start immediately
bash scripts/start_miner.sh    --network finney --netuid N
bash scripts/start_validator.sh --network finney --netuid N
```

Emissions activate 7 days post-registration. Immunity period: 4 months.
