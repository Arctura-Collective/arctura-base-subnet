# AUDIT: Arctura Base Subnet Mainnet Launch Readiness

**Audited by:** Gordon, Docker's AI assistant (adapted for security audit)  
**Date:** 2026-08-23  
**Scope:** Adversarial validator/miner behavior, evidence-gate false positives, launch blocker completeness  
**Constraints:** No wallet commands, no secrets inspection, read-only analysis

---

## Codex Triage Notes

This file is retained as raw audit input. Some findings were already resolved in
the branch Gordon reviewed, so use current source as authoritative.

- Finding 1.1 is already resolved: serving miners are selected independently of
  validator permits.
- Finding 1.5 is accepted and fixed in `arctura_base/incentive.py`: self-declared
  energy tags are telemetry only and no longer change scores.
- Findings 2.1, 2.2, 2.3, and 2.4 are partially fixed in
  `arctura_base/evidence.py`: defaults now require zero restarts, 570 health
  passes, at least two weight commits, and broader fatal markers.
- Issue #6 is partially addressed through a Prometheus textfile exporter,
  optional systemd timer, and alert rules. This does not replace a hosted
  Prometheus/Grafana deployment.
- Finding 3.1 is addressed in `neurons/miner.py`: the miner checks whether the
  configured axon port is already listening and fails before starting the axon.
- Finding 3.2 is partially addressed in `scripts/check_ubuntu_readiness.sh` and
  `docs/VPS_PROVISIONING_CHECKLIST.md`: launch preflight now checks disk and
  inode usage, and provisioning docs include journal footprint bounds. This is
  not a replacement for hosted disk alerts.
- Finding 1.2 is addressed in `neurons/validator.py` and
  `arctura_base/incentive.py`: mandate deadlines use a tighter bounded window,
  and responses after `deadline_block + LATENCY_GRACE_BLOCKS` forfeit the full
  response score.
- Finding 1.3 is further hardened in `neurons/validator.py`: calibration now
  requires warm-up samples and applies a variance penalty to unstable confidence
  histories. `score_response` also defaults unproven calibration to `0.0`.
- Finding 3.3 is addressed in `docs/KEY_ROTATION_AND_CUSTODY.md`: owner,
  validator, miner, and treasury custody now have planned rotation, emergency
  revocation, incident escalation, and approval boundaries documented.
- Finding 1.4 is addressed in `arctura_base/incentive.py`: hash-collision
  detection now flags triads and larger groups by default (`>=3`) instead of
  only four-or-more (`>3`), while leaving pair collisions unflagged because
  deterministic mandates can make two honest miners return the same hash.
- Remaining high-priority work: none from the Gordon high-priority triage list;
  mainnet remains blocked by live evidence, funding, multisig/operator approval,
  and unresolved repository issues.

---

## **SECTION 1: ADVERSARIAL SCORING & VALIDATOR GAMING VECTORS**

### **Finding 1.1 — CRITICAL: Permit-Based Exclusion Allows Validator UID Monopoly**
**File:** `neurons/validator.py`, lines 153–169 (`_get_active_miner_uids()`)
**Severity:** CRITICAL
**Category:** Miner Selection Gaming

**Issue:**  
The validator's miner selection logic filters UIDs by:
1. Checking if a UID holds a validator permit
2. Checking if `is_serving` is True

On small subnets (like netuid 505 testnet), this creates a dangerous monopoly vector:
- If miners also hold permits (common on small subnets), they are **excluded** from scoring.
- This can reduce the eligible miner set from N miners to 0, causing validators to skip scoring cycles.
- A hostile validator could intentionally exclude legitimate miners by gaming permit assignment or timing.

**Proof of vulnerability:**
```python
uid != my_uid and bool(self.metagraph.axons[uid].is_serving)
# Missing: validator permit gate is checked but filters serve/non-serve, not miners/validators
```

**Impact:**
- Validators can selectively score miners by controlling subnet permit distribution.
- Miners cannot prove their participation if filtered out.
- Sybil attackers can create miners with permits to exclude legitimate competitors.

**Fix:**
```python
def _get_active_miner_uids(self) -> list[int]:
    """Return serving Axon UIDs, excluding this validator's own UID."""
    try:
        my_uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
    except ValueError:
        my_uid = -1

    # On small subnets, a miner may also hold a permit. Do NOT exclude them.
    # Instead, filter for: not my_uid AND is_serving AND has non-zero stake.
    # Permit presence alone is not a role signal.
    return [
        uid
        for uid in range(len(self.metagraph.S))
        if uid != my_uid and bool(self.metagraph.axons[uid].is_serving) 
        and self.metagraph.S[uid] > 0  # Explicit stake check
    ]
```

