"""Small, testable client for the permitted Listmonk campaign operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class ListmonkClient:
    """Listmonk API client limited to newsletter campaign operations."""

    def __init__(
        self,
        base_url: str,
        username: str,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
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

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        response.raise_for_status()
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    def get_campaign(self, campaign_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/campaigns/{campaign_id}")

    def list_campaigns(
        self, query: str = "", status: str = "", limit: int = 20
    ) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params: dict[str, Any] = {
            "page": 1,
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

    def send_test(self, campaign_id: int, email_addresses: list[str]) -> dict[str, Any]:
        addresses = [address.strip() for address in email_addresses if address.strip()]
        if not addresses:
            raise ValueError("at least one test email address is required")
        return self._request(
            "POST",
            f"/api/campaigns/{campaign_id}/test",
            json={"subscribers": addresses},
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

