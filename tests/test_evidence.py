"""Tests for bounded local-testnet evidence template generation."""

import json

import pytest

from arctura_base.evidence import build_testnet_evidence_template, write_testnet_evidence_template


def test_template_records_scope_without_claiming_an_outcome():
    template = build_testnet_evidence_template(network="test", netuid=505, run_id="run-505-a")

    assert template["publication_state"] == "template"
    assert template["run"]["network"] == "test"
    assert template["run"]["netuid"] == 505
    assert template["run"]["id"] == "run-505-a"
    assert all(value is None for value in template["observations"].values())
    assert "not evidence" in template["claim_boundary"]


def test_template_writer_refuses_to_overwrite_an_existing_artifact(tmp_path):
    output = tmp_path / "evidence.json"
    write_testnet_evidence_template(output, network="test", netuid=505)

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["run"]["netuid"] == 505

    with pytest.raises(FileExistsError):
        write_testnet_evidence_template(output, network="test", netuid=505)
