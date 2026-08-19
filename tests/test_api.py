from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from listmonk_mcp.api import ListmonkClient


def make_client(handler) -> ListmonkClient:
    return ListmonkClient(
        "https://listmonk.example.com",
        "api-user",
        "secret-token",
        transport=httpx.MockTransport(handler),
    )


def json_response(payload, status=200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def test_list_campaigns_sends_filters_and_basic_auth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/campaigns"
        assert request.url.params["query"] == "weekly"
        assert request.url.params["status"] == "draft"
        assert request.url.params["per_page"] == "5"
        assert request.url.params["page"] == "2"
        assert request.headers["authorization"].startswith("Basic ")
        return json_response({"data": {"results": []}})

    client = make_client(handler)
    assert client.list_campaigns("weekly", "draft", 5, 2)["data"]["results"] == []


def test_list_campaigns_supports_documented_all_page_size() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "all"
        return json_response({"data": {"results": []}})

    client = make_client(handler)
    assert client.list_campaigns(limit="all")["data"]["results"] == []


def test_create_draft_uses_only_expected_campaign_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        payload = json.loads(request.content)
        assert payload == {
            "name": "Weekly",
            "subject": "News",
            "body": "<h1>Hello</h1>",
            "lists": [2],
            "from_email": "News <news@example.com>",
            "template_id": 3,
            "content_type": "html",
            "messenger": "email",
            "type": "regular",
        }
        return json_response({"data": {"id": 42, "status": "draft"}})

    client = make_client(handler)
    result = client.create_draft(
        "Weekly", "News", "<h1>Hello</h1>", [2], "News <news@example.com>", 3
    )
    assert result["data"]["id"] == 42


def test_update_refuses_non_draft_campaign() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"data": {"id": 9, "status": "running"}})

    client = make_client(handler)
    with pytest.raises(ValueError, match="not 'draft'"):
        client.update_draft(9, "Weekly", "News", "Body", [1], "a@example.com", 1)


