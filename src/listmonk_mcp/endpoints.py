"""Explicit allow-list of Listmonk API endpoints exposed through MCP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    description: str
    confirmation_required: bool = False


def _e(
    method: str, path: str, description: str, confirmation_required: bool = False
) -> Endpoint:
    return Endpoint(method, path, description, confirmation_required)


# Every path is fixed here. Tools generated from this table cannot call arbitrary URLs.
ENDPOINTS: dict[str, Endpoint] = {
    # System, dashboard, and settings.
    "api_health": _e("GET", "/api/health", "Check Listmonk service health."),
    "api_get_config": _e("GET", "/api/config", "Get public application configuration."),
    "api_dashboard_charts": _e("GET", "/api/dashboard/charts", "Get dashboard chart data."),
    "api_dashboard_counts": _e("GET", "/api/dashboard/counts", "Get dashboard summary counts."),
    "api_get_settings": _e("GET", "/api/settings", "Get Listmonk settings."),
    "api_update_settings": _e("PUT", "/api/settings", "Update Listmonk settings.", True),
    "api_test_smtp": _e("POST", "/api/settings/smtp/test", "Send an SMTP settings test.", True),
    "api_admin_reload": _e("POST", "/api/admin/reload", "Reload Listmonk configuration.", True),
    "api_get_logs": _e("GET", "/api/logs", "Retrieve application logs."),

    # Subscribers.
    "api_list_subscribers": _e("GET", "/api/subscribers", "Query subscribers."),
    "api_get_subscriber": _e("GET", "/api/subscribers/{subscriber_id}", "Get a subscriber."),
    "api_export_subscriber": _e("GET", "/api/subscribers/{subscriber_id}/export", "Export subscriber data."),
    "api_get_subscriber_bounces": _e("GET", "/api/subscribers/{subscriber_id}/bounces", "Get subscriber bounces."),
    "api_create_subscriber": _e("POST", "/api/subscribers", "Create a subscriber."),
    "api_send_subscriber_optin": _e("POST", "/api/subscribers/{subscriber_id}/optin", "Send an opt-in confirmation.", True),
    "api_public_subscribe": _e("POST", "/api/public/subscription", "Create a public subscription."),
    "api_update_subscriber_lists": _e("PUT", "/api/subscribers/lists", "Modify subscriber list memberships."),
    "api_query_update_subscriber_lists": _e("PUT", "/api/subscribers/query/lists", "Bulk modify list memberships by query.", True),
    "api_update_subscriber": _e("PUT", "/api/subscribers/{subscriber_id}", "Replace a subscriber."),
    "api_patch_subscriber": _e("PATCH", "/api/subscribers/{subscriber_id}", "Partially update a subscriber."),
    "api_set_subscriber_blocklist": _e("PUT", "/api/subscribers/{subscriber_id}/blocklist", "Set one subscriber's blocklist state."),
    "api_set_subscribers_blocklist": _e("PUT", "/api/subscribers/blocklist", "Set blocklist state for selected subscribers.", True),
    "api_query_set_subscribers_blocklist": _e("PUT", "/api/subscribers/query/blocklist", "Set blocklist state by query.", True),
    "api_delete_subscriber": _e("DELETE", "/api/subscribers/{subscriber_id}", "Delete a subscriber.", True),
    "api_delete_subscriber_bounces": _e("DELETE", "/api/subscribers/{subscriber_id}/bounces", "Delete one subscriber's bounces.", True),
    "api_delete_subscribers": _e("DELETE", "/api/subscribers", "Delete selected subscribers.", True),
    "api_query_delete_subscribers": _e("POST", "/api/subscribers/query/delete", "Delete subscribers by query.", True),

    # Lists.
    "api_list_lists": _e("GET", "/api/lists", "List mailing lists."),
    "api_list_public_lists": _e("GET", "/api/public/lists", "List active public lists."),
    "api_get_list": _e("GET", "/api/lists/{list_id}", "Get a mailing list."),
    "api_create_list": _e("POST", "/api/lists", "Create a mailing list."),
    "api_update_list": _e("PUT", "/api/lists/{list_id}", "Update a mailing list."),
    "api_delete_list": _e("DELETE", "/api/lists/{list_id}", "Delete a mailing list.", True),
    "api_delete_lists": _e("DELETE", "/api/lists", "Delete multiple mailing lists.", True),

    # Subscriber imports. Upload is handled by a dedicated binary-safe tool.
    "api_get_import_status": _e("GET", "/api/import/subscribers", "Get subscriber import status."),
    "api_get_import_logs": _e("GET", "/api/import/subscribers/logs", "Get subscriber import logs."),
    "api_stop_import": _e("DELETE", "/api/import/subscribers", "Stop and remove the current import.", True),

    # Campaigns.
    "api_list_campaigns": _e("GET", "/api/campaigns", "List campaigns."),
    "api_get_campaign": _e("GET", "/api/campaigns/{campaign_id}", "Get a campaign."),
    "api_preview_campaign": _e("GET", "/api/campaigns/{campaign_id}/preview", "Preview a campaign."),
    "api_running_campaign_stats": _e("GET", "/api/campaigns/running/stats", "Get running campaign statistics."),
    "api_campaign_analytics": _e("GET", "/api/campaigns/analytics/{analytics_type}", "Get campaign analytics."),
    "api_create_campaign": _e("POST", "/api/campaigns", "Create a campaign."),
    "api_test_campaign": _e("POST", "/api/campaigns/{campaign_id}/test", "Send a campaign test.", True),
    "api_update_campaign": _e("PUT", "/api/campaigns/{campaign_id}", "Update a campaign."),
    "api_change_campaign_status": _e("PUT", "/api/campaigns/{campaign_id}/status", "Change campaign status.", True),
    "api_set_campaign_archive": _e("PUT", "/api/campaigns/{campaign_id}/archive", "Change campaign archive publication."),
    "api_delete_campaign": _e("DELETE", "/api/campaigns/{campaign_id}", "Delete a campaign.", True),
    "api_delete_campaigns": _e("DELETE", "/api/campaigns", "Delete multiple campaigns.", True),

    # Templates.
    "api_list_templates": _e("GET", "/api/templates", "List templates."),
    "api_get_template": _e("GET", "/api/templates/{template_id}", "Get a template."),
    "api_preview_template": _e("GET", "/api/templates/{template_id}/preview", "Preview a saved template."),
    "api_render_template_preview": _e("POST", "/api/templates/preview", "Render an unsaved template preview."),
    "api_create_template": _e("POST", "/api/templates", "Create a template."),
    "api_update_template": _e("PUT", "/api/templates/{template_id}", "Update a template."),
    "api_set_default_template": _e("PUT", "/api/templates/{template_id}/default", "Set the default template."),
    "api_delete_template": _e("DELETE", "/api/templates/{template_id}", "Delete a template.", True),

    # Media. Upload is handled by a dedicated binary-safe tool.
    "api_list_media": _e("GET", "/api/media", "List uploaded media."),
    "api_get_media": _e("GET", "/api/media/{media_id}", "Get uploaded media metadata."),
    "api_delete_media": _e("DELETE", "/api/media/{media_id}", "Delete uploaded media.", True),

    # Bounces.
    "api_list_bounces": _e("GET", "/api/bounces", "List bounce records."),
    "api_delete_bounce": _e("DELETE", "/api/bounces/{bounce_id}", "Delete a bounce record.", True),
    "api_delete_bounces": _e("DELETE", "/api/bounces", "Delete selected or all bounce records.", True),
    "api_record_bounce": _e("POST", "/webhooks/bounce", "Record a bounce event."),

    # Transactional delivery.
    "api_send_transactional": _e("POST", "/api/tx", "Send a transactional message.", True),
}

