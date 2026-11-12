import json
from pathlib import Path

import pytest
from agentbench.schemas import Budget, DatasetFile, checksum
from agentbench.services.datasets import export_format, parse_import
from pydantic import ValidationError


def suite():
    return DatasetFile.model_validate_json(Path("datasets/financial-research/v1.json").read_text())


def test_curated_suites_are_frozen_by_manifest():
    manifest = json.loads(Path("datasets/manifest.json").read_text())
    total = 0
    for name, item in manifest.items():
        payload = DatasetFile.model_validate_json(Path(f"datasets/{name}/v1.json").read_text())
        assert len(payload.cases) >= 30
        assert checksum(payload.model_dump(mode="json")) == item["sha256"]
        assert all(c.expected.output or c.expected.facts or c.expected.error for c in payload.cases)
        total += len(payload.cases)
    assert total >= 150


@pytest.mark.parametrize(
    "field,value",
    [("tool_calls", -1), ("timeout_seconds", 0), ("tokens", 0), ("cost_usd", -1), ("max_steps", 1000)],
)
def test_budget_validation(field, value):
    with pytest.raises(ValidationError):
        Budget.model_validate({field: value})


def test_duplicate_case_ids_rejected():
    case = suite().cases[0]
    with pytest.raises(ValidationError, match="unique"):
        DatasetFile(name="duplicate", cases=[case, case])


@pytest.mark.parametrize("format", ["json", "jsonl", "csv"])
def test_import_export_roundtrip(format):
    original = suite()
    loaded = parse_import(export_format(original, format), format)
    assert [c.model_dump() for c in loaded.cases] == [c.model_dump() for c in original.cases]


def test_helpful_jsonl_error():
    with pytest.raises(ValueError, match="JSONL line 2"):
        parse_import(suite().cases[0].model_dump_json() + "\n{broken}", "jsonl")


def test_csv_error_reports_row():
    with pytest.raises(ValueError, match="CSV row 2"):
        parse_import("id,category,input,expected\na,rag,Question,broken", "csv")


def test_checksum_is_key_order_independent():
    assert checksum({"a": 1, "b": 2}) == checksum({"b": 2, "a": 1})
    assert checksum({"a": 1}) != checksum({"a": 2})
