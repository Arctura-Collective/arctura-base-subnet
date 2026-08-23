"""Small resilience helpers around Bittensor's live runtime API."""

from __future__ import annotations

import time
from typing import Any

import bittensor as bt


def load_metagraph(
    subtensor: Any,
    netuid: int,
    *,
    attempts: int = 5,
    retry_seconds: float = 5.0,
) -> Any:
    """Load a metagraph with bounded retries for transient runtime traps."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    for attempt in range(1, attempts + 1):
        try:
            return subtensor.metagraph(netuid)
        except Exception as exc:
            if attempt == attempts:
                raise
            bt.logging.warning(
                f"Metagraph load failed ({attempt}/{attempts}): {exc}. "
                f"Retrying in {retry_seconds:g}s."
            )
            time.sleep(retry_seconds)

    raise RuntimeError("metagraph retry loop exited unexpectedly")  # pragma: no cover
