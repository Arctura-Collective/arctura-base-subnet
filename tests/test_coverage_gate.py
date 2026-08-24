from __future__ import annotations

from arctura_base.coverage_gate import evaluate_coverage_gate


def coverage_payload() -> dict:
    return {
        "files": {
            "arctura_base/utils.py": {
                "summary": {"percent_covered": 100.0},
                "missing_lines": [],
            },
            "arctura_base/incentive.py": {
                "summary": {"percent_covered": 99.5},
                "missing_lines": [121],
            },
        }
    }


def test_coverage_gate_passes_when_all_modules_meet_threshold() -> None:
    report = evaluate_coverage_gate(
        coverage_payload(),
        modules=("arctura_base/utils.py",),
        minimum_percent=100.0,
    )

    assert report["ok"] is True
    assert report["modules"][0]["covered_percent"] == 100.0
    assert report["safety"]["on_chain_action_attempted"] is False
    assert report["safety"]["wallet_required"] is False


def test_coverage_gate_fails_below_threshold() -> None:
    report = evaluate_coverage_gate(
        coverage_payload(),
        modules=("arctura_base/incentive.py",),
        minimum_percent=100.0,
    )

    assert report["ok"] is False
    assert report["modules"][0]["missing_lines"] == [121]


def test_coverage_gate_fails_missing_module() -> None:
    report = evaluate_coverage_gate(
        coverage_payload(),
        modules=("arctura_base/base_rpc.py",),
        minimum_percent=100.0,
    )

    assert report["ok"] is False
    assert report["missing_modules"] == ["arctura_base/base_rpc.py"]
    assert report["modules"][0]["missing"] == "coverage entry missing"
