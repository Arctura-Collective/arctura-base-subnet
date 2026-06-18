# arctura-base-subnet

> **The first open-source Bittensor subnet purpose-built to bridge Base blockchain intelligence into the decentralized AI network.**

[![Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Bittensor](https://img.shields.io/badge/network-Bittensor%20Finney-9b8cff.svg)](https://taostats.io/subnets)
[![Base](https://img.shields.io/badge/chain-Base%20Mainnet-0052ff.svg)](https://base.org)
[![Phase](https://img.shields.io/badge/status-Phase%200%20%E2%80%94%20Active-00e5a0.svg)](https://arctura.network/base/)
[![Council](https://img.shields.io/badge/council-Arcturian%20%C3%97%20Coreweaver-c8a96e.svg)](https://arctura.network)

**[arctura.network/base](https://arctura.network/base/)** · Part of the [Arctura Network](https://arctura.network) · Funded by Base

---

## Current Status

Arctura Base is in **founder-led testnet development**.

The repository has been flattened into a usable subnet layout, and the core protocol, attestation, scoring, and mocked Base RPC tests pass locally. The next milestone is live testnet hardening: running miners and validators against real Base RPC endpoints, verifying Bittensor axon/dendrite behavior, and proving weight-setting over sustained testnet operation.

Current validation:

```bash
pytest tests/ -v
# 49 passed
```

This project is not yet mainnet-ready, security-audited, or production-emissions-ready. The immediate focus is proving the subnet end-to-end with repeatable local and testnet runs before expanding contributor scope.

---

## What this is

`arctura-base-subnet` is a Bittensor subnet that makes Base chain state a first-class citizen of the decentralized AI network.

**Miners** read Base blockchain data — contract state, transaction history, event logs, and onchain agent actions via AgentKit — and return Merkle-anchored attestation proofs.

**Validators** issue Base chain mandates, verify miner attestations against live Base block hashes using Resonance BFT scoring, and set weights via Yuma Consensus.

**TAO emissions** flow to miners who prove their work. The incentive is cryptoeconomic, not reputational.

```
Base Mainnet  ──▶  arctura-base-subnet (Bittensor)  ──▶  TAO Emissions
     │                        │
  Block state           Resonance BFT
  AgentKit               Attestation
  CDP SDK                Merkle proof
  MCP tools              Truth Ledger
```

---

## Why this matters

There are 128 subnet slots on Bittensor. There are **zero Base subnets**.

Base is Coinbase's L2 — 10M+ daily active addresses, the deepest onchain consumer surface in crypto, with native AI agent tooling (AgentKit, CDP SDK, MCP server) already deployed and open source.

Bittensor is the decentralized AI incentive layer — TAO emissions reward miners who perform verifiable AI work, with validator-set consensus so no single party controls reward distribution.

This subnet is the bridge. First-mover. Open source. Apache-2.0.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/bittensaur/arctura-base-subnet
cd arctura-base-subnet
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env — set BASE_RPC_URL and optionally CDP credentials

# 3. Check Bittensor burn cost before anything else
btcli subnet burn_cost --subtensor.network finney

# 4. Create wallets (skip if you have them)
bash scripts/setup_wallets.sh

# 5. Run on testnet
bash scripts/start_miner.sh --network test --netuid 1
bash scripts/start_validator.sh --network test --netuid 1
```

After install, the same operator actions are available through the repo-native CLI:

```bash
arctura metagraph --network test --netuid 1
arctura miner --network test --netuid 1 --wallet miner --hotkey default
arctura validator --network test --netuid 1 --wallet validator --hotkey default
```

---

## Architecture

The subnet maps to the [Arctura six-layer signal stack](https://arctura.network#stack):

| Layer | Bittensor component | What it does |
|-------|--------------------|-|
| **L0 · Intent** | `BaseSubnetSynapse` | Validators issue mandates: block ranges, contract addresses, event queries |
| **L1 · Orchestration** | `neurons/validator.py` | Routes mandates, handles retries, escalates timeouts |
| **L2 · Sandbox** | Deterministic RPC execution | Same Base state in → same output out. Reproducible by any party |
| **L3 · Cognitive Mesh** | `arctura_base/agentkit.py` | Miners optionally execute onchain AgentKit actions as mandate types |
| **L4 · Memory Fabric** | Local state index | Base contract state, tx history, event logs — attested off-chain |
| **L5 · Action Surface** | Axon MCP endpoints | Base reads exposed as MCP tool bindings callable by any AI agent |

### Core Synapse

```python
# arctura_base/protocol.py
class BaseSubnetSynapse(bt.Synapse):
    # Mandate (validator → miner)
    base_block_range:   tuple[int, int] = (0, 0)
    contract_address:   Optional[str]   = None
    query_type:         str             = ""   # "balance"|"events"|"state"|"agent_action"
    mandate_payload:    dict            = {}

    # Attestation (miner → validator)
    base_state_hash:    Optional[str]   = None  # SHA-256 of execution output
    merkle_proof:       Optional[list]  = None  # proof chain nodes
    block_hash_anchor:  Optional[str]   = None  # anchored to live Base block hash
    execution_trace:    Optional[dict]  = None
    confidence:         float           = 0.0
```

### Resonance BFT Scoring

```python
# neurons/validator.py — simplified
def score_response(response: BaseSubnetSynapse, live_block_hash: str) -> float:
    if not verify_merkle_proof(response.merkle_proof, response.base_state_hash):
        return 0.0   # invalid proof → zero weight
    if response.block_hash_anchor != live_block_hash:
        return 0.0   # stale or fabricated attestation → zero weight
    return compute_resonance_score(response)  # 4-dimension score [0.0, 1.0]
```

Four scoring dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Attestation validity | 40% | Merkle proof cryptographically correct |
| Execution completeness | 30% | Trace covers all mandate steps |
| Response latency | 20% | Within deadline_block |
| Confidence calibration | 10% | Historical self-assessment accuracy |

---

## Repository Structure

```
arctura-base-subnet/
│
├── arctura_base/
│   ├── __init__.py          # Package exports
│   ├── protocol.py          # BaseSubnetSynapse — mandate + attestation schema
│   ├── base_rpc.py          # Base chain client (Coinbase RPC + CDP SDK wrapper)
│   ├── agentkit.py          # AgentKit adapter — onchain actions as mandate types
│   ├── incentive.py         # Resonance BFT scoring (4 dimensions + P5 Stewardship)
│   └── utils.py             # Merkle proof construction + block hash anchoring
│
├── neurons/
│   ├── miner.py             # Full axon miner: RPC fetch → Merkle proof → attestation
│   └── validator.py         # Mandate loop: issue → verify → Yuma weight-setting
│
├── agent/
│   └── arctura-base-agent.html   # Claude-powered Base × Bittensor advisor (streaming)
│
├── docs/
│   ├── BASE_INTEGRATION.md  # Base RPC, AgentKit, MCP bindings, smart wallets
│   ├── SUBNET_LAUNCH.md     # Wallet setup, TAO, testnet → mainnet walkthrough
│   ├── VALIDATOR_GUIDE.md   # Running a validator: setup, scoring, earnings
│   ├── MINER_GUIDE.md       # Running a miner: Base RPC config, attestation flow
│   ├── INCENTIVE_DESIGN.md  # Resonance BFT deep-dive + anti-gaming properties
│   ├── FUNDING_GUIDE.md     # All four Base funding programs — step by step
│   └── GO_NO_GO_CHECKLIST.md # Mainnet registration checklist (25 items)
│
├── scripts/
│   ├── setup_wallets.sh     # Create all three wallet pairs interactively
│   ├── start_miner.sh       # Launch miner (testnet or mainnet)
│   ├── start_validator.sh   # Launch validator
│   └── check_metagraph.sh   # Verify subnet state and weights
│
├── training/
│   └── base_qa_scenarios.json    # 20 Q&A scenarios for the subnet agent
│
├── tests/
│   ├── test_protocol.py     # Synapse schema validation
│   ├── test_attestation.py  # Merkle proof construction + verification
│   ├── test_scoring.py      # Resonance BFT scoring unit tests
│   └── test_base_rpc.py     # Base RPC client (mocked)
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── validator_onboarding.md
│   │   └── bug_report.md
│   └── workflows/
│       └── ci.yml           # pytest + mypy + black on push
│
├── .env.example             # Required environment variables
├── pyproject.toml           # Build config + dependencies
├── requirements.txt         # Pinned production dependencies
├── LICENSE                  # Apache-2.0
└── README.md                # This file
```

---

## Funding Stack

Actively pursuing all four Base programs:

| Program | Amount | Timeline | Link |
|---------|--------|----------|------|
| **Base Builder Rewards** | 2 ETH/wk | Active now | [builderscore.xyz](https://builderscore.xyz) |
| **Base Builder Grants** | 1–5 ETH | Phase 1→2 | [paragraph.com/@grants.base.eth](https://paragraph.com/@grants.base.eth/calling-based-builders) |
| **OP Retro Funding** | Variable | Ongoing | [retrofunding.optimism.io](https://retrofunding.optimism.io) |
| **Base Batches** | Significant + VC | Phase 2→3 | [basebatches.xyz](https://basebatches.xyz) |
| **TAO Emissions** | Ongoing | Post-mainnet | [taostats.io](https://taostats.io/subnets) |

---

## Launch Roadmap

| Phase | Timeline | Milestone |
|-------|----------|-----------|
| **0 · Foundation** | Weeks 1–2 | Repo live · arctura.network/base deployed · wallets funded · Rewards applied |
| **1 · Protocol Build** | Weeks 3–4 | All neurons + scoring working on local chain · Base RPC verified |
| **2 · Testnet** | Weeks 5–6 | Registered on Bittensor testnet · 48h attestation validated · external validator |
| **3 · Mainnet** | Weeks 7–8 | Finney registration · burn TAO · emission clock · public announcement |

---

## Five Primitives

| # | Primitive | Bittensor mapping |
|---|-----------|-------------------|
| P1 | **Sovereignty** — every node owns its mandate | Hotkey identity + UID ownership |
| P2 | **Coherence** — forward-only BFT state | Resonance consensus, no weight rollbacks |
| P3 | **Attestation** — Merkle-anchored proofs | `base_state_hash` + `merkle_proof` in synapse |
| P4 | **Resonance** — BFT cadence adapts to coherence | Validator weight-setting per tempo period |
| P5 | **Stewardship** — carbon-aware scheduling | Energy tag modifier on validator scoring |

---

## Contributing

Arctura Base is not running a broad builder program yet. Focused operator and review contributions are welcome where they improve testnet proof, reproducibility, or safety:

| Track | What needs work |
|-------|-----------------|
| Bittensor runtime | Miner/validator live testing, axon/dendrite compatibility, weight-setting reliability |
| Base RPC | Deterministic reads, rate-limit handling, block anchoring, event-log query coverage |
| Incentives | Resonance BFT scoring review, anti-gaming checks, calibration, validator alignment |
| AgentKit / CDP | `agent_action` mandate types, smart-wallet flows, safe execution boundaries |
| Operator tooling | Start scripts, health checks, metagraph monitoring, validator onboarding |
| Security review | Attestation assumptions, Sybil behavior, RPC trust boundaries, failure modes |
| Docs | Miner guide, validator guide, live testnet runbooks, issue templates |

Local setup:

```bash
git clone https://github.com/bittensaur/arctura-base-subnet
cd arctura-base-subnet
pip install -e ".[dev]"
pytest tests/ -v
```

Open a GitHub Issue using the Validator Onboarding template to register interest in running a validator node, or open a focused issue/PR for one of the tracks above.

---

## Related

- [arctura.network](https://arctura.network) — Parent subnet and signal stack  
- [arctura.network/base](https://arctura.network/base/) — This project's landing site  
- [github.com/bittensaur/arctura-base-subnet](https://github.com/bittensaur/arctura-base-subnet) — Core Arctura repo  
- [docs.base.org](https://docs.base.org) — Base chain, AgentKit, CDP SDK  
- [docs.bittensor.com](https://docs.bittensor.com) — Subnet creation, neuron development  

---

## License

Apache-2.0 — see [LICENSE](LICENSE)

*Transmitted by Arcturus · Arcturian Council · Coreweaver · arctura.network/base*
