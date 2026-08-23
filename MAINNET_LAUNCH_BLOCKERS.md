# Mainnet Launch Blockers

No Finney subnet creation is allowed until every blocker below is satisfied and
the operator gives explicit final approval.

## Current Status

- Testnet netuid: `505`
- Current 48-hour run start: `Tue 2026-07-07 19:50:43 PDT`
- Miner service: `arctura-miner.service`
- Validator service: `arctura-validator.service`
- Health timer: `arctura-health.timer`
- Current repo checkpoint: intentionally uncommitted

## Blocked Until: Testnet Evidence

- [ ] `arctura-collect-evidence --output-dir runs/mainnet-evidence` exits `0`
- [ ] `runs/mainnet-evidence/report.json` contains `"ok": true`
- [ ] Evidence window is based on the systemd-managed services, not the older
  template helper and not the foreground probe
- [ ] Report includes at least one successful attestation
- [ ] Report includes at least one successful weight commit inside the evidence window
- [ ] Health samples meet the required threshold
- [ ] Restart counts remain within budget
- [ ] Fatal journal markers are absent

Verify without mutation:

```bash
cd /home/brimstone/gbrain-work/arctura-base-subnet
systemctl --user show arctura-miner arctura-validator \
  --property=ActiveState,SubState,MainPID,ActiveEnterTimestamp,NRestarts
journalctl --user -u arctura-miner --since "2026-07-07 19:50:43" --no-pager
journalctl --user -u arctura-validator --since "2026-07-07 19:50:43" --no-pager
journalctl --user -u arctura-health --since "2026-07-07 19:50:43" --no-pager
arctura-collect-evidence --output-dir runs/mainnet-evidence
python -m json.tool runs/mainnet-evidence/report.json
```

## Blocked Until: Code and Review

- [ ] Current checkpoint is reviewed and committed intentionally
- [ ] Full test suite passes after the final checkpoint
- [ ] Focused Ruff check/format passes on changed files
- [ ] `git diff --check` passes
- [ ] Gordon prompt 1 evidence-gate findings are either resolved or explicitly accepted
- [ ] Gordon prompt 2 scoring/adversarial findings are either resolved or explicitly accepted
- [ ] Decision recorded: current scoring vs. hardened scoring before mainnet
- [ ] No unrelated dirty worktree changes are mixed into launch commit

Already satisfied in the current checkpoint:

- [x] Local full suite passed with `103` tests on 2026-07-08
- [x] Focused Ruff check/format over changed surface passed
- [x] `git diff --check` passed
- [x] Finney register/stake CLI guard exists via `--confirm-finney`
- [x] Finney preflight rejects non-Base-mainnet chain id

Verify without mutation:

```bash
cd /home/brimstone/gbrain-work/arctura-base-subnet
git status --short
git diff --stat
/home/brimstone/gbrain-work/subnet-template-venv/bin/python -m pytest tests/ -q
/home/brimstone/gbrain-work/subnet-template-venv/bin/python -m ruff check \
  arctura_base/base_rpc.py arctura_base/cli.py arctura_base/evidence.py \
  arctura_base/evidence_collect.py tests/test_cli.py tests/test_evidence.py \
  tests/test_evidence_collect.py tests/test_systemd_units.py
/home/brimstone/gbrain-work/subnet-template-venv/bin/python -m ruff format --check \
  arctura_base/base_rpc.py arctura_base/cli.py arctura_base/evidence.py \
  arctura_base/evidence_collect.py tests/test_cli.py tests/test_evidence.py \
  tests/test_evidence_collect.py tests/test_systemd_units.py
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
