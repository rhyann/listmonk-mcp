"""Safe smoke tests against the pinned Listmonk container stack."""

from __future__ import annotations

import os
import time

import httpx
import pytest

from listmonk_mcp.api import ListmonkClient


pytestmark = pytest.mark.integration


def live_client() -> ListmonkClient:
    if os.environ.get("LISTMONK_INTEGRATION") != "1":
        pytest.skip("set LISTMONK_INTEGRATION=1 to run Docker integration tests")
    base_url = os.environ.get("LISTMONK_INTEGRATION_URL", "http://127.0.0.1:9000")
    deadline = time.monotonic() + 120
    while True:
        try:
            if httpx.get(f"{base_url}/health", timeout=2).is_success:
                break
        except httpx.HTTPError:
            pass
        if time.monotonic() >= deadline:
            pytest.fail("Listmonk did not become healthy within 120 seconds")
        time.sleep(1)
    return ListmonkClient(base_url, "smoke-test", "smoke-test")


def test_public_health_and_lists() -> None:
    client = live_client()
    try:
        base_url = os.environ.get(
            "LISTMONK_INTEGRATION_URL", "http://127.0.0.1:9000"
        )
        assert httpx.get(f"{base_url}/health").is_success
        assert client.call_endpoint("api_list_public_lists") is not None
    finally:
        client.close()
