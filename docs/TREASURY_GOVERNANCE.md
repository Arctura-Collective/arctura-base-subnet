# Treasury Governance and Dry-Run Distribution Planning

This runbook covers the repository-safe part of issue #7: defining an auditable
treasury distribution policy and generating unsigned dry-run plans for multisig
review.

It does not move funds, sign transactions, construct extrinsics, manage private
keys, or approve dTAO liquidity actions. Every treasury action still requires a
separate owner/multisig approval and hardware-wallet confirmation.

## Policy template

The template lives at:

```text
deploy/treasury/emission_policy.example.json
```

It encodes the current treasury split:

- 40% core engineering
- 30% validator syndicates
- 30% dTAO liquidity provisioning

The policy also requires:

- `dry_run_only: true`
- 18% treasury share of subnet emissions
- at least two multisig signers
- at least 24 hours of timelock before execution

## Audit a policy before planning

Before building a distribution plan, render a non-mutating readiness audit:

```bash
python -m arctura_base.treasury \
  --policy deploy/treasury/emission_policy.example.json \
  --audit-only
```

The audit reports whether the policy is still using placeholder destinations,
whether allocation shares sum to 100%, and whether signer/timelock requirements
meet the launch minimums. It does not require `--total-tao`, wallet files, chain
access, or AWS credentials.

## Generate an unsigned plan

For template review with placeholder destinations:

```bash
python -m arctura_base.treasury \
  --policy deploy/treasury/emission_policy.example.json \
  --total-tao 12.5 \
  --allow-placeholders
```

For a real pre-approval packet, copy the template outside version control,
replace every destination with the approved multisig or liquidity controller,
and omit `--allow-placeholders`:

```bash
python -m arctura_base.treasury \
  --policy /secure/review/arctura-treasury-policy.json \
  --total-tao 12.5 \
  --output /secure/review/arctura-unsigned-treasury-plan.json
```

The output is an unsigned JSON plan. Operators must compare it against the
approved governance decision before any separate treasury transaction is built.

## Final launch approval packet

Before any Finney subnet registration spend, create a separate non-signing
approval packet from the green aggregate readiness report, green 48-hour
evidence report, and a fresh burn-cost snapshot:

```bash
arctura-mainnet-approval \
  --readiness-report runs/mainnet-evidence/readiness.json \
  --evidence-report runs/mainnet-evidence/report.json \
  --cost-payload docs/data/subnet_launch_cost.json \
  --operator OWNER_NAME_OR_ID \
  --reviewer REVIEWER_NAME_OR_ID \
  --owner-wallet owner \
  --validator-wallet validator \
  --miner-wallet miner \
  --output /secure/review/arctura-mainnet-approval.json
```

The command refuses to render a packet if the aggregate readiness report is red,
if the evidence report is red, if the burn-cost payload is unavailable, or if
the burn-cost snapshot is older than 30 minutes. The packet still does not sign,
register, stake, or move funds; it is an audit artifact for the final
hardware-wallet execution step.
