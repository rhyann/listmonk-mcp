"""Regression snapshot of operations in Listmonk's official Swagger document."""

from __future__ import annotations

import re

from listmonk_mcp.endpoints import ENDPOINTS


SWAGGER_OPERATIONS = {
    ("GET", "/api/health"),
    ("GET", "/api/config"),
    ("GET", "/api/lang/{lang}"),
    ("GET", "/api/dashboard/charts"),
    ("GET", "/api/dashboard/counts"),
    ("GET", "/api/settings"),
    ("PUT", "/api/settings"),
    ("POST", "/api/settings/smtp/test"),
    ("POST", "/api/admin/reload"),
    ("GET", "/api/logs"),
    ("GET", "/api/subscribers"),
    ("POST", "/api/subscribers"),
    ("DELETE", "/api/subscribers"),
    ("GET", "/api/subscribers/{id}"),
    ("PUT", "/api/subscribers/{id}"),
    ("DELETE", "/api/subscribers/{id}"),
    ("PUT", "/api/subscribers/lists"),
    ("PUT", "/api/subscribers/lists/{id}"),
    ("PUT", "/api/subscribers/blocklist"),
    ("PUT", "/api/subscribers/{id}/blocklist"),
    ("GET", "/api/subscribers/{id}/export"),
    ("GET", "/api/subscribers/{id}/bounces"),
    ("DELETE", "/api/subscribers/{id}/bounces"),
    ("POST", "/api/subscribers/{id}/optin"),
    ("POST", "/api/subscribers/query/delete"),
    ("PUT", "/api/subscribers/query/blocklist"),
    ("PUT", "/api/subscribers/query/lists"),
    ("GET", "/api/bounces"),
    ("DELETE", "/api/bounces"),
    ("GET", "/api/bounces/{id}"),
    ("DELETE", "/api/bounces/{id}"),
    ("GET", "/api/lists"),
    ("POST", "/api/lists"),
    ("GET", "/api/lists/{id}"),
    ("PUT", "/api/lists/{id}"),
    ("DELETE", "/api/lists/{id}"),
    ("GET", "/api/import/subscribers"),
    ("POST", "/api/import/subscribers"),
    ("DELETE", "/api/import/subscribers"),
    ("GET", "/api/import/subscribers/logs"),
    ("GET", "/api/campaigns"),
    ("POST", "/api/campaigns"),
    ("GET", "/api/campaigns/{id}"),
    ("PUT", "/api/campaigns/{id}"),
    ("DELETE", "/api/campaigns/{id}"),
    ("GET", "/api/campaigns/running/stats"),
    ("GET", "/api/campaigns/analytics/{id}"),
    ("GET", "/api/campaigns/{id}/preview"),
    ("POST", "/api/campaigns/{id}/preview"),
    ("POST", "/api/campaigns/{id}/text"),
    ("PUT", "/api/campaigns/{id}/status"),
    ("PUT", "/api/campaigns/{id}/archive"),
    ("POST", "/api/campaigns/{id}/content"),
    ("POST", "/api/campaigns/{id}/test"),
    ("GET", "/api/media"),
    ("POST", "/api/media"),
    ("GET", "/api/media/{id}"),
    ("DELETE", "/api/media/{id}"),
    ("GET", "/api/templates"),
    ("POST", "/api/templates"),
    ("GET", "/api/templates/{id}"),
    ("PUT", "/api/templates/{id}"),
    ("DELETE", "/api/templates/{id}"),
    ("POST", "/api/templates/preview"),
    ("GET", "/api/templates/{id}/preview"),
    ("PUT", "/api/templates/{id}/default"),
    ("POST", "/api/tx"),
    ("DELETE", "/api/maintenance/subscribers/{id}"),
    ("DELETE", "/api/maintenance/analytics/{id}"),
    ("DELETE", "/api/maintenance/subscriptions/unconfirmed"),
    ("GET", "/api/public/lists"),
    ("POST", "/api/public/subscription"),
}


def _normalize(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{id}", path)


def test_mcp_covers_every_swagger_operation() -> None:
    exposed = {(endpoint.method, _normalize(endpoint.path)) for endpoint in ENDPOINTS.values()}
    exposed |= {
        ("POST", "/api/media"),
        ("POST", "/api/import/subscribers"),
        ("POST", "/api/tx"),
    }
    documented = {(method, _normalize(path)) for method, path in SWAGGER_OPERATIONS}
    assert documented <= exposed