def test_exact_html_replacement_preserves_campaign_and_verifies_storage() -> None:
    html = b"<!doctype html>\n<p>Hello</p>\n"
    digest = hashlib.sha256(html).hexdigest()
    requests: list[httpx.Request] = []
    campaign = {
        "id": 9,
        "status": "draft",
        "name": "Weekly",
        "subject": "News",
        "body": "old",
        "lists": [{"id": 3}],
        "from_email": "news@example.com",
        "template_id": 1,
        "content_type": "html",
        "messenger": "email",
        "type": "regular",
        "send_at": "2026-08-21T14:00:00-07:00",
        "tags": ["weekly"],
        "headers": [{"X-Test": "yes"}],
        "attribs": {"edition": 9},
        "altbody": "Hello",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "PUT":
            payload = json.loads(request.content)
            assert payload["body"].encode() == html
            assert payload["lists"] == [3]
            assert payload["send_at"] == campaign["send_at"]
            assert payload["tags"] == ["weekly"]
            return json_response({"data": True})
        stored = {**campaign, "body": html.decode() if len(requests) > 2 else "old"}
        return json_response({"data": stored})

    client = make_client(handler)
    result = client.replace_campaign_html(9, html, digest)
    assert result["data"]["body"].encode() == html
    assert result["integrity"] == {
        "sha256": digest,
        "byte_length": len(html),
        "verified": True,
    }
    assert [request.method for request in requests] == ["GET", "PUT", "GET"]


@pytest.mark.parametrize(
    ("content", "digest", "message"),
    [
        (b"hello", "not-a-digest", "64-character"),
        (b"hello", "0" * 64, "SHA-256 mismatch"),
        (b"\xff", hashlib.sha256(b"\xff").hexdigest(), "valid UTF-8"),
        (b"", hashlib.sha256(b"").hexdigest(), "must not be empty"),
    ],
)
def test_exact_html_replacement_validates_content_before_http(
    content: bytes, digest: str, message: str
) -> None:
    client = make_client(lambda request: pytest.fail("HTTP request should not be made"))
    with pytest.raises(ValueError, match=message):
        client.replace_campaign_html(9, content, digest)


@pytest.mark.parametrize(
    ("campaign", "message"),
    [
        ({"status": "running", "content_type": "html"}, "only draft or scheduled"),
        ({"status": "draft", "content_type": "visual"}, "content_type='html'"),
    ],
)
def test_exact_html_replacement_rejects_unsafe_campaign_types(
    campaign: dict, message: str
) -> None:
    html = b"<p>Hello</p>"
    client = make_client(lambda request: json_response({"data": campaign}))
    with pytest.raises(ValueError, match=message):
        client.replace_campaign_html(9, html, hashlib.sha256(html).hexdigest())


def test_scheduled_html_replacement_requires_both_safety_gates() -> None:
    html = b"<p>Hello</p>"
    digest = hashlib.sha256(html).hexdigest()
    campaign = {"status": "scheduled", "content_type": "html"}
    disabled = make_client(lambda request: json_response({"data": campaign}))
    with pytest.raises(ValueError, match="confirm=true"):
        disabled.replace_campaign_html(9, html, digest)
    with pytest.raises(PermissionError, match="LISTMONK_ENABLE_SENSITIVE_TOOLS"):
        disabled.replace_campaign_html(9, html, digest, confirm=True)


def test_exact_html_replacement_detects_storage_mismatch() -> None:
    html = b"<p>Hello</p>"
    digest = hashlib.sha256(html).hexdigest()
    campaign = {
        "status": "draft",
        "content_type": "html",
        "name": "Weekly",
        "subject": "News",
        "body": "changed",
        "lists": [3],
    }
    client = make_client(lambda request: json_response({"data": campaign}))
    with pytest.raises(RuntimeError, match="failed verification"):
        client.replace_campaign_html(9, html, digest)


def test_send_test_rejects_an_empty_recipient_list() -> None:
    client = ListmonkClient(
        "https://listmonk.example.com",
        "api-user",
        "secret-token",
        transport=httpx.MockTransport(lambda request: pytest.fail("HTTP request should not be made")),
        allow_sensitive=True,
    )
    with pytest.raises(ValueError, match="at least one"):
        client.send_test(1, ["", "  "], confirm=True)


def test_send_test_requires_confirmation_and_server_opt_in() -> None:
    client = make_client(lambda request: pytest.fail("HTTP request should not be made"))
    with pytest.raises(ValueError, match="confirm=true"):
        client.send_test(1, ["a@example.com"])
    with pytest.raises(PermissionError, match="LISTMONK_ENABLE_SENSITIVE_TOOLS"):
        client.send_test(1, ["a@example.com"], confirm=True)


def test_send_test_rejects_an_invalid_recipient() -> None:
    client = ListmonkClient(
        "https://listmonk.example.com",
        "api-user",
        "secret-token",
        transport=httpx.MockTransport(lambda request: pytest.fail("HTTP request should not be made")),
        allow_sensitive=True,
    )
    with pytest.raises(ValueError, match="invalid test email address"):
        client.send_test(1, ["not-an-email"], confirm=True)


def test_schedule_checks_draft_then_updates_time_then_status() -> None:
    requests: list[httpx.Request] = []
    campaign = {
        "id": 7,
        "status": "draft",
        "name": "Weekly",
        "subject": "News",
        "body": "Body",
        "lists": [{"id": 2, "name": "Members"}],
        "from_email": "news@example.com",
        "template_id": 1,
        "content_type": "html",
        "messenger": "email",
        "type": "regular",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return json_response({"data": campaign})
        if request.url.path.endswith("/status"):
            assert json.loads(request.content) == {"status": "scheduled"}
            return json_response({"data": {**campaign, "status": "scheduled"}})
        payload = json.loads(request.content)
        assert payload["send_at"] == "2026-08-22T09:00:00-07:00"
        assert payload["lists"] == [2]
        return json_response({"data": campaign})

    client = make_client(handler)
    result = client.schedule(7, "2026-08-22T09:00:00-07:00")
    assert result["data"]["status"] == "scheduled"
    assert [(r.method, r.url.path) for r in requests] == [
        ("GET", "/api/campaigns/7"),
        ("PUT", "/api/campaigns/7"),
        ("PUT", "/api/campaigns/7/status"),
    ]


def test_http_errors_are_not_hidden() -> None:
    client = make_client(lambda request: json_response({"message": "forbidden"}, 403))
    with pytest.raises(
        httpx.HTTPStatusError,
        match="Listmonk API returned 403 Forbidden: forbidden",
    ):
        client.get_campaign(1)


def test_non_json_http_error_detail_is_preserved_and_bounded() -> None:
    client = make_client(
        lambda request: httpx.Response(
            400,
            text="invalid campaign " + ("x" * 3000),
            request=request,
        )
    )
    with pytest.raises(httpx.HTTPStatusError) as caught:
        client.get_campaign(1)
    assert "invalid campaign" in str(caught.value)
    assert len(str(caught.value)) < 2100


def test_non_object_json_http_error_detail_is_preserved() -> None:
    client = make_client(lambda request: json_response(["invalid campaign"], 400))
    with pytest.raises(httpx.HTTPStatusError, match=r'\["invalid campaign"\]'):
        client.get_campaign(1)
