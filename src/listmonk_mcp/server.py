"""MCP tool definitions for restricted Listmonk newsletter access."""

from __future__ import annotations

import os
import base64
import json
from typing import Any

from mcp.server import MCPServer

from .api import ListmonkClient
from .endpoints import ENDPOINTS, Endpoint


mcp = MCPServer(
    "listmonk-newsletter",
    instructions=(
        "Manage Listmonk newsletter campaigns. Creating and updating never implies "
        "permission to schedule. Only call schedule_newsletter when the user explicitly "
        "requests scheduling for that campaign and time."
    ),
)


def _client() -> ListmonkClient:
    allow_sensitive = os.environ.get("LISTMONK_ENABLE_SENSITIVE_TOOLS", "false").lower()
    return ListmonkClient(
        os.environ["LISTMONK_URL"],
        os.environ["LISTMONK_USER"],
        os.environ["LISTMONK_TOKEN"],
        allow_sensitive=allow_sensitive in {"1", "true", "yes", "on"},
    )


def _call(method: str, *args: Any, **kwargs: Any) -> Any:
    client = _client()
    try:
        return getattr(client, method)(*args, **kwargs)
    finally:
        client.close()


@mcp.tool()
def get_campaign(campaign_id: int) -> dict[str, Any]:
    """Get one campaign and its current status."""
    return _call("get_campaign", campaign_id)


@mcp.tool()
def list_campaigns(query: str = "", status: str = "", limit: int = 20) -> dict[str, Any]:
    """List recent campaigns, optionally filtered by query or status."""
    return _call("list_campaigns", query, status, limit)


@mcp.tool()
def create_newsletter_draft(
    name: str,
    subject: str,
    body: str,
    list_ids: list[int],
    from_email: str,
    template_id: int,
    content_type: str = "html",
) -> dict[str, Any]:
    """Create a draft only. This never sends or schedules the campaign."""
    return _call(
        "create_draft", name, subject, body, list_ids, from_email, template_id, content_type
    )


@mcp.tool()
def update_newsletter_draft(
    campaign_id: int,
    name: str,
    subject: str,
    body: str,
    list_ids: list[int],
    from_email: str,
    template_id: int,
    content_type: str = "html",
) -> dict[str, Any]:
    """Update a campaign only if it is still a draft."""
    return _call(
        "update_draft",
        campaign_id,
        name,
        subject,
        body,
        list_ids,
        from_email,
        template_id,
        content_type,
    )


@mcp.tool()
def preview_newsletter(campaign_id: int) -> str:
    """Render and return a campaign preview."""
    return _call("preview", campaign_id)


@mcp.tool()
def send_newsletter_test(campaign_id: int, email_addresses: list[str]) -> dict[str, Any]:
    """Send a test to explicit email addresses, never to campaign lists."""
    return _call("send_test", campaign_id, email_addresses)


@mcp.tool()
def schedule_newsletter(campaign_id: int, send_at: str) -> dict[str, Any]:
    """Schedule a draft for real delivery at an explicit ISO-8601 timestamp."""
    return _call("schedule", campaign_id, send_at)


def _make_endpoint_tool(endpoint_name: str, endpoint: Endpoint):
    def endpoint_tool(
        path_params: dict[str, str | int] | None = None,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        confirm: bool = False,
    ) -> Any:
        return _call(
            "call_endpoint",
            endpoint_name,
            path_params=path_params,
            query=query,
            body=body,
            confirm=confirm,
        )

    endpoint_tool.__name__ = endpoint_name
    endpoint_tool.__qualname__ = endpoint_name
    warning = " Requires confirm=true." if endpoint.confirmation_required else ""
    endpoint_tool.__doc__ = (
        f"{endpoint.description} {endpoint.method} {endpoint.path}.{warning} "
        "Use path_params for placeholders, query for URL parameters, and body for JSON."
    )
    return endpoint_tool


for _endpoint_name, _endpoint in ENDPOINTS.items():
    mcp.tool()(_make_endpoint_tool(_endpoint_name, _endpoint))


@mcp.tool()
def upload_media(filename: str, content_base64: str) -> Any:
    """Upload media from base64 content without reading arbitrary host files."""
    return _call(
        "upload_file",
        "/api/media",
        filename=filename,
        content=base64.b64decode(content_base64, validate=True),
    )


@mcp.tool()
def import_subscribers(
    filename: str,
    content_base64: str,
    list_ids: list[int],
    mode: str = "subscribe",
    overwrite: bool = False,
    delimiter: str = ",",
) -> Any:
    """Upload a CSV/ZIP subscriber import from base64 content."""
    if mode not in {"subscribe", "blocklist"}:
        raise ValueError("mode must be 'subscribe' or 'blocklist'")
    if not list_ids or any(value <= 0 for value in list_ids):
        raise ValueError("at least one positive list ID is required")
    params = {
        "mode": mode,
        "lists": list_ids,
        "overwrite": overwrite,
        "delim": delimiter,
    }
    return _call(
        "upload_file",
        "/api/import/subscribers",
        filename=filename,
        content=base64.b64decode(content_base64, validate=True),
        form={"params": json.dumps(params)},
    )


@mcp.tool()
def send_transactional_with_attachments(
    payload: dict[str, Any],
    attachments: list[dict[str, str]],
    confirm: bool = False,
) -> Any:
    """Send transactional mail with base64 attachments. Requires both sensitive-tools opt-in and confirm=true."""
    decoded: list[tuple[str, bytes]] = []
    for attachment in attachments:
        try:
            filename = attachment["filename"]
            content = base64.b64decode(attachment["content_base64"], validate=True)
        except KeyError as exc:
            raise ValueError("each attachment needs filename and content_base64") from exc
        decoded.append((filename, content))
    return _call(
        "send_transactional_attachments",
        payload,
        decoded,
        confirm=confirm,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
