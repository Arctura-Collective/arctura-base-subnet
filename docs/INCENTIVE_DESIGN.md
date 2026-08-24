# Incentive Design — Resonance BFT Scoring

## Overview

Validators score miners on four dimensions. Scores determine Yuma Consensus
weights, which determine TAO emission distribution.

## Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Attestation validity | 40% | Merkle proof valid + block_hash_anchor matches |
| Execution completeness | 30% | execution_trace covers all required steps |
| Response latency | 20% | Response within deadline_block |
| Confidence calibration | 10% | Warmed-up, variance-penalized historical accuracy of self-reported confidence |

## Anti-Gaming Properties

| Attack | Mitigation |
|--------|-----------|
| Fabricated state hash | Merkle proof verification fails → 0.0 |
| Stale attestation | block_hash_anchor mismatch → 0.0 |
| Pre-computed proof | block_hash_anchor tied to a block that must exist at query time |
| Oversized or malformed Base RPC mandate | Miner validates block ranges against latest Base height and `max_block_lookback` before execution |
| Unbounded event-log scan | Event queries require an explicit bounded Base block range |
| Incomplete execution | Completeness scoring penalizes missing trace steps |
| Sybil triads or larger (identical hashes) | Hash collision detection flags three-or-more UIDs sharing a hash in one tempo → 75% score penalty |
| New or thin-history miner | No calibration bonus until enough observations exist |
| Overconfident or drifting miner | Calibration tracking penalizes consistent miscalibration and unstable confidence history |

## P5 Stewardship Modifier

| Energy Tag | Modifier |
|-----------|---------|
| `renewable_verified` | ×1.15 (+15%) |
| `renewable_claimed` | ×1.05 (+5%) |
| `unknown` | ×1.00 (no change) |
| `high_carbon` | ×0.90 (-10%) |

Miners still declare `ARCTURA_ENERGY_TAG`, but validators apply the modifier only
when a validator-owned verification file confirms the miner hotkey and claimed
tag. Set `ARCTURA_STEWARDSHIP_VERIFICATION_FILE` or pass
`--stewardship-verification-file` to the validator. Use
`deploy/stewardship/verification.example.json` as the template.

## Validator Economics

Validators earn TAO proportional to stake weight × Yuma Consensus alignment.
Validators who consistently set weights aligned with network consensus earn
more than outliers. Missing a tempo period = zero earnings for that period.
