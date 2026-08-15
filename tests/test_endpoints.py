from __future__ import annotations

import json

import httpx
import pytest

from listmonk_mcp.api import ListmonkClient
from listmonk_mcp.endpoints import ENDPOINTS


def make_client(handler, *, allow_sensitive: bool = False) -> ListmonkClient:
    return ListmonkClient(
        "https://listmonk.example.com",
        "api-user",
        "secret-token",
        transport=httpx.MockTransport(handler),
        allow_sensitive=allow_sensitive,
    )


def test_every_registered_endpoint_has_a_unique_tool_and_valid_path() -> None:
    assert len(ENDPOINTS) >= 60
    assert len(ENDPOINTS) == len(set(ENDPOINTS))
    for name, endpoint in ENDPOINTS.items():
        assert name.startswith("api_")
        assert endpoint.method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert endpoint.path.startswith(("/api/", "/webhooks/"))
        assert endpoint.description


def test_allowlisted_endpoint_formats_path_query_and_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == "/api/subscribers/42"
        assert request.url.params["source"] == "mcp"
        assert json.loads(request.content) == {"name": "Ada"}
        return httpx.Response(200, json={"data": {"id": 42}})

    client = make_client(handler)
    response = client.call_endpoint(
        "api_patch_subscriber",
        path_params={"subscriber_id": 42},
        query={"source": "mcp"},
        body={"name": "Ada"},
    )
    assert response["data"]["id"] == 42


def test_unknown_endpoint_is_rejected_before_http() -> None:
    client = make_client(lambda request: pytest.fail("HTTP request should not occur"))
    with pytest.raises(ValueError, match="unknown endpoint"):
        client.call_endpoint("api_arbitrary_request")


def test_missing_and_injected_path_parameters_are_rejected() -> None:
    client = make_client(lambda request: pytest.fail("HTTP request should not occur"))
    with pytest.raises(ValueError, match="missing required"):
        client.call_endpoint("api_get_subscriber")
    with pytest.raises(ValueError, match="invalid path"):
        client.call_endpoint(
            "api_get_subscriber", path_params={"subscriber_id": "../settings"}
        )
    with pytest.raises(ValueError, match="unexpected path"):
        client.call_endpoint("api_health", path_params={"id": 1})


@pytest.mark.parametrize(
    "endpoint_name",
    [name for name, endpoint in ENDPOINTS.items() if endpoint.confirmation_required],
)
def test_sensitive_endpoints_require_explicit_confirmation(endpoint_name: str) -> None:
    client = make_client(
        lambda request: pytest.fail("HTTP request should not occur"), allow_sensitive=True
    )
    with pytest.raises(ValueError, match="confirm=true"):
        client.call_endpoint(endpoint_name)


def test_sensitive_endpoints_are_disabled_by_default() -> None:
    client = make_client(lambda request: pytest.fail("HTTP request should not occur"))
    with pytest.raises(PermissionError, match="LISTMONK_ENABLE_SENSITIVE_TOOLS"):
        client.call_endpoint("api_delete_campaign", path_params={"campaign_id": 1}, confirm=True)


def test_uploads_are_limited_to_documented_upload_paths() -> None:
    client = make_client(lambda request: pytest.fail("HTTP request should not occur"))
    with pytest.raises(ValueError, match="not allow-listed"):
        client.upload_file("/api/settings", filename="payload.json", content=b"{}")
    with pytest.raises(ValueError, match="basename"):
        client.upload_file("/api/media", filename="../secret", content=b"x")


@pytest.mark.parametrize("path", ["/api/media", "/api/import/subscribers"])
def test_binary_uploads_use_multipart(path: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == path
        assert "multipart/form-data" in request.headers["content-type"]
        assert b"hello" in request.content
        return httpx.Response(200, json={"data": True})

    client = make_client(handler)
    assert client.upload_file(path, filename="input.csv", content=b"hello")["data"]


def test_transactional_attachments_are_sensitive_and_multipart() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/api/tx"
        assert "multipart/form-data" in request.headers["content-type"]
        assert b"invoice.pdf" in request.content
        assert b"document" in request.content
        return httpx.Response(200, json={"data": True})

    disabled = make_client(handler)
    with pytest.raises(PermissionError):
        disabled.send_transactional_attachments(
            {"template_id": 2}, [("invoice.pdf", b"document")], confirm=True
        )

    client = make_client(handler, allow_sensitive=True)
    with pytest.raises(ValueError, match="confirm=true"):
        client.send_transactional_attachments(
            {"template_id": 2}, [("invoice.pdf", b"document")]
        )
    assert client.send_transactional_attachments(
        {"template_id": 2}, [("invoice.pdf", b"document")], confirm=True
    )["data"]
    assert len(requests) == 1
