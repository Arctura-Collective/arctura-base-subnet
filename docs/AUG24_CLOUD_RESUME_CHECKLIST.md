# Arctura Cloud Resume Checklist — August 24, 2026

This runbook begins only after the Ubuntu cloud computer is available again. It is designed to restore operational visibility and validate readiness without sending any on-chain transaction.

## 1. Restore the Maintenance Environment

1. Confirm the cloud computer is running and inspect `/home/ubuntu/AGENTS.md` or `agents.md` before making changes.
2. Verify Docker, `btcli`, Python, GitHub CLI, and the repository checkout are available.
3. Pull the `main` branch of `bittensaur/arctura-base-subnet`, including `scripts/run_maintenance.py`.
4. Confirm the source locations for `burn_cost.log` and `validator.log`; update the maintenance invocation with `--repo-dir` only if the repository is stored elsewhere.
5. Run the daily health check locally:

   ```bash
   python3 scripts/run_maintenance.py --mode daily
   ```

## 2. Restore Recurring Operations

1. Confirm the cloud computer can reach the Finney RPC endpoint and the approved monitoring endpoints.
2. Confirm GitHub CLI authentication before enabling automated vulnerability issue creation:

   ```bash
   gh auth status
   ```

3. Run and review the weekly audit manually before enabling the Monday cadence:

   ```bash
   python3 scripts/run_maintenance.py --mode weekly --create-issues
   ```

4. Confirm the report destination is Slack channel `C0BPK23UZ3Q`. The report poster must use the approved Slack integration directly; the deterministic runner only produces the report text.

## 3. Non-Broadcast Finney Registration Readiness

Before **any** registration attempt, complete the checklist in `docs/GO_NO_GO_CHECKLIST.md`, including live burn-cost validation, wallet balances with buffer, test results, axon reachability, monitoring, and independent review.

> **Safety boundary:** Do not invoke `btcli subnet create`, sign an extrinsic, or move funds from the cloud computer until the owner provides a separate explicit multisig authorization. Ledger or other hardware wallet confirmation remains required for every on-chain signing action.

## 4. Immediate Verification Commands

```bash
cd /home/ubuntu/arctura-base-subnet
git pull --ff-only origin main
python3 scripts/run_maintenance.py --mode daily
python3 scripts/run_maintenance.py --mode weekly --create-issues
python3 scripts/run_maintenance.py --mode preflight
```
