# Arctura Base Subnet: Finney Mainnet Launch Strategy & Operational Runbook

**Prepared by:** Manus AI (World-Class Bittensor Expert)
**Target Execution Date:** August 15, 2026 (anticipating plan upgrade)
**Parent Project:** [Arctura Network](https://arctura.network) | [arctura.network/base](https://arctura.network/base/)
**Repository:** [github.com/Arctura-Collective/arctura-base-subnet](https://github.com/Arctura-Collective/arctura-base-subnet)

---

## Executive Summary

The **Arctura Base Subnet** (`arctura-base-subnet`) bridges Base blockchain intelligence (state reads, transaction history, event logs, and AgentKit autonomous actions) into the Bittensor decentralized AI network through cryptographic Merkle attestation and Resonance BFT scoring.

Currently operating successfully as a local testnet deployment on netuid `505`, the subnet is structured for migration to **Bittensor Finney Mainnet**. Because local workstation hosting is constrained, this strategy defines a robust, cost-effective cloud architecture utilizing AWS and decentralized infrastructure providers (such as Chutes and Lium) to run validators and miners securely, handle dynamic TAO (dTAO) registration economics, and ensure 24/7 uptime prior to the August 15 go-live window.

---

## 1. From Testnet (Netuid 505) to Finney Mainnet

Moving from local testnet `505` to Finney Mainnet requires understanding key structural differences between Bittensor test environments and production mainnet economics:

| Parameter | Local Testnet (`505`) | Finney Mainnet |
|---|---|---|
| **Subnet Registration** | Local CLI (`btcli subnet create`) | Dynamic TAO (dTAO) slot creation via burn or auction |
| **Token Economic Stakes** | Free/Mock test TAO | Real TAO (subject to live burn cost, e.g., 200–1,500+ TAO) |
| **Consensus & Weights** | Local Yuma Consensus simulation | Production Yuma Consensus across global validators |
| **Immunity Period** | None / Instant | 4-month immunity period post-registration |
| **Emissions Activation** | Immediate local feedback | 7 days post-registration |

### Prerequisites for Mainnet Go-Live
1. **48-Hour Continuous Testnet Run:** Prove zero uncaught exceptions, stable Merkle proofs, and valid weight-setting on testnet.
2. **Burn Cost Verification:** Run `btcli subnet burn_cost --subtensor.network finney` immediately prior to registration.
3. **Capital Reserve:** Ensure the owner coldkey holds the current dynamic burn cost plus a 20% buffer, plus sufficient TAO for miner and validator `recycle_register` operations.

---

## 2. Infrastructure & Hosting Architecture: AWS vs. Decentralized Compute

To operate a production-grade subnet on Finney, your infrastructure must guarantee low latency, static public IP addresses, and high availability (99.9% uptime for validators, 99.0% for miners).

### Recommended Hybrid Topology

```
                  ┌────────────────────────────────────────┐
                  │          Bittensor Finney Chain        │
                  └───────────┬────────────────┬───────────┘
                              │                │
              ┌───────────────┘                └───────────────┐
              ▼                                                ▼
   ┌───────────────────────┐                        ┌───────────────────────┐
   │ AWS EC2 Validator     │                        │ Decentralized Miner   │
   │ (c6i.2xlarge / 8 vCPU)│                        │ (Chutes / Lium / AWS) │
   │ - Static IP (EIP)     │                        │ - Base RPC Connector  │
   │ - Port 8092 (Axon)    │                        │ - Port 8091 (Axon)    │
   │ - Resonance BFT Engine│                        │ - Merkle Attestation  │
   └───────────────────────┘                        └───────────────────────┘
```

### Hosting Options Compared

| Platform | Role | Pros | Cons | Recommendation |
|---|---|---|---|---|
| **AWS (Amazon Web Services)** | Validator & Primary Miner | Enterprise reliability, dedicated Elastic IPs, predictable networking, seamless security groups | Higher hourly cost, centralized infrastructure | **Mandatory for Validators** (ensures uptime and weight-setting reliability). |
| **Chutes (Subnet 64)** | Miner / Inference | Native Bittensor-aligned decentralized serverless execution, GPU optimized | Emerging ecosystem, custom deployment tooling | **Highly recommended for Miner AI workloads** requiring scalable compute. |
| **Lium (Subnet 51)** | Miner / GPU Compute | Decentralized GPU rental marketplace, crypto-native infrastructure | Spot availability fluctuations | **Ideal for secondary miner nodes** seeking decentralized redundancy. |

---

## 3. Step-by-Step Mainnet Launch Runbook (August 15 Target)

### Phase A — Infrastructure Provisioning (AWS)
1. **Launch Validator EC2 Instance:**
   - Instance Type: `c6i.2xlarge` (8 vCPU, 16 GB RAM) running Ubuntu 24.04 LTS.
   - Storage: 250 GB NVMe SSD (for subtensor light client / local caching).
   - Security Group: Open inbound TCP ports `22` (SSH), `8092` (Validator Axon), and allow outbound Bittensor P2P ports (`30333`).
   - Elastic IP (EIP): Attach a static public IP.
2. **Launch Miner EC2 Instance (or Chutes/Lium node):**
   - Instance Type: `c6i.xlarge` (4 vCPU, 8 GB RAM) or GPU instance if running heavy AgentKit local LLM inference.
   - Security Group: Open inbound TCP ports `22` and `8091` (Miner Axon).

### Phase B — Environment & Wallet Setup
SSH into your cloud instances and initialize the repository:
```bash
git clone https://github.com/Arctura-Collective/arctura-base-subnet.git
cd arctura-base-subnet
pip install -e ".[dev]"
cp .env.example .env
```
Populate `.env` with your secure Base RPC endpoint (e.g., Coinbase Developer Platform / Alchemy / QuickNode) and CDP API keys.

### Phase C — Wallets & Registration
```bash
# 1. Check live mainnet burn cost
btcli subnet burn_cost --subtensor.network finney

# 2. Setup production wallets (store coldkey mnemonics offline in 2 secure locations)
bash scripts/setup_wallets.sh finney

# 3. Create subnet on Finney (Owner coldkey)
btcli subnet create --wallet.name owner --subtensor.network finney
# RECORD YOUR NETUID FROM OUTPUT

# 4. Register validator and miner hotkeys
btcli subnet recycle_register --netuid N --wallet.name validator --subtensor.network finney
btcli subnet recycle_register --netuid N --wallet.name miner --subtensor.network finney
```

### Phase D — Process Management with PM2
Ensure both neurons auto-restart upon system reboots:
```bash
sudo npm install -g pm2

# Start Miner
pm2 start scripts/start_miner.sh --name "arctura-miner" -- --network finney --netuid N

# Start Validator
pm2 start scripts/start_validator.sh --name "arctura-validator" -- --network finney --netuid N

pm2 save
pm2 startup
```

---

## 4. Monitoring, Security, and Go-Live Safeguards

1. **Metagraph Verification:** Regularly run `arctura metagraph --network finney --netuid N` or `bash scripts/check_metagraph.sh finney N` to confirm stake distribution and weight assignments.
2. **Axon Reachability:** Ensure external validators can reach your miner axon on port `8091`. Use `btcli stake` and `btcli overview` to audit validator inclusion.
3. **Emergency Stop Plan:** In the event of RPC rate-limiting or unexpected validation anomalies, stop processes immediately via `pm2 stop all` and inspect logs (`pm2 logs`).

---

## References

- [Bittensor Documentation](https://www.bittensor.com/docs) [11]
- [Taostats Subnet Explorer](https://taostats.io/subnets) [2]
- [Base Documentation](https://docs.base.org) [284]
- [Arctura Network Portal](https://arctura.network) [11]
