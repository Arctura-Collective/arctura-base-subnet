# Mainnet Readiness Tracker

This tracker maps open GitHub issues to the evidence needed before Arctura Base
Subnet can be considered live-operational on Finney. It separates repository
artifacts from external actions that cannot be completed by source changes
alone.

No item in this document authorizes wallet creation, signing, staking,
registration, treasury movement, AWS provisioning, Docker deployment, or TAO
spend. Those actions require separate explicit operator approval.

## Current evidence gate

Authoritative command:

```bash
arctura-collect-evidence --output-dir runs/mainnet-evidence
```

Mainnet go/no-go requires:

- `ok: true`
- miner and validator live
- zero miner and validator restarts in the evidence window
- zero fatal journal markers
- at least 48 hours elapsed on the current launch candidate
- at least 570 passing health samples
- at least two successful non-zero weight commits with positive `top_weight`

The evidence report includes a derived `remaining` section for the current
window. It is operator guidance only; the launch gate is still `ok: true`.

The current live candidate should not be restarted unless a runtime code change
is merged or an operational fault requires it.

To aggregate the current repo-side launch blockers without external side
effects:

```bash
arctura-readiness-audit \
  --evidence-report runs/mainnet-evidence/report.json \
  --cost-payload docs/data/subnet_launch_cost.json \
  --aws-tfvars deploy/aws/asg/terraform.tfvars.example \
  --monitoring-status deploy/monitoring/monitoring-status.example.json \
  --treasury-policy deploy/treasury/emission_policy.example.json
```

This audit reads existing files only. It does not call Bittensor, AWS,
Terraform, Docker, wallets, or systemd.

## Issue tracker

| Issue | Repository state | Remaining external blocker | Closure evidence |
| --- | --- | --- | --- |
| #1 Core Miner Incentive Mechanism: Merkle Proof Attestation & AgentKit Verification | Merkle proof scoring, live Base block-hash anchoring, payload/context validation, bounded block ranges, AgentKit mutation opt-in, and a machine-readable coverage gate are implemented. | Launch-critical coverage must pass `arctura-coverage-gate --minimum-percent 100`, and runtime evidence must stay clean on the merged code. | CI green, coverage gate `ok: true`, testnet evidence `ok: true`, and no AgentKit mutation enabled unless separately approved. |
| #2 Automated Validator Scoring & Weight-Setting Mechanism | Resonance BFT scoring, calibration hardening, Sybil collision penalty, verified-only stewardship modifiers, cooldown diagnostics, normalization, and weight setting are implemented and tested. Evidence only counts commits with positive `top_weight` and reports cooldown deferrals with remaining block gap. | Need two successful non-zero weight commits in the current evidence window. | Evidence report shows `weight_commits >= 2` and zero restart/fatal failures. |
| #4 AWS EC2 Auto-Scaling Miners & Dynamic Validator Health Checks | Terraform ASG/CloudWatch artifacts, CloudWatch metric rendering, Alertmanager bridge, dry-run AWS tfvars audit, and dry-run validator failover decision packets exist under `deploy/aws/asg/`, `arctura_base.aws_readiness`, and `arctura_base.failover`. | AWS AMI, subnet, security group, instance profile, live probe snapshots, and production apply are not provisioned from this repo. | Green `arctura-aws-asg-audit` report for real tfvars, operator-approved `terraform plan`, production apply evidence, ASG in-service capacity, CloudWatch alarm delivery evidence, and a reviewed validator failover decision packet. |
| #6 Real-Time Telemetry Monitoring & Prometheus/Grafana Alerting Dashboards | Textfile exporter, systemd metrics timer, Prometheus rules, Grafana dashboard, `deploy/monitoring` compose stack, Alertmanager routing, and dry-run `arctura-monitoring-audit` exist. | Hosted or production compose stack is not running from this repo. | Green `arctura-monitoring-audit` report from reviewed status JSON, Prometheus target healthy, Grafana dashboard imported, Alertmanager test notification delivered, and screenshots or exported status attached. |
| #7 Multi-Sig Treasury Governance & Automated dTAO Emission Pool | Dry-run treasury policy/planner, non-mutating policy audit, and custody runbooks exist; unsafe execution docs were removed. | Real multisig/Safe setup, signer list, timelock, treasury destination, and dTAO liquidity controller are external governance actions. | Signed multisig approval packet, hardware-wallet confirmation record, timelock parameters, green treasury policy audit, and dry-run plan matching the approved transaction. |

## Finney spend blockers

Before any Finney mainnet command is run, all of the following must be present:

1. Evidence report returns `ok: true`.
2. Dynamic subnet launch cost is checked from a trusted `btcli` environment
   within 30 minutes of the proposed transaction.
3. `arctura-readiness-audit` returns `ok: true` against the reviewed evidence,
   burn-cost, AWS tfvars, monitoring status, and treasury policy artifacts.
4. Funding source and buffer are confirmed.
5. Owner, validator, miner, and treasury custody gates in
   `docs/KEY_ROTATION_AND_CUSTODY.md` are complete.
6. Explicit operator approval names the exact command, wallet, network, netuid
   if applicable, amount if applicable, and maximum acceptable burn/slippage.
