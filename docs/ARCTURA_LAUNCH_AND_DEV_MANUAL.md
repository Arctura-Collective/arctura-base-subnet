# Arctura Base Subnet: Pre-Flight, Deck Hosting & Autonomous GitHub Developer Workflow

**Prepared by:** Manus AI (World-Class Bittensor Expert)
**Parent Project:** [Arctura Network](https://arctura.network) | [arctura.network/base](https://arctura.network/base/)
**Repositories:** [github.com/Arctura-Collective/arctura-base-subnet](https://github.com/Arctura-Collective/arctura-base-subnet) | [virtualmase/portfolio](https://github.com/virtualmase/portfolio)

---

## Part 1 — Final Finney Pre-Flight Checklist & Environment Variables

Before executing `btcli subnet create` on Bittensor Finney Mainnet, verify every item on this checklist. Do not execute under pressure without review.

### 1. Financial & Wallet Verification
- [ ] **Live Burn Cost Checked:** Run `btcli subnet burn_cost --subtensor.network finney` within 30 minutes of registration [9].
- [ ] **Owner Balance Funded:** Owner coldkey holds `burn_cost + 20% safety buffer` in live TAO [15].
- [ ] **Hotkey Wallets Created:** Validator and miner hotkeys initialized (`scripts/setup_wallets.sh finney`).
- [ ] **Coldkey Security:** Mnemonics stored offline in at least two separate physical locations.

### 2. Environment Variable Verification (`.env`)
Ensure your production `.env` file contains zero placeholder values:
```env
NETWORK=finney
NETUID=52                          # Replace with your live netuid upon creation
BASE_RPC_URL=https://mainnet.base.org   # Or your premium CDP/Alchemy RPC URL
CDP_API_KEY_NAME=your_verified_key_name
CDP_API_KEY_PRIVATE_KEY=your_verified_private_key
LOGGING_LEVEL=info
```

### 3. Infrastructure & Network Verification
- [ ] **AWS Security Groups Open:** Ports `22` (SSH), `8091` (Miner Axon), `8092` (Validator Axon), and outbound `30333` (P2P) verified.
- [ ] **Static Elastic IPs Attached:** EC2 instances assigned fixed public IPs.
- [ ] **Testnet Run Complete:** 48+ hours of continuous testnet (`505`) execution with zero uncaught exceptions and passing unit tests (`pytest tests/ -v`).

---

## Part 2 — Hosting the Reveal.js Pitch Deck (`docs/pitch_deck.html`)

You can host your pitch deck (`docs/pitch_deck.html`) publicly in minutes using GitHub Pages or Vercel.

### Option A: GitHub Pages (Recommended & Free)
1. Move or copy `docs/pitch_deck.html` to `index.html` in the root of your repository (or configure GitHub Pages to serve from the `/docs` folder on main branch).
2. Go to your GitHub repository → **Settings** → **Pages**.
3. Under **Build and deployment**, set Source to **Deploy from a branch** (`main` / root or `/docs`).
4. Click **Save**. Your presentation will be live instantly at `https://bittensaur.github.io/arctura-base-subnet/pitch_deck.html`.

### Option B: Vercel (Lightning Fast)
1. Install Vercel CLI or connect your GitHub repository directly at [vercel.com](https://vercel.com).
2. Import `Arctura-Collective/arctura-base-subnet`.
3. Set root directory to root or `/docs`. Click **Deploy**. Vercel will assign a production URL (`arctura-base-subnet.vercel.app`) with automatic SSL.

---

## Part 3 — Complete Speaker Script & Talking Points

*Verbatim speaker notes for presenting `docs/pitch_deck.html`.*

- **Slide 1 (Title):** "Welcome to Arctura Base Subnet. We are bridging Coinbase Base L2 intelligence into decentralized AI."
- **Slide 2 (The Intelligence Bridge):** "Base has over 10 million daily active addresses, making it the premier consumer L2. Yet, there are zero Base subnets on Bittensor. Arctura captures this untapped market."
- **Slide 3 (Six-Layer Signal Stack):** "Our architecture spans from L0 validator mandates to L3 AgentKit autonomous execution and L5 MCP tool bindings, creating a fully deterministic, reproducible intelligence loop."
- **Slide 4 (Verifiable Resonance BFT):** "Miners don't just answer queries; they prove them. Every response includes a cryptographic Merkle proof anchored to live Base block hashes, scored across four rigorous dimensions."
- **Slide 5 (Dynamic TAO Tokenomics):** "Under dTAO, emissions are cleanly split: 41% to miners, 41% to validators, and 18% to the subnet treasury, with treasury tokens locked into AMM liquidity pools during immunity."
- **Slide 6 (Go-To-Market & Grants):** "We leverage dual-stack non-dilutive grant funding—including Base Builder Rewards and Optimism Retro Funding—to cover infrastructure overhead while partnering with top validator syndicates."
- **Slide 7 (Launch Roadmap):** "Our local testnet on netuid 505 is fully verified. We are hardening AWS nodes now, targeting Finney mainnet registration on August 15."
- **Slide 8 (Call to Action):** "We are onboarding founding validator partners today. Check out our GitHub repository or visit arctura.network/base to join us."

---

## Part 4 — Autonomous Bittensor Developer & GitHub Workflow

You asked how to train me (Manus) on coding, triage, and issue resolution across your repositories (such as `virtualmase/portfolio` and `Arctura-Collective/arctura-base-subnet`). Here is the exact operational framework for how I act as your **Autonomous Bittensor Developer**:

### 1. How I Interact with Your GitHub Repositories
- **Pre-Configured GitHub CLI (`gh`):** I have direct access to GitHub via pre-authenticated `gh` commands in the sandbox shell.
- **Cloning & Branching:** For any new feature or bug fix, I clone your repository, create a dedicated feature branch (`git checkout -b feature/name`), write code, run tests, and push back to GitHub.
- **Pull Requests & Code Reviews:** I can open pull requests (`gh pr create`), review diffs, resolve merge conflicts, and address automated CI/CD failures (`pytest`, `mypy`, `black`).

### 2. Standard Operating Procedure for Coding & Triage Tasks
When you assign a coding task or GitHub issue, provide instructions using this standard prompt template:

```markdown
Task: [Describe bug fix, new miner feature, or RPC optimization]
Repository: [Arctura-Collective/arctura-base-subnet or virtualmase/portfolio]
Issue # / Reference: [Link or description]
Acceptance Criteria:
1. All unit tests must pass (`pytest tests/ -v`).
2. Code must follow existing repository patterns and Apache-2.0 standards.
3. Push changes to a new branch and open a draft PR.
```

Upon receiving this, I will immediately execute the task, verify execution in the sandbox, and report back with the pull request link.

---

## References

- [Bittensor Documentation](https://www.bittensor.com/docs) [11]
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [Arctura Network Portal](https://arctura.network) [11]
