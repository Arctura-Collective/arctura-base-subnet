# Mainnet Launch Blockers

No Finney subnet creation is allowed until every blocker below is satisfied and
the operator gives explicit final approval.

## Current Status

- Testnet netuid: `505`
- Current 48-hour run start: `Sun 2026-08-23 15:34:42 PDT`
- Miner service: `arctura-miner.service`
- Validator service: `arctura-validator.service`
- Health timer: `arctura-health.timer`
- Current repo checkpoint: `codex/live-launch`

## Blocked Until: Testnet Evidence

- [ ] `arctura-collect-evidence --output-dir runs/mainnet-evidence` exits `0`
- [ ] `runs/mainnet-evidence/report.json` contains `"ok": true`
- [ ] Evidence window is based on the systemd-managed services, not the older
  template helper and not the foreground probe
- [ ] Report includes at least one successful attestation
- [ ] Report includes at least two successful weight commits inside the evidence window
- [ ] Health samples meet the required threshold (`570` by default)
- [ ] Restart counts remain at zero during the evidence window
- [ ] Fatal journal markers are absent

Verify without mutation:

```bash
cd /home/brimstone/arctura-base-subnet-live
systemctl --user show arctura-miner arctura-validator \
  --property=ActiveState,SubState,MainPID,ActiveEnterTimestamp,NRestarts
journalctl --user -u arctura-miner --since "2026-08-23 15:31:18" --no-pager
journalctl --user -u arctura-validator --since "2026-08-23 15:34:42" --no-pager
journalctl --user -u arctura-health --since "2026-08-23 15:34:42" --no-pager
arctura-collect-evidence --output-dir runs/mainnet-evidence
python -m json.tool runs/mainnet-evidence/report.json
```

## Blocked Until: Code and Review

- [x] Current checkpoint is reviewed and committed intentionally
- [x] Full test suite passes after the final checkpoint
- [x] Ruff check/format passes
- [x] `git diff --check` passes
- [ ] Gordon prompt 1 evidence-gate findings are either resolved or explicitly accepted
- [ ] Gordon prompt 2 scoring/adversarial findings are either resolved or explicitly accepted
- [ ] Decision recorded: current scoring vs. hardened scoring before mainnet
- [ ] No unrelated dirty worktree changes are mixed into launch commit

Already satisfied in the current checkpoint:

- [x] Local full suite passed with `113` tests on 2026-08-23
- [x] Ruff check/format over the repo passed
- [x] `git diff --check` passed
- [x] Finney register/stake CLI guard exists via `--confirm-finney`
- [x] Finney preflight rejects non-Base-mainnet chain id
- [x] Bittensor v10.5 runtime compatibility verified on testnet
- [x] Systemd-managed testnet services emitted one attestation and one non-zero
  weight commit on 2026-08-23

Verify without mutation:

```bash
cd /home/brimstone/arctura-base-subnet-live
git status --short
git diff --stat
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy arctura_base neurons scripts tests
git diff --check
```

## Blocked Until: Capital and Operator Controls

- [ ] Finney burn cost checked within 30 minutes of launch decision
- [ ] Owner coldkey balance is at least burn cost plus 20% buffer
- [ ] Validator hotkey has enough liquid TAO for recycle registration
- [ ] Miner hotkey has enough liquid TAO for recycle registration
- [ ] At least 30 days of server cost is budgeted
- [ ] Owner coldkey mnemonic stored offline in at least two separate locations
- [ ] Validator coldkey mnemonic stored offline
- [ ] Miner coldkey mnemonic stored offline
- [ ] Final operator approval recorded with date, burn cost, wallet names, and command

Verify without mutation:

```bash
btcli subnet burn_cost --subtensor.network finney
btcli wallet balance --wallet.name owner --subtensor.network finney
btcli wallet balance --wallet.name validator --subtensor.network finney
btcli wallet balance --wallet.name miner --subtensor.network finney
```

Do not run any registration or stake command from this checklist.

## Blocked Until: Network and Community

- [ ] At least one external validator is confirmed for post-launch
- [ ] Bittensor Discord announcement is drafted for `#subnet-owners`
- [ ] Mainnet monitoring host is selected
- [ ] Mainnet operator env is prepared privately and reviewed
- [ ] Mainnet miner axon port/firewall plan is confirmed
- [ ] Rollback/stop procedure is documented for both neuron services

Verify without mutation:

```bash
systemctl --user cat arctura-miner arctura-validator arctura-health.timer
cat deploy/systemd/operator.env.example
cat docs/SUBNET_LAUNCH.md
cat docs/GO_NO_GO_CHECKLIST.md
```

## Commands Forbidden Until Final Approval

Do not run these until every blocker above is satisfied and final approval is
explicit:

```bash
btcli subnet create --wallet.name owner --subtensor.network finney
btcli subnet recycle_register --netuid N --wallet.name validator --subtensor.network finney
btcli subnet recycle_register --netuid N --wallet.name miner --subtensor.network finney
btcli subnet register --netuid N --wallet.name validator --subtensor.network finney
btcli subnet register --netuid N --wallet.name miner --subtensor.network finney
btcli stake add --subtensor.network finney
```
