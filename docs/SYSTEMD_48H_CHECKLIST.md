# Systemd 48-Hour Evidence Checklist

Use this checklist for the supervised Arctura Base testnet run before any Finney
launch decision.

Current run anchor: `Tue 2026-07-07 19:50:43 PDT`

## Service Install

- [x] User units installed under `~/.config/systemd/user/`
- [x] Private operator env installed at `~/.config/arctura-base-subnet.env`
- [x] Operator env mode set to `0600`
- [x] Miner service enabled: `arctura-miner.service`
- [x] Validator service enabled: `arctura-validator.service`
- [x] Health timer enabled: `arctura-health.timer`
- [x] `loginctl enable-linger "$USER"` confirmed on the launch host

Verify:

```bash
systemctl --user status arctura-miner arctura-validator arctura-health.timer
stat -c '%a %n' ~/.config/arctura-base-subnet.env
loginctl show-user "$USER" --property=Linger
```

## Runtime State

- [x] Miner active on testnet netuid `505`
- [x] Validator active on testnet netuid `505`
- [x] Miner axon started on port `8191`
- [x] Validator issued a mandate to UID `1`
- [x] Miner attested a systemd-managed mandate
- [x] Validator scored UID `1`
- [ ] Validator commits at least one non-zero weight during the uninterrupted systemd run
- [ ] Restart counts remain within budget
- [ ] Health timer emits at least 500 passing samples
- [ ] No fatal journal markers during the 48-hour window

Verify:

```bash
systemctl --user show arctura-miner arctura-validator \
  --property=ActiveState,SubState,MainPID,ActiveEnterTimestamp,NRestarts
journalctl --user -u arctura-miner --since "2026-07-07 19:50:43" --no-pager
journalctl --user -u arctura-validator --since "2026-07-07 19:50:43" --no-pager
journalctl --user -u arctura-health --since "2026-07-07 19:50:43" --no-pager
```

## Unit Robustness

- [x] Miner unit uses `Restart=always`
- [x] Validator unit uses `Restart=always`
- [x] Neuron units load `EnvironmentFile=%h/.config/arctura-base-subnet.env`
- [x] Neuron units use `NoNewPrivileges=true`
- [x] Neuron units use `PrivateTmp=true`
- [x] Health timer runs every five minutes
- [x] Health timer is persistent
- [ ] Operator verifies env values match the intended host and netuid before any restart

Verify:

```bash
grep -R "Restart=always\\|EnvironmentFile=\\|NoNewPrivileges=\\|PrivateTmp=" deploy/systemd
grep -R "OnUnitActiveSec=5min\\|Persistent=true" deploy/systemd/arctura-health.timer
```

## Evidence Collection

- [ ] Run has lasted at least 48 uninterrupted hours from the later neuron start time
- [ ] `arctura-collect-evidence` exits `0`
- [ ] `runs/mainnet-evidence/report.json` contains `"ok": true`
- [ ] Exported miner, validator, and health logs were reviewed
- [ ] Report was retained outside volatile terminal output

Collect after the 48-hour window:

```bash
cd /home/brimstone/gbrain-work/arctura-base-subnet
arctura-collect-evidence --output-dir runs/mainnet-evidence
python -m json.tool runs/mainnet-evidence/report.json
```

## Known Footguns

- Do not count the older `subnet-ranker/run_testnet_template_nodes.py` loop as
  evidence for this Arctura build.
- Do not count the successful foreground probe as the 48-hour run start; the
  evidence window starts from the systemd-managed neuron start.
- A chain cooldown deferral is not a failure by itself, but the 48-hour evidence
  gate still requires at least one successful weight commit inside the collected
  systemd journal window.
- Process state alone is insufficient. The evidence report must pass.
