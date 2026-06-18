"""Benchmark harness tests."""

from arctura_base.benchmark import BenchmarkResult, percentile


def test_percentile_interpolates():
    assert percentile([1.0, 2.0, 3.0], 50) == 2.0
    assert percentile([], 95) is None


def test_benchmark_summary_failure_rate():
    result = BenchmarkResult(
        iterations=4,
        successes=3,
        failures=1,
        rpc_calls=8,
        hashes_stable=True,
        first_hash="abc",
        latency_ms=[1.0, 2.0, 3.0],
    )
    summary = result.summary()
    assert summary["failure_rate"] == 0.25
    assert summary["rpc_calls_per_iteration"] == 2.0
    assert summary["latency_ms"]["p50"] == 2.0
