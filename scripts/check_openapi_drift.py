#!/usr/bin/env python3
"""Fail when Listmonk's current OpenAPI operations diverge from the MCP contract."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from listmonk_mcp.endpoints import ENDPOINTS, Endpoint  # noqa: E402


DEFAULT_SPEC = "https://listmonk.app/docs/swagger/collections.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
SPECIAL_OPERATIONS = {
    ("POST", "/api/media"),
    ("POST", "/api/import/subscribers"),
}
# The narrative guide documents no_body as optional. Upstream OpenAPI currently
# marks it required, so do not force that stale requirement into the MCP contract.
OPTIONAL_QUERY_OVERRIDES = {
    ("GET", "/api/templates"): {"no_body"},
}


def normalize(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def load_spec(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "listmonk-mcp-ci"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return yaml.safe_load(response.read())
    return yaml.safe_load(Path(source).read_text())


def operations(spec: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                result[(method.upper(), normalize(f"/api{path}"))] = operation
    return result


def endpoint_operations() -> dict[tuple[str, str], tuple[str, Endpoint]]:
    return {
        (endpoint.method, normalize(endpoint.path)): (name, endpoint)
        for name, endpoint in ENDPOINTS.items()
        if endpoint.path.startswith("/api/")
    }


def content_types(operation: dict[str, Any]) -> set[str]:
    return set(operation.get("requestBody", {}).get("content", {}))


def required_query(operation: dict[str, Any]) -> set[str]:
    return {
        parameter["name"]
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "query" and parameter.get("required")
    }


def path_enum_sets(operation: dict[str, Any]) -> set[frozenset[str]]:
    return {
        frozenset(parameter.get("schema", {}).get("enum", []))
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "path" and parameter.get("schema", {}).get("enum")
    }


def validate(spec: dict[str, Any]) -> list[str]:
    documented = operations(spec)
    exposed = endpoint_operations()
    errors: list[str] = []

    missing = set(documented) - set(exposed) - SPECIAL_OPERATIONS
    for method, path in sorted(missing):
        errors.append(f"missing operation: {method} {path}")

    for key in sorted(set(documented) & set(exposed)):
        operation = documented[key]
        name, endpoint = exposed[key]
        # The upstream spec incorrectly describes a form body on GET
        # /templates/{id}/preview; the narrative docs and HTTP behavior use no body.
        request_body = operation.get("requestBody", {}) if key[0] != "GET" else {}
        types = set(request_body.get("content", {}))
        expected_encoding = (
            "form" if "application/x-www-form-urlencoded" in types and "application/json" not in types else "json"
        )
        if types and endpoint.body_encoding != expected_encoding:
            errors.append(
                f"{name}: body encoding is {endpoint.body_encoding}, expected {expected_encoding}"
            )
        if request_body.get("required") and not endpoint.body_required:
            errors.append(f"{name}: OpenAPI requires a request body")
        missing_query = (
            required_query(operation)
            - set(endpoint.required_query)
            - OPTIONAL_QUERY_OVERRIDES.get(key, set())
        )
        if missing_query:
            errors.append(
                f"{name}: missing required query metadata: {', '.join(sorted(missing_query))}"
            )
        documented_enums = path_enum_sets(operation)
        registered_enums = {
            frozenset(values) for _, values in endpoint.path_enums
        }
        if documented_enums - registered_enums:
            errors.append(f"{name}: path enum metadata differs from OpenAPI")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=DEFAULT_SPEC, help="OpenAPI YAML path or URL")
    args = parser.parse_args()
    errors = validate(load_spec(args.spec))
    if errors:
        print("Listmonk OpenAPI drift detected:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Listmonk OpenAPI contract matches the MCP endpoint registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
