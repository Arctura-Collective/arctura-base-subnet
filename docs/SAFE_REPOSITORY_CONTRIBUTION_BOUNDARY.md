# Safe Repository Contribution Boundary

This document defines what can be changed and validated in source control without touching live network, wallet, treasury, or infrastructure state.

## In scope

The following work is safe to develop on an isolated branch and validate with local tests, static checks, and reviewable artifacts:

- Source code, unit tests, fixtures, developer tooling, and CI configuration.
- Testnet documentation, redacted run templates, and evidence-export tooling that does not fabricate or publish a result.
- Local health checks, metric schemas, alert-rule fixtures, and deployment plans that do not provision infrastructure.
- Deterministic validator and miner reliability improvements that use mocks or local test configuration.

## Explicitly operator-gated

The following actions require explicit operator authorization, the appropriate account or key holder, and a separate approved runbook:

- Creating or using wallets, coldkeys, hotkeys, or mnemonic material.
- Registering a subnet, registering a validator or miner, staking, transferring funds, or submitting weights to a live network.
- Finney-mainnet registration, emissions configuration, treasury distribution, dTAO liquidity, or multisig changes.
- Provisioning, altering, or paying for AWS, Prometheus, Grafana, RPC-provider, or other hosted infrastructure.
- Publishing a testnet result as an observed fact without the linked artifact, timestamp, method, and stated limitation.

## Evidence rule

Repository changes may generate **templates and tools** for a testnet record. They must not generate a synthetic success record. A published operational claim requires a dated artifact supplied by an authorized operator or an independently inspectable network reference.

## Review rule

Every contribution should be branch-scoped, pass the declared local quality gates where dependencies permit, explain its boundary in the pull request, and preserve the distinction between local testnet work and a Finney-mainnet claim.
