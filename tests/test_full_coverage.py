from __future__ import annotations

import base64
import json
import runpy
import warnings
from typing import Any

import httpx
import pytest
from mcp.server import MCPServer

from listmonk_mcp.api import ListmonkClient
from listmonk_mcp.endpoints import ENDPOINTS
from listmonk_mcp import server


def make_client(handler, *, allow_sensitive: bool = False) -> ListmonkClient:
    return ListmonkClient(
        "https://listmonk.example.com",
        "api-user",
        "secret-token",
        transport=httpx.MockTransport(handler),
        allow_sensitive=allow_sensitive,
    )


def response(payload: Any = None, *, text: str | None = None) -> httpx.Response:
    if text is not None:
        return httpx.Response(200, text=text, headers={"content-type": "text/html"})
    return httpx.Response(200, json=payload if payload is not None else {"data": True})


@pytest.mark.parametrize(
    ("url", "username", "token", "message"),
    [
        ("listmonk.example.com", "user", "token", "http"),
        ("https://listmonk.example.com", "", "token", "required"),
        ("https://listmonk.example.com", "user", "", "required"),
    ],
)
def test_client_rejects_invalid_configuration(
    url: str, username: str, token: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ListmonkClient(url, username, token)


def test_client_close_and_text_response() -> None:
    client = make_client(lambda request: response(text="<p>preview</p>"))
    assert client.preview(1) == "<p>preview</p>"
    client.close()


@pytest.mark.parametrize("limit", [0, 101])
def test_campaign_list_limit_validation(limit: int) -> None:
    client = make_client(lambda request: pytest.fail("HTTP should not occur"))
    with pytest.raises(ValueError, match="between 1 and 100"):
        client.list_campaigns(limit=limit)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": " "}, "name, subject, and body"),
        ({"list_ids": []}, "positive list ID"),
        ({"list_ids": [0]}, "positive list ID"),
        ({"template_id": 0}, "template_id"),
        ({"content_type": "binary"}, "unsupported content_type"),
    ],
)
def test_campaign_payload_validation(overrides: dict[str, Any], message: str) -> None:
    values: dict[str, Any] = {
        "name": "Weekly",
        "subject": "News",
        "body": "Body",
        "list_ids": [1],
        "from_email": "news@example.com",
        "template_id": 1,
        "content_type": "html",
    }
    values.update(overrides)
    with pytest.raises(ValueError, match=message):
        ListmonkClient._campaign_payload(**values)


def test_update_preview_send_and_raw_draft_response() -> None:
    requests: list[httpx.Request] = []
    campaign = {
        "id": 3,
        "status": "draft",
        "name": "Old",
        "subject": "Old",
        "body": "Old",
        "lists": [1],
        "content_type": "html",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET" and request.url.path == "/api/campaigns/3":
            return response(campaign)  # Exercises responses without a data envelope.
        if request.url.path.endswith("/preview"):
            return response(text="preview")
        return response()

    client = make_client(handler)
    assert client.update_draft(3, "New", "Subject", "Body", [1], "n@example.com", 1)[
        "data"
    ]
    assert client.preview(3) == "preview"
    assert client.send_test(3, [" a@example.com ", ""])["data"]
    assert [item.method for item in requests] == ["GET", "PUT", "GET", "POST"]


def test_schedule_rejects_invalid_timestamp() -> None:
    client = make_client(
        lambda request: response({"data": {"id": 1, "status": "draft"}})
    )
    with pytest.raises(ValueError, match="ISO-8601"):
        client.schedule(1, "not-a-time")


def test_transactional_attachment_validation() -> None:
    client = make_client(lambda request: pytest.fail("HTTP should not occur"), allow_sensitive=True)
    with pytest.raises(ValueError, match="at least one attachment"):
        client.send_transactional_attachments({}, [], confirm=True)
    for filename in ("", "../secret", "folder/file", "folder\\file"):
        with pytest.raises(ValueError, match="basename"):
            client.send_transactional_attachments({}, [(filename, b"x")], confirm=True)


def test_server_client_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, url, user, token, *, allow_sensitive=False):
            captured.update(
                url=url, user=user, token=token, allow_sensitive=allow_sensitive
            )

    monkeypatch.setattr(server, "ListmonkClient", FakeClient)
    monkeypatch.setenv("LISTMONK_URL", "https://example.com")
    monkeypatch.setenv("LISTMONK_USER", "user")
    monkeypatch.setenv("LISTMONK_TOKEN", "token")
    monkeypatch.setenv("LISTMONK_ENABLE_SENSITIVE_TOOLS", "YES")
    assert isinstance(server._client(), FakeClient)
    assert captured == {
        "url": "https://example.com",
        "user": "user",
        "token": "token",
        "allow_sensitive": True,
    }


