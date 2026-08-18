"""Tests for intentional OpenAPI versus narrative-guide differences."""

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_openapi_drift.py"
SPEC = importlib.util.spec_from_file_location("check_openapi_drift", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate = MODULE.validate


def operation_with_required_query(name: str) -> dict:
    return {
        "parameters": [
            {
                "in": "query",
                "name": name,
                "required": True,
                "schema": {"type": "string"},
            }
        ]
    }


def test_template_no_body_openapi_mismatch_is_intentionally_ignored() -> None:
    spec = {"paths": {"/templates": {"get": operation_with_required_query("no_body")}}}
    assert validate(spec) == []


def test_subscriber_delete_retains_required_id_metadata() -> None:
    spec = {
        "paths": {
            "/subscribers": {"delete": operation_with_required_query("id")}
        }
    }
    assert validate(spec) == []