---

### **Finding 1.2 — HIGH: Block Deadline Gaming Allows Late-Stage Score Injection**
**File:** `neurons/validator.py`, lines 206–227 (`_build_mandate()`)
**Severity:** HIGH
**Category:** Latency Spoofing

**Issue:**  
The mandate deadline is set relative to current block:
```python
deadline_block = current_block + tempo // 4
```

At 360-block tempos (~72 min), this sets a deadline **90 blocks (~18 minutes) in the future**. A miner can:
1. Respond late (at block N+120), pay small latency penalty (`score_latency()` returns ~0.17)
2. But if validator takes >90 blocks to fetch reference hash, the miner receives no penalty
3. Multi-response attack: send multiple copies of same response at different blocks

**Proof:**  
`arctura_base/incentive.py` line 122:
```python
LATENCY_GRACE_BLOCKS = 12  # ~2.4 minutes
```

If a miner waits 95 blocks (~19 min), `blocks_late = 95 - 90 = 5`, score drops to `1.0 - (5/12) ≈ 0.58`. But if validator hasn't fetched the reference hash by block 90+12=102, the scorer can't compute actual latency. **Late miners still receive scores for work they may not have started.**

**Impact:**
- Miners can delay execution intentionally and still be rewarded.
- Validators can't distinguish honest-late from lazy-late.

**Fix:**  
Reduce deadline window and enforce strict response-block checks:
```python
# Set tighter deadline (tempo // 8 = 45 blocks = ~9 minutes)
deadline_block = current_block + max(30, tempo // 8)

# In score_response, reject any response where response_block > deadline_block + LATENCY_GRACE_BLOCKS
if response_block > deadline_block + LATENCY_GRACE_BLOCKS:
    # Miner forfeited—score 0.0 regardless of content quality
    return 0.0
```

---

### **Finding 1.3 — HIGH: Confidence Calibration Exploitable via Historical Averaging**
**File:** `neurons/validator.py`, lines 181–189 (`_update_calibration()`) and `incentive.py` line 162  
**Severity:** HIGH
**Category:** Scoring Manipulation

**Issue:**  
Confidence calibration uses a **rolling 100-round window**:
```python
self._calibration_history[hotkey] = history[-self._CALIBRATION_WINDOW :]
```

A miner can game this by:
1. **Rounds 1–50:** submit honest, well-calibrated responses (build trust).
2. **Rounds 51–100:** spam overconfident (0.9) responses on fabricated data.
3. **Rounds 101+:** the oldest 50 honest rounds drop out of the window.
4. **Net result:** calibration smoothly transitions to malicious while maintaining high average.

Additionally, new miners default to `calibration = 0.5` (neutral). A miner can:
- Respond with fabricated hashes on first 100 rounds.
- Earn `0.10 × 0.5 = 0.05` calibration component per response with any base score.
- Only after 100 rounds is there enough data to detect the fraud.

**Proof:**  
```python
if not history:
    return 0.5  # New miner: instant 0.5 calibration score for any response
```

**Impact:**
- Sybil attack: spawn 100 new UIDs, each earns `(0.40 × 0 + 0.30 × 0 + 0.20 × 0 + 0.10 × 0.5)` on fabricated responses.
- Gradual drift: established miners slowly retrain their calibration model downward.

**Fix:**  
```python
# Default to 0.0 (or require validator permit + 50 historical attestations before non-zero calibration)
if not history:
    return 0.0  # Unproven miner: no calibration bonus until proven

# Extend validation window; require convergence check
if len(history) < 50:
    # Not enough data; use only observed samples, no smoothing
    return sum(history) / len(history)
else:
    # Compute moving average and variance
    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    # Penalize high variance (signs of drift)
    return max(0.0, mean - 0.1 * variance)
```

---

### **Finding 1.4 — HIGH: Sybil Collision Threshold Too High (>3 Miners)**
**File:** `arctura_base/incentive.py`, lines 236–250 (`detect_hash_collision()`)  
**Severity:** HIGH
**Category:** Sybil Detection

**Issue:**  
The Sybil detection flags UIDs only if **>3 miners** share the same hash:
```python
collision_threshold = 3  # Flag if >3 miners share the same hash
if len(uids) > collision_threshold:
    flagged.update(uids)
```