def test_server_call_always_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        closed = False

        def success(self, value):
            return value

        def failure(self):
            raise RuntimeError("boom")

        def close(self):
            self.closed = True

    first = FakeClient()
    monkeypatch.setattr(server, "_client", lambda: first)
    assert server._call("success", 42) == 42
    assert first.closed

    second = FakeClient()
    monkeypatch.setattr(server, "_client", lambda: second)
    with pytest.raises(RuntimeError, match="boom"):
        server._call("failure")
    assert second.closed


def test_high_level_server_wrappers_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def fake_call(method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, args, kwargs))
        return {"method": method}

    monkeypatch.setattr(server, "_call", fake_call)
    assert server.get_campaign(1)["method"] == "get_campaign"
    assert server.list_campaigns("q", "draft", 2)["method"] == "list_campaigns"
    assert server.create_newsletter_draft("n", "s", "b", [1], "f", 1)["method"] == "create_draft"
    assert server.update_newsletter_draft(1, "n", "s", "b", [1], "f", 1)["method"] == "update_draft"
    assert server.preview_newsletter(1) == {"method": "preview"}
    assert server.send_newsletter_test(1, ["a@example.com"])["method"] == "send_test"
    assert server.schedule_newsletter(1, "2026-01-01T00:00:00Z")["method"] == "schedule"
    assert len(calls) == 7


def test_generated_endpoint_tools_delegate_and_document_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(
        server,
        "_call",
        lambda method, *args, **kwargs: calls.append((method, args, kwargs)) or "ok",
    )
    safe_tool = server._make_endpoint_tool("api_health", ENDPOINTS["api_health"])
    sensitive_tool = server._make_endpoint_tool(
        "api_delete_campaign", ENDPOINTS["api_delete_campaign"]
    )
    assert safe_tool(query={"x": 1}) == "ok"
    assert sensitive_tool(path_params={"campaign_id": 1}, confirm=True) == "ok"
    assert safe_tool.__name__ == "api_health"
    assert "Requires confirm=true" not in (safe_tool.__doc__ or "")
    assert "Requires confirm=true" in (sensitive_tool.__doc__ or "")
    assert len(calls) == 2


def test_upload_and_import_server_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(
        server,
        "_call",
        lambda method, *args, **kwargs: calls.append((method, args, kwargs)) or {"data": True},
    )
    encoded = base64.b64encode(b"hello").decode()
    assert server.upload_media("image.png", encoded)["data"]
    assert server.import_subscribers("people.csv", encoded, [1], "blocklist", True, ";")["data"]
    params = json.loads(calls[1][2]["form"]["params"])
    assert params == {"mode": "blocklist", "lists": [1], "overwrite": True, "delim": ";"}

    with pytest.raises(ValueError, match="mode"):
        server.import_subscribers("people.csv", encoded, [1], "invalid")
    with pytest.raises(ValueError, match="positive list ID"):
        server.import_subscribers("people.csv", encoded, [])


def test_attachment_server_tool_and_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_call(method: str, *args: Any, **kwargs: Any) -> dict[str, bool]:
        captured.update(method=method, args=args, kwargs=kwargs)
        return {"data": True}

    monkeypatch.setattr(server, "_call", fake_call)
    encoded = base64.b64encode(b"document").decode()
    assert server.send_transactional_with_attachments(
        {"template_id": 2},
        [{"filename": "invoice.pdf", "content_base64": encoded}],
        confirm=True,
    )["data"]
    assert captured["args"][1] == [("invoice.pdf", b"document")]
    with pytest.raises(ValueError, match="filename and content_base64"):
        server.send_transactional_with_attachments({}, [{"filename": "missing"}])


def test_main_runs_stdio_and_module_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    transports: list[str] = []
    monkeypatch.setattr(MCPServer, "run", lambda self, transport: transports.append(transport))
    server.main()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message=".*found in sys.modules.*", category=RuntimeWarning
        )
        runpy.run_module("listmonk_mcp.server", run_name="__main__")
    assert transports == ["stdio", "stdio"]
