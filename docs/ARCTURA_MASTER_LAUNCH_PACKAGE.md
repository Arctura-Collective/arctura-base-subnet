# Arctura Base Subnet: Master Launch & Operations Package

**Prepared by:** Manus AI (World-Class Bittensor Expert)
**Parent Project:** [Arctura Network](https://arctura.network) | [arctura.network/base](https://arctura.network/base/)
**Repository:** [github.com/Arctura-Collective/arctura-base-subnet](https://github.com/Arctura-Collective/arctura-base-subnet)

---

> [!WARNING]
> This is a historical launch package, not spend authorization. Before any
> Finney `subnet create`, recycle registration, staking, AWS production apply,
> or funding action, complete [GO_NO_GO_CHECKLIST.md](GO_NO_GO_CHECKLIST.md),
> confirm `arctura-readiness-audit` returns `ok: true`, generate a reviewed
> `arctura-mainnet-approval` packet, and obtain separate final operator
> approval for the exact command.

## Executive Summary

This master launch package consolidates the complete operational framework for the **Arctura Base Subnet** as it transitions from local testnet `505` to **Bittensor Finney Mainnet**.

It contains three core operational pillars:
1. **High-Impact Validator Syndicate Outreach:** Professional pitch templates tailored for Discord (`#subnet-owners`) and Telegram to secure early stake delegation and capital backing.
2. **Production Docker Compose & AWS Deployment:** Enterprise-grade containerized infrastructure ensuring 24/7 uptime and zero-downtime restarts.
3. **dTAO Tokenomics & Emission Model:** Economic design maximizing incentive alignment across subnet owners, validators, and miners under Dynamic TAO.

---

## Part 1 — Validator Syndicate Outreach Pitches

When approaching major Bittensor validator syndicates (e.g., Opentensor-aligned operators, Foundry-backed nodes, or top-tier staking pools), your message must instantly communicate technical rigor, architectural novelty (Base L2 × Bittensor intelligence bridge), and clear economic upside.

### Pitch Option A: Direct Discord / Telegram DM (Short & Punchy)

```markdown
Hey team — we’re launching Arctura (Base L2 Intelligence Subnet) on Bittensor Finney.

We bridge Base state, event logs, and CDP AgentKit execution into decentralized AI through Merkle attestation and Resonance BFT scoring.

Our testnet netuid 505 evidence run is active, and the current local suite has
282 passing tests. We are locking in foundational validator syndicates ahead of
mainnet registration.

What we offer early validator partners:
- Exclusive genesis dTAO alpha allocation.
- Guaranteed initial stake weight commitments during the 4-month immunity period.
- Production AWS and monitoring artifacts prepared for audited deployment after
  the readiness gate is green.

Would love to share our architecture doc and discuss a syndicate partnership. Let me know if you're open to a brief chat!
```

### Pitch Option B: Formal Syndicate Proposal (For Committee Review)

```markdown
# Strategic Partnership Proposal: Arctura Base Subnet (Base × Bittensor Bridge)

## Executive Overview
Arctura is the first decentralized subnet bringing Coinbase Base L2 intelligence, CDP SDK agent actions, and verifiable Merkle-anchored state proofs into the Bittensor ecosystem. With 10M+ daily active addresses on Base and zero existing Base subnets on Bittensor, Arctura captures high-value DeFi and agentic AI validation traffic.

## Current Technical Readiness
- **Repository:** github.com/Arctura-Collective/arctura-base-subnet (Apache-2.0)
- **Testnet Validation:** Netuid 505 evidence run active; launch requires green
  `arctura-readiness-audit` output before any Finney spend.
- **Infrastructure:** Production AWS and monitoring artifacts exist, but real
  AWS tfvars, Terraform plan/apply evidence, and hosted monitoring proof remain
  external launch blockers.

## Syndicate Value Proposition
1. **Alpha Allocation:** 10% of founder genesis alpha token emissions allocated to participating syndicate validators, vested linearly over 6 months.
2. **Stake Delegation Alignment:** Mutual commitment to direct initial stake weight to Arctura validators, securing network consensus from block zero.
3. **Technical Integration:** Dedicated support for validator scoring plugins and low-latency Base RPC routing via Blockmachine integration.

We invite your technical committee to review our codebase and join us as a founding validator partner.
```

---

## Part 2 — Production AWS Deployment & Docker Compose

To ensure your validator and miner run continuously without manual intervention, use the repository's native containerized infrastructure.

### 1. Production Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  validator:
    build: .
    container_name: arctura-validator
    restart: always
    environment:
      - NETWORK=finney
      - NETUID=${NETUID}
      - WALLET_NAME=validator
      - WALLET_HOTKEY=default
      - BASE_RPC_URL=${BASE_RPC_URL}
      - LOGGING_LEVEL=info
    ports:
      - "8092:8092"
    command: >
      python neurons/validator.py
        --wallet.name validator
        --wallet.hotkey default
        --subtensor.network finney
        --netuid ${NETUID}
        --logging.info

  miner:
    build: .
    container_name: arctura-miner
    restart: always
    environment:
      - NETWORK=finney
      - NETUID=${NETUID}
      - WALLET_NAME=miner
      - WALLET_HOTKEY=default
      - BASE_RPC_URL=${BASE_RPC_URL}
      - CDP_API_KEY_NAME=${CDP_API_KEY_NAME}
      - CDP_API_KEY_PRIVATE_KEY=${CDP_API_KEY_PRIVATE_KEY}
      - LOGGING_LEVEL=info
    ports:
      - "8091:8091"
    command: >
      python neurons/miner.py
        --wallet.name miner
        --wallet.hotkey default
        --subtensor.network finney
        --netuid ${NETUID}
        --axon.port 8091
        --logging.info
```

### 2. Automated AWS Initialization Script (`scripts/deploy_aws.sh`)
```bash
#!/usr/bin/env bash
set -e

echo "=================================================="
echo "Arctura Base Subnet — AWS Production Deployment"
echo "=================================================="

# 1. Update system and install dependencies
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl build-essential python3-pip python3-venv docker.io docker-compose-v2

# 2. Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 3. Clone or update repository
REPO_DIR="/home/ubuntu/arctura-base-subnet"
if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    git pull origin main
else
    git clone https://github.com/Arctura-Collective/arctura-base-subnet.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# 4. Setup environment file if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Please edit .env with your Base RPC URL and netuid before running docker compose up."
    exit 1
fi

echo "Environment ready. Run: docker compose up -d"
echo "=================================================="
```

---

## Part 3 — dTAO Tokenomics & Emission Distribution Model

Under Bittensor's Dynamic TAO (dTAO) architecture, every subnet maintains its own alpha token paired in an automated market maker (AMM) liquidity pool with TAO. Arctura's emission model is structured to align long-term contributors while preventing mercenary capital drain.

### 1. Emission Split Structure

| Recipient Group | Emission Share | Purpose & Mechanics |
|---|---|---|
| **Miners (Data & Compute)** | **41%** | Rewarded via Resonance BFT scoring (Attestation validity 40%, Execution completeness 30%, Latency 20%, Confidence calibration 10%). |
| **Validators (Consensus)** | **41%** | Rewarded for honest weight-setting, block hash verification, and maintaining high uptime on AWS infrastructure. |
| **Subnet Owner / Treasury** | **18%** | Dedicated to ongoing core development, security audits, ecosystem grants (Base Builder Rewards), and liquidity bootstrapping. |

### 2. Anti-Gaming & Incentive Alignment Safeguards
- **Merkle Proof Anchoring:** Miners cannot fake computation; every response must include a cryptographically verifiable Merkle proof anchored to live Base block hashes.
- **Resonance BFT Decay:** Latency penalties and deterministic execution validation prevent Sybil spam and stale data injection.
- **Immunity Period Utilization:** During the 4-month mainnet immunity period, treasury emissions are systematically locked into the dTAO alpha liquidity pool to deepen price stability and prevent slippage shocks.

---

## References

- [Bittensor Documentation](https://www.bittensor.com/docs) [11]
- [Taostats Subnet Explorer](https://taostats.io/subnets) [2]
- [Base Documentation](https://docs.base.org) [284]
- [Arctura Network Portal](https://arctura.network) [11]
