# VPS 48-Hour Testnet Runbook

Use this when moving the Arctura Base 48-hour evidence run from a local PC to an
always-on Linux host.

## Host Requirements

- Ubuntu 22.04/24.04 or comparable systemd Linux host
- 2 vCPU, 4 GB RAM minimum
- 20 GB disk minimum
- Stable public network
- Inbound miner axon port open: `8191/tcp`
- Outbound access to Bittensor testnet and Base RPC
- SSH key login only; no password SSH

## Important Evidence Rule

Moving to a VPS starts a new uninterrupted evidence window. The 48-hour clock
should be measured from the later `ActiveEnterTimestamp` of the miner and
validator services on the VPS.

Do not combine the local PC run and VPS run into one evidence window.

## 1. Prepare the VPS

Run on the VPS:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip build-essential curl ufw
sudo ufw allow OpenSSH
sudo ufw allow 8191/tcp
sudo ufw --force enable
```

Create the working directory:

```bash
mkdir -p ~/gbrain-work
```

## 2. Copy Repo and Wallets

From the local machine, copy the repo and testnet wallets:

```bash
rsync -az --exclude '.git' \
  /home/brimstone/gbrain-work/arctura-base-subnet/ \
  USER@VPS_HOST:~/gbrain-work/arctura-base-subnet/

rsync -az \
  ~/.bittensor/wallets/arctura_miner \
  ~/.bittensor/wallets/arctura_val \
  USER@VPS_HOST:~/.bittensor/wallets/
```

Keep owner/mainnet wallets off the VPS unless there is a deliberate launch
decision. For the 48-hour testnet evidence run, the VPS only needs the testnet
miner and validator wallets listed above.

## 3. Install Python Environment

Run on the VPS:

```bash
cd ~/gbrain-work/arctura-base-subnet
python3 -m venv .venv
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install -e .
```

If dependency installation fails because the host lacks build packages, install
the missing package with `apt` and rerun `.venv/bin/pip install -e .`.

## 4. Configure Operator Env

Run on the VPS:

```bash
mkdir -p ~/.config/systemd/user ~/.config
cp deploy/systemd/operator.env.example ~/.config/arctura-base-subnet.env
chmod 600 ~/.config/arctura-base-subnet.env
```

Edit `~/.config/arctura-base-subnet.env`:

```bash
ARCTURA_REPO=/home/USER/gbrain-work/arctura-base-subnet
ARCTURA_PYTHON=/home/USER/gbrain-work/arctura-base-subnet/.venv/bin/python
BASE_RPC_URL=https://mainnet.base.org
BT_NETWORK=test
BT_NETUID=505
BT_VALIDATOR_WALLET=arctura_val
BT_MINER_WALLET=arctura_miner
BT_DEFAULT_HOTKEY=default
MINER_AXON_PORT=8191
VALIDATOR_TIMEOUT=30
VALIDATOR_TEMPO=360
ARCTURA_ENERGY_TAG=unknown
```

Verify:

```bash
stat -c '%a %n' ~/.config/arctura-base-subnet.env
```

Expected mode: `600`.

## 5. Install and Start Services

Run on the VPS:

```bash
cd ~/gbrain-work/arctura-base-subnet
cp deploy/systemd/arctura-*.service deploy/systemd/arctura-health.timer \
  ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now arctura-miner arctura-validator arctura-health.timer
loginctl enable-linger "$USER"
```

Verify:

```bash
systemctl --user status arctura-miner arctura-validator arctura-health.timer
systemctl --user show arctura-miner arctura-validator \
  --property=ActiveState,SubState,MainPID,ActiveEnterTimestamp,NRestarts
loginctl show-user "$USER" --property=Linger
```

## 6. Confirm First Cycle

Run on the VPS:

```bash
journalctl --user -u arctura-miner -n 80 --no-pager
journalctl --user -u arctura-validator -n 120 --no-pager
journalctl --user -u arctura-health -n 120 --no-pager
```

Expected:

- Miner logs `Arctura Base miner live`
- Validator logs `Arctura Base validator live`
- Miner receives and attests a mandate
- Validator scores UID `1`
- Health service logs JSON with `"ok": true`

## 7. Track the 48-Hour Window

Record the later service start time:

```bash
systemctl --user show arctura-miner arctura-validator \
  --property=ActiveEnterTimestamp
```

That timestamp is the evidence window anchor. Update
`docs/SYSTEMD_48H_CHECKLIST.md` if this VPS becomes the active evidence host.

Monitor without restarting:

```bash
systemctl --user show arctura-miner arctura-validator \
  --property=ActiveState,SubState,NRestarts,ActiveEnterTimestamp
journalctl --user -u arctura-validator -n 100 --no-pager
journalctl --user -u arctura-health -n 100 --no-pager
```

## 8. Collect Evidence After 48 Hours

Run on the VPS after the uninterrupted 48-hour window:

```bash
cd ~/gbrain-work/arctura-base-subnet
arctura-collect-evidence --output-dir runs/mainnet-evidence
python -m json.tool runs/mainnet-evidence/report.json
```

The mainnet blocker remains open unless `report.json` contains `"ok": true`.

## Stop or Roll Back

```bash
systemctl --user stop arctura-validator arctura-miner arctura-health.timer
systemctl --user disable arctura-validator arctura-miner arctura-health.timer
```

Stopping the services invalidates the current 48-hour evidence window.
