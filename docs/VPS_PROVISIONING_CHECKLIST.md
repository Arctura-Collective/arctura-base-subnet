# VPS Provisioning Checklist — Arctura Testnet 505

This checklist outlines the end-to-end operator workflow for provisioning a fresh, always-on Linux VPS host for the Arctura Base testnet run (netuid `505`).

---

## 🚨 Security Warning (Critical)

> [!WARNING]
> **DO NOT COPY OWNER OR MAINNET WALLETS TO THE VPS.**
>
> To safeguard your assets from theft, **only** copy the testnet wallets `arctura_miner` and `arctura_val` (using their `default` hotkeys) to this host. Never copy any keys containing mainnet funds or administrative capabilities onto an always-on public-facing VPS.

---

## 📋 Provisioning Workflow

### 1. Host Preparation
Provision a provider-neutral VPS instance meeting the following minimum system requirements:
- **Operating System:** Ubuntu 22.04 or 24.04 (LTS)
- **Specs:** 2 vCPU, 4 GB RAM, 20 GB disk (minimum SSD storage recommended)
- **SSH access:** Password SSH access must be disabled; use **SSH keys only**.
- **Inbound network rules:** Port `8191/tcp` (miner axon port) and port `22` (SSH) must be allowed in the VPS provider's network security group/firewall.

On the VPS, install core dependencies and set up the local firewall:
```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip build-essential curl ufw

# Set up local firewall
sudo ufw allow OpenSSH
sudo ufw allow 8191/tcp
sudo ufw --force enable
```

Create the working directories:
```bash
mkdir -p ~/gbrain-work
mkdir -p ~/.bittensor/wallets
```

---

### 2. Copy Repository & Testnet Wallets
From the **local machine**, sync the codebase (excluding git history) and copy **only** the testnet wallets required for this run:

```bash
# Sync repository to VPS
rsync -az --exclude '.git' \
  /home/brimstone/gbrain-work/arctura-base-subnet/ \
  USER@VPS_HOST:~/gbrain-work/arctura-base-subnet/

# Sync ONLY the miner and validator wallets to VPS
rsync -az \
  ~/.bittensor/wallets/arctura_miner \
  ~/.bittensor/wallets/arctura_val \
  USER@VPS_HOST:~/.bittensor/wallets/
```

---

### 3. Install Python Environment
On the **VPS**, initialize the Python virtual environment and install the repository in editable mode:
```bash
cd ~/gbrain-work/arctura-base-subnet
python3 -m venv .venv
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install -e .
```
*(If dependencies fail to build due to missing system headers, search for and install the corresponding `-dev` packages via `apt` and run the install command again).*

---

### 4. Configure Operator Environment
Create the configuration directory, copy the systemd environment template, and set private file permissions:
```bash
mkdir -p ~/.config
cp deploy/systemd/operator.env.example ~/.config/arctura-base-subnet.env
chmod 600 ~/.config/arctura-base-subnet.env
```

Edit `~/.config/arctura-base-subnet.env` to populate the specific configurations:
```ini
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
*(Replace `USER` with the actual VPS username).*

---

### 5. Install & Start systemd Services
Install the user units, reload the user-level daemon, enable/start services, and configure user lingering so services persist after SSH logout:
```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/arctura-*.service deploy/systemd/arctura-health.timer \
  ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now arctura-miner arctura-validator arctura-health.timer
loginctl enable-linger "$USER"
```

---

## 🔍 Verification & Health Audits

Execute these commands to verify that all components are correctly configured and operating.

### Verify Firewall & Inbound Port Routing
Verify that the UFW rules are active and port `8191/tcp` is bound by the miner axon process:
```bash
# Check local firewall status
sudo ufw status verbose

# Confirm the miner axon is listening on port 8191
ss -tulpn | grep 8191
```

### Verify Wallets Directory & Structure
Ensure only the specified testnet wallets are present:
```bash
ls -la ~/.bittensor/wallets/
# Expected: Only 'arctura_miner' and 'arctura_val' directories
```

### Verify Environment File Permissions
Confirm the environment configuration file restricts access to the owner only (permissions `0600` or `-rw-------`):
```bash
stat -c '%a %n' ~/.config/arctura-base-subnet.env
# Expected output: 600 /home/USER/.config/arctura-base-subnet.env
```

### Verify systemd User Services State
Check the active state, PID, start time, and restart counts for services:
```bash
# General status
systemctl --user status arctura-miner arctura-validator arctura-health.timer

# Detailed properties (verify ActiveState=active, SubState=running, NRestarts=0 or low)
systemctl --user show arctura-miner arctura-validator \
  --property=ActiveState,SubState,MainPID,ActiveEnterTimestamp,NRestarts
```

### Verify User Lingering
Verify that the user session is allowed to linger when offline:
```bash
loginctl show-user "$USER" --property=Linger
# Expected output: Linger=yes
```

### Audit First Cycle Logs
Inspect journal logs to verify successful boot, attestation, and scoring:
```bash
# Miner logs (Verify: "Arctura Base miner live" and mandate attestation)
journalctl --user -u arctura-miner -n 100 --no-pager

# Validator logs (Verify: "Arctura Base validator live" and mandate scoring UID 1)
journalctl --user -u arctura-validator -n 120 --no-pager

# Health timer logs (Verify: json output containing "ok": true)
journalctl --user -u arctura-health -n 50 --no-pager
```

---

## 🔄 Stop & Rollback Commands

If you need to halt operations, modify configuration, or dismantle the environment, use the following procedures.

### Halt and Disable Services
Stopping the services **invalidates** the current 48-hour continuous run window. Use these commands to stop and disable them:
```bash
systemctl --user stop arctura-validator arctura-miner arctura-health.timer
systemctl --user disable arctura-validator arctura-miner arctura-health.timer
```

### Full Rollback / Clean Uninstall
To completely remove the installation and configurations from the host:
```bash
# Stop and disable running services
systemctl --user stop arctura-validator arctura-miner arctura-health.timer
systemctl --user disable arctura-validator arctura-miner arctura-health.timer

# Clean up systemd user files and reload configuration
rm -f ~/.config/systemd/user/arctura-*.service ~/.config/systemd/user/arctura-*.timer
systemctl --user daemon-reload

# Clean up operator config and virtual environment
rm -f ~/.config/arctura-base-subnet.env
rm -rf ~/gbrain-work/arctura-base-subnet/.venv

# Disable user lingering
loginctl disable-linger "$USER"
```

---

## 🚫 Out of Scope: Mainnet & Token Transactions
This provisioning runbook is restricted purely to testnet operation and validation. **Do not execute any mainnet (Finney) registration, staking, or transfer operations on this host.** Subnet creation, staking, and key registration are managed separately and must not be run under the scope of this checklist.
