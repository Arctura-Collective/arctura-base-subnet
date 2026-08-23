# Key Rotation and Emergency Custody Runbook

This runbook covers Arctura owner, validator, miner, and treasury keys before
Finney mainnet launch. It is intentionally operational: repository changes may
prepare the process, but no key generation, secret inspection, signing, fund
movement, subnet registration, staking, or treasury action is authorized by this
document alone.

## Roles

| Role | Scope | Custody requirement |
| --- | --- | --- |
| Owner coldkey | Finney subnet ownership and registration authority | Offline hardware-backed custody; no routine server use |
| Validator coldkey | Validator wallet parent key | Offline backup; hotkey may operate on the validator host |
| Miner coldkey | Miner wallet parent key | Offline backup; hotkey may operate on the miner host |
| Treasury / emissions | Post-launch treasury and liquidity actions | Multisig or equivalent governance-controlled custody |

## Pre-Mainnet Custody Gate

Complete these before any `btcli subnet create`, recycle registration, staking,
or treasury transaction:

- Owner coldkey is not an operational hot wallet.
- Owner coldkey seed phrase is stored offline in at least two physically
  separate locations.
- Validator and miner coldkey seed phrases are stored offline.
- Any hotkey present on a server can be revoked or replaced without losing the
  coldkey.
- Treasury destination is controlled by a multisig or documented governance
  account, not a single unattended server key.
- At least two humans have reviewed the wallet names, hotkey names, and intended
  chain/network before signing.
- A final approval record exists with date, approving parties, wallet names,
  burn cost, buffer amount, and exact commands.

## Planned Hotkey Rotation

Use this process when replacing a validator or miner hotkey for routine
maintenance.

1. Stop the affected service only after deciding whether the current evidence
   window can be invalidated.
2. Create or import the replacement hotkey on the intended host under the
   correct coldkey wallet. This step is operator-gated and must not be run by
   automation without approval.
3. Verify the replacement hotkey address out of band.
4. Update the private environment file, for example
   `~/.config/arctura-base-subnet.env`, to reference the replacement hotkey.
5. Start the affected service and verify:

   ```bash
   systemctl --user status arctura-miner arctura-validator --no-pager
   journalctl --user -u arctura-miner -u arctura-validator --since "10 minutes ago" --no-pager
   .venv/bin/arctura-collect-evidence --output-dir runs/mainnet-evidence
   ```

6. Record the rotation time, old hotkey, new hotkey, operator, reason, and
   evidence-window impact.

## Emergency Hotkey Revocation

Use this when a server, hotkey, API key, or operator laptop may be compromised.

1. Isolate the host from inbound traffic.
2. Stop affected services:

   ```bash
   systemctl --user stop arctura-validator arctura-miner
   ```

3. Preserve logs for incident review:

   ```bash
   journalctl --user -u arctura-miner -u arctura-validator --since "24 hours ago" --no-pager
   ```

4. From a clean machine, rotate the compromised hotkey under the relevant
   coldkey. If the coldkey or owner key may be exposed, treat this as an owner
   custody incident and escalate to multisig signers before any new transaction.
5. Remove the compromised hotkey material from the host after logs and forensic
   artifacts are preserved.
6. Rebuild the host from a clean image before restoring service.
7. Restart the evidence window only after the replacement hotkey is verified and
   the service is clean.

## Owner Coldkey or Treasury Incident

If the owner coldkey, treasury key, or multisig signer is suspected compromised:

- Do not register, stake, unstake, transfer, or alter subnet ownership.
- Convene the approved signers/operators out of band.
- Check current chain state from a clean read-only machine.
- Prepare a replacement owner or treasury custody plan.
- Require explicit signed approval before any recovery transaction.
- Publish only factual incident status; do not disclose mnemonic, private-key,
  API-key, or signing-device details in GitHub issues, PRs, chat, or logs.

## Rotation Record Template

```text
Date/time UTC:
Reason:
Affected role:
Old hotkey SS58:
New hotkey SS58:
Coldkey wallet name:
Host:
Operator:
Approvers:
Commands approved:
Evidence-window impact:
Post-rotation checks:
Notes:
```

## Forbidden Without Explicit Final Approval

These commands are examples of actions that must not be run merely because this
runbook exists:

```bash
btcli wallet new_coldkey
btcli wallet regen_coldkey
btcli wallet new_hotkey
btcli subnet create --subtensor.network finney
btcli subnet recycle_register --subtensor.network finney
btcli subnet register --subtensor.network finney
btcli stake add --subtensor.network finney
btcli transfer --subtensor.network finney
```

