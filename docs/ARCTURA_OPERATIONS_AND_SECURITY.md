# Arctura Base Subnet: Treasury, Security & Pitch Operations Manual

**Prepared by:** Manus AI (World-Class Bittensor Expert)
**Parent Project:** [Arctura Network](https://arctura.network) | [arctura.network/base](https://arctura.network/base/)
**Repository:** [github.com/Arctura-Collective/arctura-base-subnet](https://github.com/Arctura-Collective/arctura-base-subnet)

---

## Executive Summary

This manual provides the complete operational, legal, and security blueprint for launching and maintaining the **Arctura Base Subnet** on Bittensor Finney Mainnet. It details treasury governance under Dynamic TAO (dTAO), AWS cloud infrastructure security hardening against DDoS and RPC exploitation, and includes a full investor and validator pitch deck in Markdown format.

---

## Part 1 — Treasury Governance & dTAO Management Framework

Operating a decentralized AI subnet requires disciplined treasury management to balance validator incentives, developer grants, and liquidity provisioning.

### 1. Treasury Operational Architecture
- **Multisig Custody:** The subnet owner coldkey and treasury reserves must be managed through a secure Gnosis Safe or hardware-backed multisig (utilizing Ledger devices via Crucible Wallet) [11]. No single private key should hold unilateral control over emission custody or owner permissions.
- **Emission Allocation Split (18% Subnet Pool):**
  - **Core Engineering & Maintenance (40% of Treasury):** Funds ongoing protocol upgrades, Pytest test suite expansion, and Base RPC integration reliability.
  - **Ecosystem & Validator Grants (30% of Treasury):** Subsidizes early validator syndicates and rewards top-performing miners who maintain >99.5% uptime.
  - **Liquidity & dTAO Provisioning (30% of Treasury):** Deployed into the subnet's alpha-TAO automated market maker (AMM) liquidity pools to stabilize slippage and encourage institutional delegation [2].

### 2. Legal & Compliance Guardrails
- **Open-Source Attribution:** All subnet code, agent adapters, and validation contracts are published under the permissive **Apache-2.0 License**, ensuring alignment with public goods funding (Optimism Retro Funding, Base Builder Grants).
- **Tax & Entity Structure:** Core development is structured around decentralized open-source contributors, with treasury reserves held in digital asset trusts or DAO legal wrappers to ensure regulatory clarity across multi-jurisdictional participation.

---

## Part 2 — AWS EC2 Security Hardening & DDoS Mitigation

Bittensor validators and miners operate in an adversarial peer-to-peer environment where exposure to unauthenticated RPC endpoints, DDoS floods, and hotkey exfiltration attempts represents a critical risk.

### 1. Network & Firewall Hardening (UFW & Security Groups)
Disable all default inbound ports on your AWS EC2 instances and restrict access strictly to necessary Bittensor ports:
```bash
# Enable UFW and set strict default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH only from a trusted administrative IP / VPN subnet
sudo ufw allow from YOUR_ADMIN_IP to any port 22 proto tcp

# Allow Bittensor P2P traffic
sudo ufw allow 30333/tcp

# Allow Miner Axon (Port 8091) and Validator Axon (Port 8092)
sudo ufw allow 8091/tcp
sudo ufw allow 8092/tcp

sudo ufw enable
```

### 2. DDoS Mitigation & Rate Limiting (Nginx Reverse Proxy)
To protect miner and validator axons from volumetric layer-7 HTTP/WebSocket floods, route external traffic through an Nginx reverse proxy configured with rate limiting:
```nginx
# /etc/nginx/sites-available/arctura-axon
limit_req_zone $binary_remote_addr zone=axon_limit:10m rate=10r/s;

server {
    listen 8091;
    server_name _;

    location / {
        limit_req zone=axon_limit burst=20 nodelay;
        proxy_pass http://127.0.0.1:9091; # Internal container port
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### 3. Hotkey Isolation & File Permissions
- **Coldkey/Hotkey Separation:** Never store coldkey mnemonics on cloud instances. Coldkeys must remain in offline hardware storage (Ledger via Crucible Wallet). Hotkeys stored on AWS must have strict file permissions:
  ```bash
  chmod 700 ~/.bittensor/wallets/*
  chmod 600 ~/.bittensor/wallets/*/hotkeys/*
  ```
- **Fail2ban Integration:** Install and configure `fail2ban` to automatically ban IP addresses exhibiting brute-force SSH or anomalous RPC request patterns.

---

## Part 3 — Investor & Validator Pitch Deck

*Below is the complete presentation deck formatted in Markdown, structured to convince institutional validators, angel investors, and ecosystem partners.*

---

# ARCTURA BASE SUBNET
### Bridging Base Blockchain Intelligence into Decentralized AI
*Presented by Arctura Core Team · August 2026*

---

## Slide 1: Executive Summary — The Intelligence Bridge
- **The Core Thesis:** Base is Coinbase’s L2 consumer engine (10M+ daily active addresses); Bittensor is the decentralized AI incentive layer. Currently, **zero Base subnets exist** on Bittensor.
- **The Solution:** Arctura (`arctura-base-subnet`) integrates Base state reads, event logs, and CDP AgentKit autonomous actions directly into Bittensor through verifiable Merkle attestation and Resonance BFT scoring.
- **The Milestone:** Fully verified locally on testnet (`505`) with 63/63 pytest unit tests passing. Ready for Finney Mainnet deployment.

---

## Slide 2: The Problem — Fragmented Onchain Intelligence
- **Data Silos:** Onchain state across L2s remains isolated from decentralized AI models, limiting autonomous agent capabilities.
- **Lack of Verification:** Existing oracle and indexing solutions rely on centralized trust assumptions rather than cryptographic proof.
- **The Opportunity:** Bittensor’s 128 subnet slots require high-utility real-world data commodities. Base is the fastest-growing financial and agentic surface in crypto.

---

## Slide 3: The Architecture — Six-Layer Signal Stack
- **L0 · Intent (`BaseSubnetSynapse`):** Validators issue programmatic mandates (block ranges, contract queries, agent actions).
- **L1 · Orchestration (`neurons/validator.py`):** Decentralized validation loop routing mandates and enforcing consensus.
- **L2 · Sandbox:** Deterministic RPC execution guaranteeing reproducible state outputs across independent nodes.
- **L3 · Cognitive Mesh (`arctura_base/agentkit.py`):** Miners execute onchain CDP AgentKit actions as native subnet mandate types.
- **L4 · Memory Fabric:** Local immutable indexing of Base contract state and transaction history.
- **L5 · Action Surface:** Axon MCP endpoints exposing Base reads as callable AI agent tools.

---

## Slide 4: Resonance BFT & Cryptographic Attestation
- **Verifiable Work:** Miners do not just answer queries; they return SHA-256 state hashes accompanied by cryptographic Merkle proofs anchored to live Base block hashes.
- **Four-Dimension Scoring:**
  - *Attestation Validity (40%):* Mathematical proof of correct execution.
  - *Execution Completeness (30%):* Trace covers all mandate steps.
  - *Response Latency (20%):* Timely delivery within deadline blocks.
  - *Confidence Calibration (10%):* Historical self-assessment accuracy.
- **Zero Tolerance:** Invalid proofs or stale block anchors receive **0.0 weight**, eliminating Sybil spam and fabricated data.

---

## Slide 5: Tokenomics & dTAO Incentive Model
- **Emission Distribution:**
  - **41% Miners:** Rewarded for high-fidelity Base intelligence and verifiable attestation.
  - **41% Validators:** Rewarded for consensus verification and reliable AWS uptime.
  - **18% Subnet Treasury:** Dedicated to core development, Base Builder rewards, and dTAO liquidity pools.
- **Immunity Period Strategy:** Systematic locking of treasury emissions into alpha-TAO AMM liquidity pools during the 4-month mainnet immunity period to stabilize token velocity.

---

## Slide 6: Go-To-Market & Ecosystem Funding
- **Dual-Stack Grant Stacking:**
  - *Base Builder Rewards:* Up to 2 ETH/week via weekly public build logs (`builderscore.xyz`) [8].
  - *Base Builder Grants:* 1–5 ETH retroactive funding for shipped prototypes (`paragraph.com`) [14].
  - *OP Retro Funding:* Public goods funding for Apache-2.0 open-source code and agent datasets [20].
- **Validator Syndicates:** Partnering with top-tier validators to provide initial stake weight and dTAO genesis liquidity.

---

## Slide 7: Roadmap to Mainnet Launch (August 2026)
- **Phase 0 (Complete):** Repository flattened, core protocol tested, local testnet `505` operational.
- **Phase 1 (Current):** AWS EC2 infrastructure hardened, security protocols implemented, syndicate outreach active.
- **Phase 2 (August 15):** Finney mainnet registration (`btcli subnet create`), hotkey recycling, and PM2/Docker process daemonization.
- **Phase 3 (Post-Launch):** Public announcement, Bitstarter liquidity activation, and decentralized miner onboarding.

---

## Slide 8: Join the Arctura Ecosystem
- **GitHub:** [github.com/Arctura-Collective/arctura-base-subnet](https://github.com/Arctura-Collective/arctura-base-subnet)
- **Portal:** [arctura.network/base](https://arctura.network/base/)
- **Call to Action:** We are actively onboarding founding validator partners and institutional syndicate backers ahead of our August 15 Finney registration window.

---

## References

- [Bittensor Documentation](https://www.bittensor.com/docs) [11]
- [Taostats Subnet Explorer](https://taostats.io/subnets) [2]
- [Base Documentation](https://docs.base.org) [284]
- [Arctura Network Portal](https://arctura.network) [11]