On a 5-UID subnet (1 validator + 4 miners), an attacker can:
- Create 3 Sybil miners returning identical hashes.
- **None are flagged** (threshold is >3, not ≥3).
- All 3 receive full scores.

Additionally, **legitimate deterministic results could produce hash collisions** if multiple miners fetch the same Base state correctly. The current logic flags all of them equally, making it impossible to detect which are Sybil vs. correct.

**Impact:**
- Sybil triads pass undetected on small subnets.
- Honest miners are penalized alongside attackers.

**Fix:**  
```python
# Lower threshold to 2 on testnet/small subnets; enable allowlist
collision_threshold = 2  # Flag if ≥2 miners share same hash
flagged = set()
for h, uids in hash_to_uids.items():
    if len(uids) >= collision_threshold:
        # Do NOT automatically flag all UIDs; check if hash is "expected"
        # For deterministic state (e.g., USDC balance), >1 hash may be legitimate
        # For ephemeral state (e.g., latest block), >1 hash is suspicious
        # For now: flag all but record confidence
        flagged.update(uids)

return flagged
```

And in the validator loop, apply a **proportional penalty** instead of flat 0.25×:
```python
# From validator.py line 310
if uid in sybil_flagged:
    # Apply graduated penalty based on collision count
    num_collisions = len(hash_to_uids[synapse.base_state_hash])
    penalty = 0.25 / num_collisions  # Share penalty among all colliding UIDs
    final_score *= penalty
```

---

### **Finding 1.5 — MEDIUM: Energy Tag Self-Declaration Trivially Gamed**
**File:** `arctura_base/utils.py`, lines 94–107 (`get_energy_tag()`) and `incentive.py` line 183
**Severity:** MEDIUM
**Category:** Incentive Fraud

**Issue:**  
Energy tag is **self-declared and unverified**:
```python
def get_energy_tag() -> str:
    tag = os.environ.get("ARCTURA_ENERGY_TAG", "unknown").strip().lower()
    return tag if tag in _VALID_ENERGY_TAGS else "unknown"
```

Any miner can set `ARCTURA_ENERGY_TAG=renewable_verified` and earn **+15% P5 modifier** (line 181 in `incentive.py`):
```python
STEWARDSHIP_MODIFIER: dict[str, float] = {
    "renewable_verified": 1.15,  # +15%
    ...
}
```

**Impact:**
- All miners claim `renewable_verified` → identical boost → incentive is nullified.
- Or: honest miners declare `unknown`, fraudulent miners declare `renewable_verified` → attacker advantage.

**Fix:**  
Until Stewardship Index API is available (Phase 03):
1. Remove self-declaration; set all miners to `"unknown"` (1.0× modifier).
2. Or require validator attestation: validators can manually sign energy claims off-chain.

```python
# Disable self-declared energy tags for Phase 01
def apply_stewardship_modifier(base_score: float, energy_tag: str) -> float:
    # For Phase 01, ignore self-declared tags; use only on-chain attestation
    return base_score  # No modifier
```

---

## **SECTION 2: EVIDENCE-GATE FALSE-POSITIVE AUDIT**

### **Finding 2.1 — CRITICAL: Evidence Gate Missing Restart Budget Validation**
**File:** `arctura_base/evidence.py`, lines 65–78 (`evaluate_evidence()`)  
**Severity:** CRITICAL
**Category:** Gate Bypass

**Issue:**  
The evidence gate checks for restart count threshold:
```python
"restart_budget": max(miner_restarts, validator_restarts) <= maximum_restarts,
```

But the **default** `maximum_restarts` is hardcoded to `3` (line 10):
```python
def evaluate_evidence(
    *,
    ...
    maximum_restarts: int = 3,
) -> dict[str, Any]:
```

On a 48-hour run with systemd `Restart=always`, **3 restarts is extremely loose**:
- A miner crashing once per 16 hours is acceptable.
- A miner that silently hangs (no process exit) will never restart, bypassing this check.

More critically, **the checklist doesn't validate whether restarts happened during the evidence window**. A miner could:
1. Restart at hour 0, hour 1, hour 2 (3 restarts before evidence window).
2. Then be stable for 48 hours.
3. `NRestarts=3` at collection time, gate passes.

**Proof:**  
The `systemctl show` property `NRestarts` is cumulative across the service lifetime. There's no way to distinguish restarts **before** vs. **during** the evidence window from the fields currently collected.

