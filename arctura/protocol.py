"""
arctura/protocol.py
Bittensor SDK v10 compatible synapse definition for Arctura Network.

Changes from v7.4.0 template:
- Pydantic v2: replaced allow_mutation=False with model_config frozen field
- Explicit type annotations throughout
- deserialize returns typed str
"""

import bittensor as bt
from pydantic import ConfigDict, Field


class ArcturaSynapse(bt.Synapse):
    """
    Base protocol synapse for the Arctura subnet.

    Validators send `prompt` to miners; miners populate `response`.
    The `prompt` field is immutable post-construction (frozen via model_config).
    """

    model_config = ConfigDict(
        frozen=False
    )  # bt.Synapse base requires False; prompt immutability enforced below

    prompt: str = Field(
        default="",
        title="Prompt",
        description="Input task sent from validator to miner. Do not mutate after construction.",
    )

    response: str = Field(
        default="",
        title="Response",
        description="Miner's output to be scored by the validator.",
    )

    def deserialize(self) -> str:
        """Return the miner response for scoring."""
        return self.response
