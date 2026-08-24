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
- at least two successful weight commits

The current live candidate should not be restarted unless a runtime code change
is merged or an operational fault requires it.

## Issue tracker

| Issue | Repository state | Remaining external blocker | Closure evidence |
| --- | --- | --- | --- |
| #1 Core Miner Incentive Mechanism: Merkle Proof Attestation & AgentKit Verification | Merkle proof scoring, live Base block-hash anchoring, payload/context validation, bounded block ranges, and AgentKit mutation opt-in are implemented and tested. | None for source-control readiness; runtime evidence must stay clean on the merged code. | CI green, testnet evidence `ok: true`, and no AgentKit mutation enabled unless separately approved. |
| #2 Automated Validator Scoring & Weight-Setting Mechanism | Resonance BFT scoring, calibration hardening, Sybil collision penalty, verified-only stewardship modifiers, cooldown diagnostics, normalization, and weight setting are implemented and tested. | Need two successful weight commits in the current evidence window. | Evidence report shows `weight_commits >= 2` and zero restart/fatal failures. |
| #4 AWS EC2 Auto-Scaling Miners & Dynamic Validator Health Checks | Terraform ASG/CloudWatch artifacts, CloudWatch metric rendering, Alertmanager bridge, and dry-run validator failover decision packets exist under `deploy/aws/asg/` and `arctura_base.failover`. | AWS AMI, subnet, security group, instance profile, live probe snapshots, and production apply are not provisioned from this repo. | Operator-approved `terraform plan`, production apply evidence, ASG in-service capacity, CloudWatch alarm delivery evidence, and a reviewed validator failover decision packet. |
| #6 Real-Time Telemetry Monitoring & Prometheus/Grafana Alerting Dashboards | Textfile exporter, systemd metrics timer, Prometheus rules, Grafana dashboard, `deploy/monitoring` compose stack, and Alertmanager routing are implemented and tested. | Hosted or production compose stack is not running from this repo. | Prometheus target healthy, Grafana dashboard imported, Alertmanager test notification delivered, and screenshots or exported status attached. |
| #7 Multi-Sig Treasury Governance & Automated dTAO Emission Pool | Dry-run treasury policy/planner and custody runbooks exist; unsafe execution docs were removed. | Real multisig/Safe setup, signer list, timelock, treasury destination, and dTAO liquidity controller are external governance actions. | Signed multisig approval packet, hardware-wallet confirmation record, timelock parameters, and dry-run plan matching the approved transaction. |

## Finney spend blockers

Before any Finney mainnet command is run, all of the following must be present:

1. Evidence report returns `ok: true`.
2. Dynamic subnet launch cost is checked from a trusted `btcli` environment
   within 30 minutes of the proposed transaction.
3. Funding source and buffer are confirmed.
4. Owner, validator, miner, and treasury custody gates in
   `docs/KEY_ROTATION_AND_CUSTODY.md` are complete.
5. Explicit operator approval names the exact command, wallet, network, netuid
   if applicable, amount if applicable, and maximum acceptable burn/slippage.
