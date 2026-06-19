"""Benchmark harness tests."""

from unittest.mock import MagicMock

from arctura_base.benchmark import (
    BenchmarkResult,
    CountingBaseRPCClient,
    main,
    get_max_rss_kb,
    percentile,
)


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


def test_max_rss_is_numeric_on_supported_and_unsupported_platforms():
    assert isinstance(get_max_rss_kb(), int)


def test_counting_client_does_not_count_cached_block_hash_as_rpc_call():
    client = object.__new__(CountingBaseRPCClient)
    client.rpc_calls = 0
    client._block_hash_cache = {}
    client.w3 = MagicMock()
    client.w3.eth.get_block.return_value = {"hash": bytes.fromhex("22" * 32)}

    assert client.get_block_hash(21_000_000) == "22" * 32
    assert client.get_block_hash(21_000_000) == "22" * 32
    assert client.rpc_calls == 1


def test_main_writes_summary_to_output_file(monkeypatch, tmp_path, capsys):
    output_path = tmp_path / "benchmark.json"
    result = BenchmarkResult(
        iterations=1,
        successes=1,
        failures=0,
        rpc_calls=2,
        hashes_stable=True,
        first_hash="abc",
        latency_ms=[1.0],
    )

    monkeypatch.setattr("arctura_base.benchmark.run_balance_benchmark", lambda **kwargs: result)

    assert main(["--iterations", "1", "--output", str(output_path)]) == 0
    assert '"successes": 1' in capsys.readouterr().out
    assert '"rpc_calls": 2' in output_path.read_text()
