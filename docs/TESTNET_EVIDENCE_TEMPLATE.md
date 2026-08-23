# Testnet Evidence Template

Use `scripts/create_testnet_evidence_template.py` **before** an authorized local testnet run to create a blank, machine-readable record. The generated JSON has no observed result fields populated and must not be published as proof of a successful testnet or mainnet run.

```bash
python scripts/create_testnet_evidence_template.py \
  --output artifacts/netuid-505-run.json \
  --network test \
  --netuid 505 \
  --run-id operator-supplied-id
```

After the run, an authorized operator may complete the record with the UTC-bounded method, source revision, observations, limitations, and an immutable log, artifact hash, or network reference where available.

## Boundary

This tool does not connect to Bittensor, use a wallet, submit weights, register a node, stake funds, or create a success assertion. It only creates a non-overwriting template for a real run to document later.
