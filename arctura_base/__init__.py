"""
arctura_base — Base × Bittensor subnet protocol package.

The first open-source Bittensor subnet bridging Base blockchain intelligence
into the decentralized AI network.

    Base Mainnet ──▶ arctura-base-subnet ──▶ TAO Emissions

Exports:
    BaseSubnetSynapse   — mandate + attestation protocol object
    score_response      — Resonance BFT scoring function
    normalize_weights   — Yuma Consensus weight normalizer
    apply_stewardship   — P5 carbon-aware weight modifier
    build_merkle_proof  — Merkle proof construction
    verify_merkle_proof — Merkle proof verification
    get_energy_tag      — P5 Stewardship energy tag resolver

Arctura Council · Coreweaver · arctura.network/base
Apache-2.0
"""

__version__ = "0.1.0"
__author__ = "Arctura Collective"
__license__ = "Apache-2.0"

__all__ = [
    "BaseSubnetSynapse",
    "score_response",
    "normalize_weights",
    "apply_stewardship",
    "build_merkle_proof",
    "verify_merkle_proof",
    "get_energy_tag",
]


def __getattr__(name: str):
    """Lazily expose package helpers without importing bittensor during CLI startup."""
    if name == "BaseSubnetSynapse":
        from arctura_base.protocol import BaseSubnetSynapse

        return BaseSubnetSynapse
    if name in {"score_response", "normalize_weights"}:
        from arctura_base import incentive

        return getattr(incentive, name)
    if name == "apply_stewardship":
        from arctura_base.incentive import apply_stewardship_modifier

        return apply_stewardship_modifier
    if name in {"build_merkle_proof", "verify_merkle_proof", "get_energy_tag"}:
        from arctura_base import utils

        return getattr(utils, name)
    raise AttributeError(f"module 'arctura_base' has no attribute {name!r}")
