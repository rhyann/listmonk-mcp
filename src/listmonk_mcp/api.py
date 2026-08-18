"""Small, testable client for the permitted Listmonk campaign operations."""

from __future__ import annotations

from datetime import datetime
from email.utils import parseaddr
import json
from typing import Any, Literal

import httpx

from .endpoints import ENDPOINTS


class ListmonkClient:
    """Listmonk API client limited to newsletter campaign operations."""

    def __init__(
        self,
        base_url: str,
        username: str,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
        allow_sensitive: bool = False,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("LISTMONK_URL must begin with http:// or https://")
        if not username or not token:
            raise ValueError("Listmonk username and token are required")

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            auth=(username, token),
            headers={"Accept": "application/json"},
            timeout=30.0,
            transport=transport,
        )
        self._allow_sensitive = allow_sensitive

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.is_error:
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = payload.get("message") or payload.get("error") or payload
                else:
                    detail = payload
            except ValueError:
                detail = response.text.strip() or response.reason_phrase
            rendered_detail = (
                detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
            )
            # Keep remote error bodies useful to MCP callers without allowing an
            # unexpectedly large response to flood the tool result or logs.
            rendered_detail = rendered_detail[:2000]
            raise httpx.HTTPStatusError(
                f"Listmonk API returned {response.status_code} "
                f"{response.reason_phrase}: {rendered_detail}",
                request=response.request,
                response=response,
            )
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    def call_endpoint(
        self,
        endpoint_name: str,
        *,
        path_params: dict[str, str | int] | None = None,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        confirm: bool = False,
    ) -> Any:
        """Call one explicitly allow-listed endpoint."""
        try:
            endpoint = ENDPOINTS[endpoint_name]
        except KeyError as exc:
            raise ValueError(f"unknown endpoint: {endpoint_name}") from exc
        if endpoint.confirmation_required and not confirm:
            raise ValueError(f"{endpoint_name} requires confirm=true")
        if endpoint.confirmation_required and not self._allow_sensitive:
            raise PermissionError(
                f"{endpoint_name} is disabled; set LISTMONK_ENABLE_SENSITIVE_TOOLS=true"
            )

        missing_query = [
            name for name in endpoint.required_query if name not in (query or {})
        ]
        if missing_query:
            raise ValueError(
                f"{endpoint_name} requires query parameter(s): {', '.join(missing_query)}"
            )
        if endpoint.query_required and not query:
            raise ValueError(f"{endpoint_name} requires query parameters")
        if endpoint.body_required and not body:
            raise ValueError(f"{endpoint_name} requires a non-empty body")

        path = endpoint.path
        path_enums = dict(endpoint.path_enums)
        for key, value in (path_params or {}).items():
            token = "{" + key + "}"
            if token not in path:
                raise ValueError(f"unexpected path parameter: {key}")
            if not str(value) or "/" in str(value) or ".." in str(value):
                raise ValueError(f"invalid path parameter: {key}")
            if key in path_enums and str(value) not in path_enums[key]:
                allowed = ", ".join(path_enums[key])
                raise ValueError(f"{key} must be one of: {allowed}")
            path = path.replace(token, str(value))
        if "{" in path or "}" in path:
            raise ValueError("missing required path parameter")

        kwargs: dict[str, Any] = {}
        if query:
            kwargs["params"] = query
        if body is not None:
            kwargs["data" if endpoint.body_encoding == "form" else "json"] = body
        return self._request(endpoint.method, path, **kwargs)

    def upload_file(
        self,
        path: str,
        *,
        filename: str,
        content: bytes,
        form: dict[str, str] | None = None,
    ) -> Any:
        if path not in {"/api/media", "/api/import/subscribers"}:
            raise ValueError("upload path is not allow-listed")
        if not filename or "/" in filename or "\\" in filename:
            raise ValueError("filename must be a basename")
        return self._request(
            "POST",
            path,
            data=form or {},
            files={"file": (filename, content, "application/octet-stream")},
        )

    def send_transactional_attachments(
        self,
        payload: dict[str, Any],
        attachments: list[tuple[str, bytes]],
        *,
        confirm: bool = False,
    ) -> Any:
        if not confirm:
            raise ValueError("send_transactional_with_attachments requires confirm=true")
        if not self._allow_sensitive:
            raise PermissionError(
                "transactional delivery is disabled; set "
                "LISTMONK_ENABLE_SENSITIVE_TOOLS=true"
            )
        if not attachments:
            raise ValueError("at least one attachment is required")
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for filename, content in attachments:
            if not filename or "/" in filename or "\\" in filename:
                raise ValueError("attachment filename must be a basename")
            files.append(("file", (filename, content, "application/octet-stream")))
        return self._request(
            "POST",
            "/api/tx",
            data={"data": json.dumps(payload)},
            files=files,
        )

    def get_campaign(self, campaign_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/campaigns/{campaign_id}")

    def list_campaigns(
        self,
        query: str = "",
        status: str = "",
        limit: int | Literal["all"] = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        if limit != "all" and (
            isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100
        ):
            raise ValueError("limit must be between 1 and 100, or 'all'")
        if page < 1:
            raise ValueError("page must be at least 1")
        params: dict[str, Any] = {
            "page": page,
            "per_page": limit,
            "no_body": True,
            "order": "DESC",
            "order_by": "created_at",
        }
        if query:
            params["query"] = query
        if status:
            params["status"] = status
        return self._request("GET", "/api/campaigns", params=params)

    @staticmethod
    def _campaign_payload(
        name: str,
        subject: str,
        body: str,
        list_ids: list[int],
        from_email: str,
        template_id: int,
        content_type: str,
    ) -> dict[str, Any]:
        if not name.strip() or not subject.strip() or not body.strip():
            raise ValueError("name, subject, and body are required")
        if not list_ids or any(item <= 0 for item in list_ids):
            raise ValueError("at least one positive list ID is required")
        if template_id <= 0:
            raise ValueError("template_id must be positive")
        if content_type not in {"richtext", "html", "markdown", "plain", "visual"}:
            raise ValueError("unsupported content_type")
        return {
            "name": name,
            "subject": subject,
            "body": body,
            "lists": list_ids,
            "from_email": from_email,
            "template_id": template_id,
            "content_type": content_type,
            "messenger": "email",
            "type": "regular",
        }

    def create_draft(
        self,
        name: str,
        subject: str,
        body: str,
        list_ids: list[int],
        from_email: str,
        template_id: int,
        content_type: str = "html",
    ) -> dict[str, Any]:
        payload = self._campaign_payload(
            name, subject, body, list_ids, from_email, template_id, content_type
        )
        return self._request("POST", "/api/campaigns", json=payload)

    def update_draft(
        self,
        campaign_id: int,
        name: str,
        subject: str,
        body: str,
        list_ids: list[int],
        from_email: str,
        template_id: int,
        content_type: str = "html",
    ) -> dict[str, Any]:
        self._require_draft(campaign_id)
        payload = self._campaign_payload(
            name, subject, body, list_ids, from_email, template_id, content_type
        )
        return self._request("PUT", f"/api/campaigns/{campaign_id}", json=payload)

    def preview(self, campaign_id: int) -> str:
        return self._request("GET", f"/api/campaigns/{campaign_id}/preview")

    def send_test(
        self,
        campaign_id: int,
        email_addresses: list[str],
        *,
        confirm: bool = False,
    ) -> dict[str, Any]:
        if not confirm:
            raise ValueError("send_newsletter_test requires confirm=true")
        if not self._allow_sensitive:
            raise PermissionError(
                "test delivery is disabled; set LISTMONK_ENABLE_SENSITIVE_TOOLS=true"
            )

        addresses: list[str] = []
        for value in email_addresses:
            value = value.strip()
            if not value:
                continue
            _, address = parseaddr(value)
            if not address or "@" not in address:
                raise ValueError(f"invalid test email address: {value!r}")
            normalized = address.lower()
            if normalized not in addresses:
                addresses.append(normalized)
        if not addresses:
            raise ValueError("at least one test email address is required")

        response = self.get_campaign(campaign_id)
        campaign = response.get("data", response)
        payload = {
            "name": campaign["name"],
            "subject": campaign["subject"],
            "body": campaign["body"],
            "lists": [
                item["id"] if isinstance(item, dict) else item
                for item in campaign["lists"]
            ],
            "from_email": campaign.get("from_email", ""),
            "template_id": campaign.get("template_id", 0),
            "content_type": campaign["content_type"],
            "messenger": campaign.get("messenger", "email"),
            "type": campaign.get("type", "regular"),
            "subscribers": addresses,
        }
        for optional_field in ("altbody", "headers", "media"):
            if optional_field in campaign:
                payload[optional_field] = campaign[optional_field]
        return self._request(
            "POST",
            f"/api/campaigns/{campaign_id}/test",
            json=payload,
        )

    def schedule(self, campaign_id: int, send_at: str) -> dict[str, Any]:
        campaign = self._require_draft(campaign_id)
        try:
            datetime.fromisoformat(send_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("send_at must be an ISO-8601 timestamp") from exc

        update = {
            "name": campaign["name"],
            "subject": campaign["subject"],
            "body": campaign["body"],
            "lists": [item["id"] if isinstance(item, dict) else item for item in campaign["lists"]],
            "from_email": campaign.get("from_email", ""),
            "template_id": campaign.get("template_id", 0),
            "content_type": campaign["content_type"],
            "messenger": campaign.get("messenger", "email"),
            "type": campaign.get("type", "regular"),
            "send_at": send_at,
        }
        self._request("PUT", f"/api/campaigns/{campaign_id}", json=update)
        return self._request(
            "PUT",
            f"/api/campaigns/{campaign_id}/status",
            json={"status": "scheduled"},
        )

    def _require_draft(self, campaign_id: int) -> dict[str, Any]:
        response = self.get_campaign(campaign_id)
        campaign = response.get("data", response)
        if campaign.get("status") != "draft":
            raise ValueError(
                f"campaign {campaign_id} is {campaign.get('status')!r}, not 'draft'"
            )
        return campaign
