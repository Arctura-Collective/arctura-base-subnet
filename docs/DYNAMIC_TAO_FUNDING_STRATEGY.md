# Dynamic TAO Funding Strategy

Arctura should not treat `686 TAO` as a fixed launch requirement. Finney subnet
registration cost is dynamic and must be checked immediately before any launch
decision.

Current ticker data:

```bash
python scripts/update_subnet_cost_ticker.py
python -m json.tool docs/data/subnet_launch_cost.json
```

If this repository host does not have `btcli`, run the live cost command in a
separate trusted shell and paste the output into the payload builder without
having the repo call Bittensor:

```bash
python scripts/update_subnet_cost_ticker.py \
  --raw-btcli-output 'Subnet burn cost: 812.5 TAO'
python -m json.tool docs/data/subnet_launch_cost.json
```

Manual mode only parses operator-provided output; it does not query the chain,
open a wallet, register a subnet, stake, transfer funds, or approve launch.

The committed JSON and `docs/subnet-cost.html` page are planning snapshots. The
mainnet checklist still requires a fresh burn-cost check within 30 minutes of
registration and explicit operator approval before any on-chain spend.

## Can Arctura Launch Without Self-Funding the Full Cost?

For an owner-controlled new Finney subnet, no. The chain registration still
requires the current subnet registration cost to be supplied by an owner account
or a governance-controlled funding path.

The practical question is not whether the cost can be skipped; it is whether
Arctura can avoid one founder personally fronting the whole amount. Viable paths:

- Validator or ecosystem syndicate funds the registration wallet or multisig in
  exchange for documented alpha-token/economic participation.
- Community crowdfunding or launchpad campaign raises TAO into a controlled
  owner account after the 48-hour testnet evidence report passes.
- Grant and sponsor funding covers infrastructure and frees treasury capital for
  registration.
- A partner with an existing subnet owner account handles registration under a
  written governance agreement.
- Arctura continues on testnet or as an off-chain Base intelligence service until
  the registration cost decays or funding is secured.

Non-goals:

- Do not register Finney without the 48-hour evidence gate.
- Do not use an operational hot wallet as the permanent subnet owner.
- Do not fund registration until owner custody and key rotation procedures are
  reviewed in `docs/KEY_ROTATION_AND_CUSTODY.md`.
- Do not present the old `686 TAO` figure as current.
- Do not promise emissions, alpha allocations, or treasury distributions without
  written governance terms.

## Current Fundraising Leverage

- PR #9 merged into `main` with GitHub CI green.
- Local suite passes with 286 tests.
- Testnet netuid `505` has produced a systemd-managed attestation; non-zero
  validator weight commits are still pending in the current evidence window.
- The 48-hour evidence run is active but not complete.

## Next Funding Milestone

Wait for `arctura-collect-evidence --output-dir runs/mainnet-evidence` to return
`ok: true`. That gives backers a concrete proof package: uninterrupted services,
attestations, weight commits, health samples, zero fatal logs, and restart budget
compliance.
