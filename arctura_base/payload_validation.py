"""Pydantic validation for BaseSubnetSynapse mandate payloads."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from arctura_base.agentkit import SUPPORTED_AGENT_ACTIONS
from arctura_base.utils import is_valid_address

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class BalancePayload(BaseModel):
    """Schema for balance query mandates."""

    address: str
    token_address: str | None = None

    @field_validator("address", "token_address")
    @classmethod
    def validate_address(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_valid_address(value):
            raise ValueError(f"Invalid EVM address: {value}")
        return value


class EventsPayload(BaseModel):
    """Schema for event-log query mandates."""

    abi: list[dict[str, Any]]
    event_name: str
    filter_args: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, value: str) -> str:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"Invalid event name: {value}")
        return value

    @field_validator("abi")
    @classmethod
    def validate_abi(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise ValueError("ABI must be a non-empty list")
        return value


class StatePayload(BaseModel):
    """Schema for contract state query mandates."""

    abi: list[dict[str, Any]]
    function_name: str
    args: list[Any] = Field(default_factory=list)

    @field_validator("function_name")
    @classmethod
    def validate_function_name(cls, value: str) -> str:
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError(f"Invalid function name: {value}")
        return value

    @field_validator("abi")
    @classmethod
    def validate_abi(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise ValueError("ABI must be a non-empty list")
        return value


class AgentActionPayload(BaseModel):
    """Schema for AgentKit action mandates."""

    action_type: str
    action_args: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, value: str) -> str:
        if value not in SUPPORTED_AGENT_ACTIONS:
            raise ValueError(f"Unknown action_type: {value}")
        return value


PAYLOAD_SCHEMAS: dict[str, type[BaseModel]] = {
    "balance": BalancePayload,
    "events": EventsPayload,
    "state": StatePayload,
    "agent_action": AgentActionPayload,
}


def normalize_block_range(
    block_range: tuple[int, int],
    *,
    latest_block: int,
) -> tuple[int, int]:
    """Normalize a Base block range against the current latest block.

    `(0, 0)` means "latest block" for single-block mandates. `(start, 0)` means
    "single explicit start block". All other ranges are inclusive.
    """
    if len(block_range) != 2:
        raise ValueError("base_block_range must contain exactly two block numbers")
    start, end = block_range
    if not isinstance(start, int) or not isinstance(end, int):
        raise ValueError("base_block_range values must be integers")
    if start < 0 or end < 0:
        raise ValueError("base_block_range values must be non-negative")
    if latest_block < 0:
        raise ValueError("latest_block must be non-negative")

    if start == 0 and end == 0:
        return latest_block, latest_block
    if end == 0:
        end = start
    if start > end:
        raise ValueError("base_block_range start must be <= end")
    if end > latest_block:
        raise ValueError("base_block_range cannot target future Base blocks")
    return start, end


def validate_mandate_context(
    *,
    query_type: str,
    block_range: tuple[int, int],
    contract_address: str | None,
    latest_block: int,
    max_block_lookback: int,
    allow_agent_actions: bool = False,
) -> tuple[bool, str | None]:
    """Validate mandate fields that depend on chain context and miner policy."""
    if query_type == "agent_action" and not allow_agent_actions:
        return False, "agent_action mandates are disabled by default"
    if max_block_lookback <= 0:
        return False, "max_block_lookback must be positive"
    try:
        start, end = normalize_block_range(block_range, latest_block=latest_block)
    except ValueError as exc:
        return False, str(exc)

    if latest_block - start > max_block_lookback:
        return False, "base_block_range exceeds max_block_lookback"
    if query_type == "events" and block_range == (0, 0):
        return False, "events query requires an explicit bounded base_block_range"
    if query_type in {"events", "state"}:
        if not contract_address:
            return False, f"contract_address required for {query_type} query"
        if not is_valid_address(contract_address):
            return False, f"Invalid contract_address: {contract_address}"
    if query_type == "balance" and contract_address is not None:
        return False, "contract_address must be omitted for balance query"

    _ = end
    return True, None


def validate_mandate_payload(query_type: str, payload: Any) -> tuple[bool, str | None]:
    """Validate a mandate payload for its query type."""
    schema = PAYLOAD_SCHEMAS.get(query_type)
    if schema is None:
        return False, f"Unknown query_type: {query_type}"
    if not isinstance(payload, dict):
        return False, f"Payload must be a dict, got {type(payload).__name__}"
    try:
        schema(**payload)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        return False, f"Payload validation failed: {details}"
    return True, None


def validate_and_raise(query_type: str, payload: Any) -> None:
    """Raise ValueError when a mandate payload is invalid."""
    is_valid, error = validate_mandate_payload(query_type, payload)
    if not is_valid:
        raise ValueError(error or f"Invalid payload for query_type={query_type}")