**Impact:**
- Unstable miners pass the gate if their crashes happen outside the evidence window.
- Validator gate is non-deterministic (depends on prior history, not just the 48-hour window).

**Fix:**  
In `evidence_collect.py`, record restart count **at the start of the evidence window**:
```python
def collect(output_dir: Path, runner: Runner = run, now: datetime | None = None) -> dict:
    properties = {service: service_properties(service, runner) for service in SERVICES}
    starts = { ... }
    started_at = max(starts.values())
    
    # BEFORE collecting logs, save restart count at window start
    restart_count_at_start = {
        "arctura-miner": int(properties["arctura-miner"]["NRestarts"]),
        "arctura-validator": int(properties["arctura-validator"]["NRestarts"]),
    }
    
    # Collect logs
    logs = { ... }
    collected_at = now or datetime.now(timezone.utc)
    
    # Calculate restarts DURING the window
    miner_restarts_during = int(properties["arctura-miner"]["NRestarts"]) - restart_count_at_start["arctura-miner"]
    validator_restarts_during = int(properties["arctura-validator"]["NRestarts"]) - restart_count_at_start["arctura-validator"]
    
    report = evaluate_evidence(
        ...
        miner_restarts=miner_restarts_during,
        validator_restarts=validator_restarts_during,
    )
```

And tighten the budget:
```python
maximum_restarts: int = 1,  # Max 1 restart allowed during 48-hour window
```

---

### **Finding 2.2 — HIGH: Health Timer Samples Not Time-Bounded to Evidence Window**
**File:** `arctura_base/evidence.py`, lines 82–83 (`evaluate_evidence()`)  
**Severity:** HIGH
**Category:** Gate Bypass

**Issue:**  
The gate counts health timer passes as:
```python
health_passes = health_log.count('"ok": true')
```

But `health_log` is collected from `started_at` (line 34 in `evidence_collect.py`):
```python
logs = {
    "miner": journal("arctura-miner", starts["arctura-miner"], runner),
    "validator": journal("arctura-validator", starts["arctura-validator"], runner),
    "health": journal("arctura-health", started_at, runner),  # started_at is MAX of miner/validator
}
```

If the health timer started **before** the miner/validator (e.g., operator enabled health timer separately), its early samples will be included. More critically:

**The timer runs every 5 minutes** (line 17 in `deploy/systemd/arctura-health.timer`):
```
OnUnitActiveSec=5min
```

Over 48 hours, there should be `(48 × 60) / 5 = 576` samples. The gate requires `≥500` (line 10):
```python
minimum_health_checks: int = 500,
```

A gate that accepts `500/576 = 86.8% pass rate` is **too loose**. If the health service is flaky, it can miss 76 samples and still pass.

**Impact:**
- Health timer sample count doesn't prove continuous operation; it allows gaps.
- Early samples before evidence window are counted.

**Fix:**  
```python
def collect(output_dir: Path, runner: Runner = run, now: datetime | None = None) -> dict:
    # ... existing code ...
    # Only count health samples **after** the evidence window started
    collected_at = now or datetime.now(timezone.utc)
    
    # Calculate expected samples in the time window
    elapsed_seconds = (collected_at - started_at).total_seconds()
    expected_samples = int(elapsed_seconds / (5 * 60))  # 5 minutes per sample
    
    # Filter logs to only include samples from the evidence window
    # (This requires parsing timestamps from health log, which may not be present)
    
    # For now: tighten the minimum
    minimum_health_checks: int = 570,  # Allow max 6 missing samples (30 min downtime) in 48h
```

---

### **Finding 2.3 — MEDIUM: No Mandatory Weight Commit Inside Evidence Window**
**File:** `docs/SYSTEMD_48H_CHECKLIST.md`, line 29  
**Severity:** MEDIUM
**Category:** Gate Inconsistency

**Issue:**  
The checklist requires:
> "Validator commits at least one non-zero weight during the uninterrupted systemd run"

But this is checked manually (line 29 in checklist):
```
[ ] Validator issued a mandate to UID `1`
[ ] Miner attested a systemd-managed mandate
[ ] Validator scored UID `1`
[ ] Validator commits at least one non-zero weight during the uninterrupted systemd run
```

The `arctura-collect-evidence` script checks for weight commits in the log (line 82 in `evidence.py`):
```python
weight_commits = validator_log.count("Weights set")
```

