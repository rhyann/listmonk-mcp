from __future__ import annotations

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


def test_send_test_rejects_an_empty_recipient_list() -> None:
    client = make_client(lambda request: pytest.fail("HTTP request should not be made"))
    with pytest.raises(ValueError, match="at least one"):
        client.send_test(1, ["", "  "])


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
    with pytest.raises(httpx.HTTPStatusError):
        client.get_campaign(1)
