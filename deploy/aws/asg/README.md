# Arctura AWS Auto Scaling and Health Alarms

This Terraform module is the production infrastructure artifact for GitHub issue
#4. It is intentionally declarative: reviewing or testing this repository never
provisions AWS resources.

## What it defines

- EC2 launch template for miner nodes.
- Auto Scaling Group for miner axons across supplied subnets.
- CPU target-tracking scaling policy.
- mandate-load step scaling policy backed by a custom CloudWatch metric named
  `Arctura/Miner` / `MandatesPerMinute`.
- CloudWatch alarms for miner CPU pressure, mandate-load pressure, unhealthy
  ASG capacity, and validator health-check failures.
- SNS topic plus Lambda bridge that converts CloudWatch alarm notifications into
  Alertmanager-compatible Prometheus webhook alerts.

Launch evidence metrics are rendered separately by
`scripts/render_cloudwatch_metrics.py`. That script produces a
`put-metric-data` JSON payload for the `Arctura/Launch` namespace but does not
call AWS or provision resources.

Validator failover planning is also dry-run only. Use
`deploy/aws/asg/validator-probe.example.json` as the operator-provided probe
schema, then render an advisory decision packet:

```bash
arctura-validator-failover-plan \
  --evidence-report runs/mainnet-evidence/report.json \
  --probe-snapshot deploy/aws/asg/validator-probe.example.json \
  --output runs/mainnet-evidence/validator-failover-decision.json
```

The packet can say `hold`, `investigate`, or `failover_ready`. It never stops a
service, modifies AWS, promotes a standby, signs transactions, or moves funds;
actual failover still requires separate operator approval.

## Required inputs

Copy `terraform.tfvars.example` to `terraform.tfvars` outside version control and
fill in real VPC/subnet/security-group/AMI values.

Do not place coldkeys, mnemonics, or owner credentials on EC2 instances. This
module is for hotkey-operated runtime nodes only.

Before running `terraform plan`, audit the variable file locally:

```bash
arctura-aws-asg-audit --tfvars terraform.tfvars
```

The audit parses the tfvars file and reports placeholder IDs, invalid capacity
bounds, missing subnets/security groups, non-HTTPS Alertmanager endpoints, and
secret markers such as coldkey or mnemonic text. It does not call AWS,
Terraform, Docker, systemd, wallets, or the network.

## Deployment outline

```bash
cd deploy/aws/asg
terraform init
terraform plan -out arctura-asg.plan
terraform apply arctura-asg.plan
```

Before applying:

1. Confirm the AMI contains Ubuntu 24.04, Python 3.12, systemd user lingering,
   and the Arctura repo checkout.
2. Confirm the launch template uses an encrypted 200 GB gp3 root volume unless a
   smaller tested AMI-specific value has been explicitly approved.
3. Confirm the security group exposes only SSH from operator IPs and the miner
   axon port from intended Bittensor peers.
4. Confirm `alertmanager_webhook_url` points at an authenticated/isolated
   Alertmanager endpoint.
5. Confirm no coldkey material is present in user data, AMI snapshots, or SSM
   parameters.
