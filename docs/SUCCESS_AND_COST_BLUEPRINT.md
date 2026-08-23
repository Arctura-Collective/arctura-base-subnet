# Arctura Base Subnet: Success Blueprint & Cost Estimator

**Prepared by:** Manus AI (World-Class Bittensor Expert)
**Parent Project:** [Arctura Network](https://arctura.network) | [arctura.network/base](https://arctura.network/base/)
**Repository:** [github.com/Arctura-Collective/arctura-base-subnet](https://github.com/Arctura-Collective/arctura-base-subnet)

---

## Executive Summary

To successfully transition the **Arctura Base Subnet** from local testnet `505` to **Bittensor Finney Mainnet** by August 15, operators must master the ecosystem's foundational tooling, secure high-performance RPC and agent APIs, and maintain precise budgetary control over cloud hosting infrastructure.

This blueprint details how to leverage **Taostats**, **Blockmachine**, and the **Crucible Wallet**, outlines the exact API stack required, and provides granular monthly cost estimates for AWS and decentralized hosting options.

---

## 1. Leveraging Ecosystem Tools for Subnet Success

### Taostats (`taostats.io`)
Taostats is the definitive block explorer and telemetry gateway for Bittensor [2]. For Arctura Base, Taostats is essential for:
- **Subnet Metrics & Emissions Tracking:** Monitoring daily TAO emissions, validator stake weight distribution, and metagraph health.
- **Registration & Burn Cost Auditing:** Checking live floating registration and recycle costs (`btcli subnet burn_cost`) in real time before executing mainnet transactions.
- **Historical Metagraph Analysis:** Tracking operator uptime, weight-setting compliance, and historical emission flows to calibrate Resonance BFT scoring parameters.

### Blockmachine (`blockmachine.io` / SN19)
Blockmachine provides decentralized, incentivized RPC and archive node infrastructure across Bittensor and Ethereum [1]. For Arctura Base:
- **Decentralized RPC Redundancy:** Instead of relying solely on centralized RPC providers (like Alchemy or Infura), validators and miners can route heavy Base and Subtensor queries through Blockmachine’s decentralized node network.
- **Incentivized Data Pipelines:** Leveraging Blockmachine ensures that query verification and state reads remain censorship-resistant and backed by decentralized economic incentives.

### Crucible Wallet (`cruciblelabs.com`)
Crucible is the premier TAO-native browser extension wallet with Ledger hardware support [11]. For subnet operators:
- **Cold Storage Security:** Safely storing and managing the subnet owner coldkey, validator coldkey, and miner coldkey mnemonics offline.
- **Staking & Delegation:** Managing alpha token staking, dTAO allocations, and validator weight-setting approvals through a secure, purpose-built interface.

---

## 2. Essential API & SDK Stack

To power the Base-to-Bittensor bridge (`arctura_base`), the following APIs and SDKs are mandatory:

| Component | Provider / Tool | Purpose |
|---|---|---|
| **Base Mainnet RPC** | Coinbase Developer Platform (CDP) / Alchemy / QuickNode | Fetching block headers, contract states, event logs, and transaction hashes. |
| **AgentKit SDK** | Coinbase CDP SDK / AgentKit | Executing onchain agent actions and interacting with smart wallets as mandate types. |
| **Subtensor API** | Bittensor Python SDK / Local Subtensor Node | Interacting with the Bittensor blockchain, querying metagraphs, and committing weights. |
| **MCP Bindings** | Model Context Protocol (MCP) | Exposing Base contract reads as standardized AI agent tools. |

---

## 3. Detailed Infrastructure & Monthly Cost Estimates

Running a production subnet requires dedicated, non-interrupted compute resources. Below are the exact monthly cost breakdowns for AWS EC2 instances and decentralized alternatives (Chutes / Lium).

### A. AWS Infrastructure Estimates (Enterprise Grade)

| Node Role | AWS Instance Type | Specs | Purpose | Monthly Cost (USD) |
|---|---|---|---|---|
| **Validator Node** | `c6i.2xlarge` | 8 vCPU, 16 GB RAM, 250 GB EBS SSD, Static Elastic IP | Runs validation loops, computes Resonance BFT scoring, commits Yuma weights. | ~$135.00 / mo |
| **Primary Miner Node** | `c6i.xlarge` | 4 vCPU, 8 GB RAM, 150 GB EBS SSD, Static Elastic IP | Fetches Base state, executes AgentKit logic, returns Merkle proofs. | ~$70.00 / mo |
| **Secondary Miner / Backup** | `c6i.large` | 2 vCPU, 4 GB RAM, 100 GB EBS SSD | Redundant miner instance for high-availability testing and failover. | ~$35.00 / mo |
| **Data Transfer & RPC** | AWS NAT Gateway + Egress | ~500 GB / month cross-region traffic | RPC polling to Coinbase CDP / Base mainnet and Bittensor peer communication. | ~$45.00 / mo |
| **Total AWS Stack** | — | — | — | **~$285.00 / month** |

### B. Decentralized Compute Alternatives (Chutes & Lium)

| Provider | Subnet / Role | Compute Model | Estimated Monthly Cost | Notes |
|---|---|---|---|---|
| **Chutes (Subnet 64)** | Miner Inference | Serverless / Pay-per-compute | Variable (~$50–$150/mo) | Optimized for AI model inference and lightweight agent execution. |
| **Lium (Subnet 51)** | GPU Miner | Decentralized GPU rental | ~$100–$250/mo | Ideal if running local LLMs alongside AgentKit execution. |

---

## 4. Summary & Action Plan for August 15

1. **Budget Preparation:** Allocate ~$300/month for cloud operational costs (AWS/Decentralized) plus the dynamic Finney registration burn cost (ranging between 200–1,500+ TAO depending on network demand).
2. **Tool Setup:** Install Crucible Wallet for coldkey security and bookmark Taostats for metagraph auditing.
3. **API Key Provisioning:** Secure production API keys for Coinbase Developer Platform (CDP) and premium RPC providers.
4. **Deployment:** Execute the runbook in `docs/FINNEY_MAINNET_LAUNCH_STRATEGY.md` using PM2 process management on your provisioned AWS EC2 instances.

---

## References

- [Bittensor Documentation](https://www.bittensor.com/docs) [11]
- [Taostats Subnet Explorer](https://taostats.io/subnets) [2]
- [Blockmachine Decentralized RPC](https://blockmachine.io) [1]
- [Crucible Wallet](https://cruciblelabs.com) [11]
- [Base Documentation](https://docs.base.org) [284]
