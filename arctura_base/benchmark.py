"""Lightweight benchmark harness for ARCTURA Base RPC mandates."""

from __future__ import annotations

import argparse
import json
import resource
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from arctura_base.base_rpc import BaseRPCClient
from arctura_base.utils import hash_output


DEFAULT_BALANCE_ADDRESS = "0x4200000000000000000000000000000000000006"


@dataclass
class BenchmarkResult:
    iterations: int
    successes: int
    failures: int
    rpc_calls: int
    hashes_stable: bool
    first_hash: str | None
    latency_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    max_rss_kb: int = 0

    def summary(self) -> dict[str, Any]:
        latencies = self.latency_ms
        return {
            "iterations": self.iterations,
            "successes": self.successes,
            "failures": self.failures,
            "failure_rate": self.failures / self.iterations if self.iterations else 0.0,
            "rpc_calls": self.rpc_calls,
            "rpc_calls_per_iteration": self.rpc_calls / self.iterations
            if self.iterations
            else 0.0,
            "hashes_stable": self.hashes_stable,
            "first_hash": self.first_hash,
            "latency_ms": {
                "p50": percentile(latencies, 50),
                "p95": percentile(latencies, 95),
                "p99": percentile(latencies, 99),
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
            },
            "max_rss_kb": self.max_rss_kb,
            "errors": self.errors[:10],
        }


class CountingBaseRPCClient(BaseRPCClient):
    """BaseRPCClient variant that counts RPC-style method calls."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.rpc_calls = 0
        super().__init__(*args, **kwargs)

    def get_latest_block_number(self) -> int:
        self.rpc_calls += 1
        return super().get_latest_block_number()

    def get_block_hash(self, block_number: int) -> str:
        self.rpc_calls += 1
        return super().get_block_hash(block_number)

    def get_balance(self, *args: Any, **kwargs: Any) -> dict:
        self.rpc_calls += 1
        return super().get_balance(*args, **kwargs)

    def get_events(self, *args: Any, **kwargs: Any) -> dict:
        self.rpc_calls += 1
        return super().get_events(*args, **kwargs)

    def call_view(self, *args: Any, **kwargs: Any) -> dict:
        self.rpc_calls += 1
        return super().call_view(*args, **kwargs)


def percentile(values: list[float], percent: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (percent / 100)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_balance_benchmark(
    iterations: int,
    address: str = DEFAULT_BALANCE_ADDRESS,
    rpc_url: str | None = None,
    timeout: int = 10,
) -> BenchmarkResult:
    client = CountingBaseRPCClient(rpc_url=rpc_url, timeout=timeout)
    block_number = client.get_latest_block_number()
    first_hash: str | None = None
    hashes_stable = True
    result = BenchmarkResult(
        iterations=iterations,
        successes=0,
        failures=0,
        rpc_calls=0,
        hashes_stable=True,
        first_hash=None,
    )

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            output = client.execute_mandate(
                query_type="balance",
                contract_address=None,
                block_range=(block_number, block_number),
                payload={"address": address},
            )
            output_hash = hash_output(output)
            if first_hash is None:
                first_hash = output_hash
            elif output_hash != first_hash:
                hashes_stable = False
            result.successes += 1
            result.latency_ms.append((time.perf_counter() - start) * 1000)
        except Exception as exc:  # pragma: no cover - exercised during live RPC failures
            result.failures += 1
            result.errors.append(f"{type(exc).__name__}: {exc}")

    result.rpc_calls = client.rpc_calls
    result.hashes_stable = hashes_stable
    result.first_hash = first_hash
    result.max_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark ARCTURA Base RPC mandate efficiency.")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--address", default=DEFAULT_BALANCE_ADDRESS)
    parser.add_argument("--rpc-url", default=None)
    parser.add_argument("--timeout", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_balance_benchmark(
        iterations=args.iterations,
        address=args.address,
        rpc_url=args.rpc_url,
        timeout=args.timeout,
    )
    print(json.dumps(result.summary(), indent=2, sort_keys=True))
    return 0 if result.failures == 0 and result.hashes_stable else 1


if __name__ == "__main__":
    raise SystemExit(main())