But there's **no enforcement that at least one weight commit happened during the evidence window**. The validator's tempos are ~72 minutes. If:
1. Validator starts at hour 0.
2. Issues mandate at hour 1.
3. Sets weights at hour 2.
4. Then crashes and restarts via `Restart=always` at hour 2:00:01.
5. The `NRestarts` counter increments, but the restart is immediate.
6. At hour 48, there's **1 weight commit in the entire 48-hour log**, but it happened in the first 2 hours.

The gate passes, but the validator was only healthy for 2 hours and then broken for 46.

**Impact:**
- Gate allows one-time successful operation followed by failure.

**Fix:**  
Require **multiple weight commits** spaced across the window:
```python
def evaluate_evidence(...) -> dict[str, Any]:
    # Count weight commits and check they span the window
    weight_commits = validator_log.count("Weights set")
    
    # Extract timestamps from weight commit logs
    import re
    weight_times = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', validator_log)
    
    # Check that commits span at least 40 of the 48 hours
    if weight_times:
        first_commit = parse_timestamp(weight_times[0])
        last_commit = parse_timestamp(weight_times[-1])
        commit_span_hours = (last_commit - first_commit).total_seconds() / 3600
    else:
        commit_span_hours = 0
    
    checks = {
        ...
        "weight_commits": weight_commits >= 2,  # At least 2 commits
        "weight_span": commit_span_hours >= 40,  # Spanning at least 40 hours
    }
```

---

### **Finding 2.4 — MEDIUM: Fatal Markers Regex Incomplete**
**File:** `arctura_base/evidence.py`, line 10  
**Severity:** MEDIUM
**Category:** Gate Incompleteness

**Issue:**  
The fatal marker detection checks for:
```python
FATAL_MARKERS = ("Traceback (most recent call last)", "uncaught exception", "CRITICAL")
```

Python error messages can include:
- `SystemExit` (process exit)
- `KeyboardInterrupt` (manual stop)
- `RuntimeError`, `ValueError`, `TypeError` (if not caught)
- `bittensor.errors.*` (Bittensor-specific errors)

Additionally, the check uses `str.lower().count()`, which is **case-insensitive** but doesn't validate whether the markers are in error contexts. A log line like:
> "This is an uncaught exception in the implementation design..."

...would be counted as a fatal marker even though it's documentation.

**Impact:**
- False positives: non-fatal error mentions block the gate.
- False negatives: uncaught Python errors slip through.

**Fix:**  
```python
FATAL_MARKERS = (
    "Traceback (most recent call last)",
    "uncaught exception",
    "CRITICAL",
    "SystemExit",
    "KeyboardInterrupt",
    "RuntimeError",
    "bittensor.errors",
)

def evaluate_evidence(...) -> dict[str, Any]:
    combined = "\n".join((miner_log, validator_log, health_log))
    fatal_counts = {}
    
    for marker in FATAL_MARKERS:
        # Count only if marker appears in a log line that looks like an error
        pattern = rf"(^|\s)(ERROR|FATAL|CRITICAL|Traceback|Exception).*{re.escape(marker)}"
        fatal_counts[marker] = len(re.findall(pattern, combined, re.IGNORECASE | re.MULTILINE))
    
    checks = {
        ...
        "no_fatal_errors": not any(fatal_counts.values()),
    }
```

---

## **SECTION 3: OPERATIONAL & LAUNCH BLOCKER GAPS**

### **Finding 3.1 — CRITICAL: Miner Axon Port Hardcoded; No Port Conflict Check**
**File:** `neurons/miner.py`, line 35 and `deploy/systemd/operator.env.example`, line 12  
**Severity:** CRITICAL
**Category:** Deployment Risk

**Issue:**  
The miner axon port is hardcoded in systemd config:
```
ExecStart=... --axon.port "$MINER_AXON_PORT" ...
```

And the example env sets it to `8191`. If a user:
1. Deploys two miner instances on the same host (for HA testing).
2. Both use port `8191`.
3. The second miner crashes silently (port in use).
4. Evidence collection reports `NRestarts=0`, gate passes.

**Proof:**  
No port conflict detection exists in miner setup or systemd unit.

**Impact:**
- Silent deployment failures on shared hosts.
- Evidence gate is invalidated if miner doesn't actually start.

**Fix:**  
In `neurons/miner.py`:
```python
import socket

def _verify_port_available(self, port: int) -> None:
    """Ensure the axon port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    if result == 0:
        raise RuntimeError(
            f"Port {port} is already in use. "
            f"Check for conflicting miner instances or change MINER_AXON_PORT."
        )

def run(self) -> None:
    self._verify_port_available(int(self.config.axon.port))
    self.axon.start()
    ...
```

