"""Pydantic validation for BaseSubnetSynapse mandate payloads."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

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
        valid_actions = {
            "transfer",
            "swap",
            "deploy_contract",
            "call_function",
            "read_state",
        }
        if value not in valid_actions:
            raise ValueError(f"Unknown action_type: {value}")
        return value


PAYLOAD_SCHEMAS: dict[str, type[BaseModel]] = {
    "balance": BalancePayload,
    "events": EventsPayload,
    "state": StatePayload,
    "agent_action": AgentActionPayload,
}


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
