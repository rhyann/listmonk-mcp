"""MCP tool definitions for restricted Listmonk newsletter access."""

from __future__ import annotations

import os
import base64
import inspect
import json
from typing import Any, Literal

from mcp.server import MCPServer

from .api import ListmonkClient
from .contracts import BODY_MODELS, QUERY_MODELS, dump_contract, path_model
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
def list_campaigns(
    query: str = "",
    status: str = "",
    limit: int | Literal["all"] = 20,
    page: int = 1,
) -> dict[str, Any]:
    """List recent campaigns, optionally filtered by query or status."""
    return _call("list_campaigns", query, status, limit, page)


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
    def endpoint_tool(**arguments: Any) -> Any:
        return _call(
            "call_endpoint",
            endpoint_name,
            path_params=dump_contract(arguments.get("path_params")),
            query=dump_contract(arguments.get("query")),
            body=dump_contract(arguments.get("body")),
            confirm=arguments.get("confirm", False),
        )

    endpoint_tool.__name__ = endpoint_name
    endpoint_tool.__qualname__ = endpoint_name
    parameter_types: list[tuple[str, Any, bool]] = []
    endpoint_path_model = path_model(endpoint_name, endpoint)
    if endpoint_path_model is not None:
        parameter_types.append(("path_params", endpoint_path_model, True))
    query_model = QUERY_MODELS.get(endpoint_name)
    if query_model is not None:
        parameter_types.append(("query", query_model, bool(endpoint.required_query)))
    else:
        parameter_types.append(("query", dict[str, Any] | None, False))
    body_model = BODY_MODELS.get(endpoint_name)
    if body_model is not None:
        parameter_types.append(("body", body_model, endpoint.body_required))
    else:
        parameter_types.append(("body", dict[str, Any] | None, False))
    parameter_types.append(("confirm", bool, False))
    required = [item for item in parameter_types if item[2]]
    optional = [item for item in parameter_types if not item[2]]
    endpoint_tool.__signature__ = inspect.Signature(
        [
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=annotation,
                default=(
                    inspect.Parameter.empty
                    if is_required
                    else False if name == "confirm" else None
                ),
            )
            for name, annotation, is_required in required + optional
        ],
        return_annotation=Any,
    )
    warning = " Requires confirm=true." if endpoint.confirmation_required else ""
    body_format = (
        "form-encoded fields" if endpoint.body_encoding == "form" else "JSON"
    )
    endpoint_tool.__doc__ = (
        f"{endpoint.description} {endpoint.method} {endpoint.path}.{warning} "
        f"Use path_params for placeholders, query for URL parameters, and body for {body_format}."
    )
    return endpoint_tool


@mcp.tool()
def api_list_subscribers(
    page: int = 1,
    per_page: int | Literal["all"] = 20,
    query: str = "",
    list_ids: list[int] | None = None,
    subscription_status: str = "",
    order_by: str = "created_at",
    order: str = "DESC",
) -> Any:
    """List subscribers with explicit, one-based pagination arguments."""
    if page < 1:
        raise ValueError("page must be at least 1")
    _validate_per_page(per_page)
    if order not in {"ASC", "DESC"}:
        raise ValueError("order must be ASC or DESC")

    params: dict[str, Any] = {
        "page": page,
        "per_page": per_page,
        "order_by": order_by,
        "order": order,
    }
    if query:
        params["query"] = query
    if list_ids:
        params["list_id"] = list_ids
    if subscription_status:
        params["subscription_status"] = subscription_status
    return _call("call_endpoint", "api_list_subscribers", query=params)


@mcp.tool()
def api_list_campaigns(
    page: int = 1,
    per_page: int | Literal["all"] = 20,
    query: str = "",
    statuses: list[str] | None = None,
    tags: list[str] | None = None,
    no_body: bool = True,
    order_by: str = "created_at",
    order: str = "DESC",
) -> Any:
    """List campaigns with explicit, one-based pagination arguments."""
    params = _paginated_query(page, per_page, order_by, order)
    params["no_body"] = no_body
    if query:
        params["query"] = query
    if statuses:
        params["status"] = statuses
    if tags:
        params["tags"] = tags
    return _call("call_endpoint", "api_list_campaigns", query=params)


@mcp.tool()
def api_list_lists(
    page: int = 1,
    per_page: int | Literal["all"] = 20,
    query: str = "",
    status: str = "",
    tags: list[str] | None = None,
    minimal: bool = False,
    order_by: str = "created_at",
    order: str = "DESC",
) -> Any:
    """List mailing lists with explicit, one-based pagination arguments."""
    params = _paginated_query(page, per_page, order_by, order)
    params["minimal"] = minimal
    if query:
        params["query"] = query
    if status:
        params["status"] = status
    if tags:
        params["tag"] = tags
    return _call("call_endpoint", "api_list_lists", query=params)


@mcp.tool()
def api_list_bounces(
    page: int = 1,
    per_page: int | Literal["all"] = 20,
    campaign_id: int | None = None,
    source: str = "",
    order_by: str = "created_at",
    order: str = "DESC",
) -> Any:
    """List bounce records with explicit, one-based pagination arguments."""
    params = _paginated_query(page, per_page, order_by, order)
    if campaign_id is not None:
        if campaign_id <= 0:
            raise ValueError("campaign_id must be positive")
        params["campaign_id"] = campaign_id
    if source:
        params["source"] = source
    return _call("call_endpoint", "api_list_bounces", query=params)


def _paginated_query(
    page: int, per_page: int | Literal["all"], order_by: str, order: str
) -> dict[str, Any]:
    if page < 1:
        raise ValueError("page must be at least 1")
    _validate_per_page(per_page)
    normalized_order = order.upper()
    if normalized_order not in {"ASC", "DESC"}:
        raise ValueError("order must be ASC or DESC")
    return {
        "page": page,
        "per_page": per_page,
        "order_by": order_by,
        "order": normalized_order,
    }


def _validate_per_page(per_page: int | Literal["all"]) -> None:
    if per_page == "all":
        return
    if isinstance(per_page, bool) or not isinstance(per_page, int):
        raise ValueError("per_page must be an integer or 'all'")
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100, or 'all'")


for _endpoint_name, _endpoint in ENDPOINTS.items():
    if _endpoint_name not in {
        "api_list_subscribers",
        "api_list_campaigns",
        "api_list_lists",
        "api_list_bounces",
    }:
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
    subscription_status: str = "confirmed",
) -> Any:
    """Upload a CSV/ZIP subscriber import from base64 content."""
    if mode not in {"subscribe", "blocklist"}:
        raise ValueError("mode must be 'subscribe' or 'blocklist'")
    if not list_ids or any(value <= 0 for value in list_ids):
        raise ValueError("at least one positive list ID is required")
    if subscription_status not in {"confirmed", "unconfirmed", "unsubscribed"}:
        raise ValueError(
            "subscription_status must be confirmed, unconfirmed, or unsubscribed"
        )
    params = {
        "mode": mode,
        "lists": list_ids,
        "overwrite": overwrite,
        "delim": delimiter,
        "subscription_status": subscription_status,
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