---

### **Finding 3.2 — HIGH: VPS Provisioning Checklist Missing Disk Space & Inode Checks**
**File:** `docs/VPS_PROVISIONING_CHECKLIST.md`  
**Severity:** HIGH
**Category:** Operational Risk

**Issue:**  
The checklist requires "20 GB disk minimum" but provides no verification step. Additionally:
1. **No inode check:** Journal growth can exhaust inodes before disk space is full.
2. **No log rotation:** 48-hour continuous operation can generate 1–5 GB of logs.
3. **No disk monitoring:** If disk fills at hour 36, the evidence window is invalidated.

The checklist states:
> Audit First Cycle Logs

But provides no step to monitor disk usage during the 48-hour window.

**Impact:**
- Disk fills → miner/validator axon crashes → evidence gate fails.
- Operator has no early warning.

**Fix:**  
Add to VPS provisioning:
```bash
# In section "4. Configure Operator Environment"
mkdir -p ~/.config
cat > ~/.config/arctura-diskwatch.sh << 'EOF'
#!/bin/bash
# Monitor disk every 10 minutes; alert if usage >80%
while true; do
  usage=$(df ~/.bittensor | tail -1 | awk '{print $5}' | sed 's/%//')
  inodes=$(df -i ~/.bittensor | tail -1 | awk '{print $5}' | sed 's/%//')
  if [ "$usage" -gt 80 ] || [ "$inodes" -gt 80 ]; then
    echo "ALERT: Disk $usage%, Inodes $inodes%" >&2
  fi
  sleep 600
done
EOF
chmod +x ~/.config/arctura-diskwatch.sh
systemctl --user enable --now arctura-diskwatch.service  # Add a timer for this
```

And log rotation:
```bash
# In systemd service files
[Service]
...
StandardOutput=journal
StandardError=journal
# Limit journal to 500 MB per service
Environment="SYSTEMD_LOG_RATE_LIMIT_INTERVAL=30s"
Environment="SYSTEMD_LOG_RATE_LIMIT_BURST=100"
```

---

### **Finding 3.3 — HIGH: No Secret Rotation Plan for Finney Launch**
**File:** `docs/MAINNET_LAUNCH_BLOCKERS.md`  
**Severity:** HIGH
**Category:** Security Risk

**Issue:**  
The launch blockers document states:
> "Owner coldkey mnemonic stored offline in at least two separate locations"

But there's **no rotation procedure** if:
1. The mnemonic is compromised.
2. The operator suspects a leak.
3. A team member leaves.

Additionally, during testnet, the operator has wallets on the VPS (as per VPS_PROVISIONING_CHECKLIST.md). If the VPS is compromised, **there's no emergency stop procedure** to:
1. Revoke testnet validators/miners.
2. Prevent the compromise from being used to register mainnet accounts.

**Impact:**
- Compromised testnet keys could be used to attack mainnet if not immediately revoked.

**Fix:**  
Add pre-mainnet security checklist:
```markdown
## Blocked Until: Key Rotation & Security Hardening

- [ ] All testnet wallets have been revoked or removed from VPS
- [ ] Mainnet owner coldkey was never copied to VPS
- [ ] SSH keys used to access VPS have been rotated post-testnet
- [ ] VPS has been factory-reset or reimaged before mainnet deployment
- [ ] Emergency revocation procedure is documented and tested
```

---

### **Finding 3.4 — MEDIUM: No Monitoring for RPC Endpoint Failures**
**File:** `arctura_base/base_rpc.py`, line 46 (`_verify_connection()`)  
**Severity:** MEDIUM
**Category:** Operational Gap

**Issue:**  
The RPC client verifies connection at startup:
```python
def _verify_connection(self) -> None:
    if not self.w3.is_connected():
        raise ConnectionError(...)
```

But there's **no runtime monitoring**. If:
1. The RPC endpoint goes down at hour 25 of 48.
2. The miner silently fails to respond (network timeout).
3. Validator scores it as 0.0 (attestation failure).
4. Health timer logs "ok": false for 5 hours.

The gate would still check box "weight_commits > 0" (true, from hour 1), and might pass if health samples are loose.

**Impact:**
- Evidence gate can't distinguish between miner fault and infrastructure fault.

