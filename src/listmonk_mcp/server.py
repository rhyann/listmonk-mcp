"""MCP tool definitions for restricted Listmonk newsletter access."""

from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer

from .api import ListmonkClient


mcp = MCPServer(
    "listmonk-newsletter",
    instructions=(
        "Manage Listmonk newsletter campaigns. Creating and updating never implies "
        "permission to schedule. Only call schedule_newsletter when the user explicitly "
        "requests scheduling for that campaign and time."
    ),
)


def _client() -> ListmonkClient:
    return ListmonkClient(
        os.environ["LISTMONK_URL"],
        os.environ["LISTMONK_USER"],
        os.environ["LISTMONK_TOKEN"],
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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