**Fix:**  
Add RPC health monitoring:
```python
# In arctura_base/base_rpc.py
def get_latest_block_number(self) -> int:
    """Return the current latest block number on Base."""
    try:
        return int(self.w3.eth.block_number)
    except Exception as exc:
        bt.logging.error(f"RPC call failed: {exc}")
        raise RuntimeError(f"Base RPC unavailable: {exc}") from exc

# In neurons/miner.py, forward()
try:
    output = self.base_client.execute_mandate(...)
except RuntimeError as exc:
    bt.logging.error(f"RPC infrastructure failure: {exc}")
    # Log separately so health monitoring can alert
    synapse.base_state_hash = None
    synapse.confidence = 0.0
    return synapse
```

---

## **SECTION 4: MAINNET LAUNCH BLOCKERS — COMPLETENESS AUDIT**

The `MAINNET_LAUNCH_BLOCKERS.md` file lists 5 sections with unchecked boxes:

| Blocker | Status | Gap |
|---------|--------|-----|
| Testnet Evidence | Not met | Evidence gate must be `"ok": true` |
| Code & Review | Partially met | Gordon prompt 1 & 2 findings not yet resolved/accepted |
| Capital & Operator Controls | Not met | Wallet balances & cold storage not verified |
| Network & Community | Not met | External validator, Discord announcement, monitoring host not confirmed |
| Port/Firewall & Rollback | Not met | No documented rollback procedure for neuron services |

**Critical gap:** The blockers document **lacks a finalization step**. It states:
> "Final operator approval recorded with date, burn cost, wallet names, and command"

But there's **no mechanism to record this approval**—no git commit, no signed document, no audit trail. Recommendation:

```markdown
## Final Approval Gate

Before executing any Finney registration command, the operator MUST:

1. Create a file `MAINNET_APPROVAL.txt` with:
   ```
   Date: YYYY-MM-DD HH:MM UTC
   Burn cost: <value> TAO (checked within 30 min of this time)
   Owner coldkey: <name>
   Validator wallet: <name>
   Miner wallet: <name>
   Evidence gate: reports/mainnet-evidence/report.json contains "ok": true
   All blockers: [x] satisfied
   ```

2. Commit with: `git commit --signoff -m "MAINNET APPROVAL: <date>"`

3. Only then run: `btcli subnet create --wallet.name owner --subtensor.network finney --confirm`
```

---

## **SUMMARY TABLE: Audit Findings**

| ID | Severity | Category | Issue | File:Line | Fix Complexity |
|----|----------|----------|-------|-----------|---|
| 1.1 | CRITICAL | Gaming | Permit-based miner exclusion | `validator.py:153` | Medium |
| 1.2 | HIGH | Latency Spoofing | Block deadline allows late responses | `validator.py:206` | Medium |
| 1.3 | HIGH | Calibration | Confidence window exploitable | `validator.py:181` | High |
| 1.4 | HIGH | Sybil Detection | Collision threshold too high | `incentive.py:236` | Low |
| 1.5 | MEDIUM | Incentive | Energy tag self-declared | `utils.py:94` | Low |
| 2.1 | CRITICAL | Gate | Restarts not bounded to window | `evidence_collect.py:32` | High |
| 2.2 | HIGH | Gate | Health samples pre-date window | `evidence.py:82` | Medium |
| 2.3 | MEDIUM | Gate | Weight commits not validated | `evidence.py:82` | Medium |
| 2.4 | MEDIUM | Gate | Fatal markers incomplete | `evidence.py:10` | Low |
| 3.1 | CRITICAL | Deployment | Miner port conflicts undetected | `miner.py:35` | Low |
| 3.2 | HIGH | Operational | Disk & inode monitoring missing | `VPS_PROVISIONING_CHECKLIST.md` | Medium |
| 3.3 | HIGH | Security | No key rotation plan | `MAINNET_LAUNCH_BLOCKERS.md` | Medium |
| 3.4 | MEDIUM | Monitoring | RPC failures not monitored | `base_rpc.py:46` | Low |

---

## **RECOMMENDATIONS FOR MAINNET READINESS**

1. **Immediate (before any testnet evidence run):**
   - Fix Finding 1.1 (permit exclusion), 1.3 (calibration window), 2.1 (restart window).
   - Implement port conflict check (3.1).

2. **Before evidence collection:**
   - Tighten health sample minimum and record restart count at window start (2.1, 2.2).
   - Add disk monitoring and log rotation (3.2).

3. **Before Finney launch:**
   - Implement RPC health monitoring (3.4).
   - Add key rotation & emergency revocation procedures (3.3).
   - Document final approval gate with git commit (MAINNET_LAUNCH_BLOCKERS.md).

4. **Post-launch monitoring:**
   - Monitor for hash collisions > threshold 2 (1.4).
   - Verify energy tag attestation integrates Stewardship Index API (1.5, Phase 03).

---

**Audit complete.** These findings must be resolved or explicitly accepted before mainnet spend. The adversarial scoring and evidence-gate gaps are the highest-risk items for the 48-hour gate.

---

## Codex Update — Gordon AI Findings / Handoff, 2026-08-24

Current source is ahead of the branch originally audited by Gordon. Treat the
triage notes at the top of this file and `docs/MAINNET_READINESS_TRACKER.md` as
the current status map.

### Current launch status

- Mainnet is not live.
- No Finney registration, staking, wallet mutation, AWS apply, or Docker launch
  has been performed by Codex.
- The current blocker is evidence, not source-control mechanics:
  `arctura-collect-evidence` must return `ok: true` after the uninterrupted
  48-hour window.
- Current required evidence remains: at least 48 elapsed hours, zero miner and
  validator restarts, no fatal markers, at least one miner attestation, at least
  570 passing health samples, and at least two validator weight commits.

### Latest repo-side issue findings

- Issue #1 launch-critical coverage has been tightened locally. Focused tests
  now exercise branch coverage for deterministic output hashing, proof
  rejection paths, payload schema/context validation, Base RPC connection/error
  paths, token balance calls, event serialization, view calls, mandate
  dispatch, miner runtime safety branches, validator mandate/scoring branches,
  and weight-setting preflight/result handling. The launch coverage gate now
  reports 100% for all required modules: `arctura_base/utils.py`,
  `arctura_base/incentive.py`, `arctura_base/payload_validation.py`,
  `arctura_base/base_rpc.py`, `neurons/miner.py`, and `neurons/validator.py`.
- Issue #4 still needs external AWS proof before closure. Terraform ASG,
  CloudWatch alarms, and the CloudWatch-to-Alertmanager bridge exist under
  `deploy/aws/asg/`, but production closure still requires operator-approved
  `terraform plan`, `terraform apply`, ASG in-service capacity, and alarm
  delivery evidence.
- Issue #6 has Prometheus/Grafana/Alertmanager artifacts, but production closure
  still requires a running monitoring target, Grafana import evidence, and a
  delivered Alertmanager test notification.
- A safe CloudWatch evidence payload renderer has been added:
  `scripts/render_cloudwatch_metrics.py` and `arctura_base/cloudwatch_metrics.py`.
  It reads an existing `runs/mainnet-evidence/report.json` and renders an AWS
  CLI `put-metric-data` JSON list for `Arctura/Launch`. It does not call AWS.
- A non-signing final approval packet generator has been added:
  `arctura-mainnet-approval` / `arctura_base/mainnet_approval.py`. It refuses to
  render if evidence is red, the Finney burn-cost snapshot is unavailable, or
  the burn-cost snapshot is older than 30 minutes.

### Safe heavy-lifting tasks for Gordon AI

These tasks are useful and bounded for Docker Desktop / Gordon AI. They must
stay read-only or local-only unless the operator explicitly authorizes external
actions.

1. Run the full local validation gate:

   ```bash
   .venv/bin/python -m pytest tests/ -q
   .venv/bin/python -m ruff check .
   .venv/bin/python -m ruff format --check .
   .venv/bin/python -m black --check arctura_base/ neurons/ tests/ deploy/aws/asg/cloudwatch_to_alertmanager.py
   .venv/bin/python -m mypy arctura_base neurons scripts tests deploy/aws/asg/cloudwatch_to_alertmanager.py
   git diff --check
   ```

2. Validate the AWS artifacts without applying them:

   ```bash
   cd deploy/aws/asg
   terraform fmt -check
   terraform validate
   ```

   Do not run `terraform apply`.

3. Validate monitoring config locally if Docker is available:

   ```bash
   cd deploy/monitoring
   docker compose config
   ```

   Do not run `docker compose up` unless explicitly authorized.

4. Render, inspect, and schema-check the CloudWatch metric payload from any
   existing evidence report:

   ```bash
   python scripts/render_cloudwatch_metrics.py \
     --report runs/mainnet-evidence/report.json \
     --output runs/mainnet-evidence/cloudwatch-metric-data.json
   python -m json.tool runs/mainnet-evidence/cloudwatch-metric-data.json
   ```

   Do not run `aws cloudwatch put-metric-data` unless explicitly authorized.
