"""Typed request contracts derived from Listmonk's OpenAPI schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from .endpoints import Endpoint


class ContractModel(BaseModel):
    """Permit forward-compatible fields while validating documented fields."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SubscriberQuery(ContractModel):
    page: int | None = None
    per_page: int | Literal["all"] | None = None
    query: str | None = None
    order_by: Literal["name", "status", "created_at", "updated_at"] | None = None
    order: Literal["ASC", "DESC"] | None = None
    subscription_status: str | None = None
    list_id: list[int] | None = None


class BounceQuery(ContractModel):
    campaign_id: int | None = None
    page: int | None = None
    per_page: int | Literal["all"] | None = None
    source: str | None = None
    order_by: Literal["email", "campaign_name", "source", "created_at"] | None = None
    order: Literal["asc", "desc"] | None = None


class ListQuery(ContractModel):
    page: int | None = None
    per_page: int | Literal["all"] | None = None
    query: str | None = None
    order_by: Literal["name", "status", "created_at", "updated_at"] | None = None
    order: Literal["ASC", "DESC"] | None = None
    minimal: bool | None = None
    tag: list[str] | None = None


class CampaignQuery(ContractModel):
    status: list[str] | None = None
    no_body: bool | None = None
    page: int | None = None
    per_page: int | Literal["all"] | None = None
    tags: list[str] | None = None
    order: Literal["ASC", "DESC"] | None = None
    order_by: Literal["name", "status", "created_at", "updated_at"] | None = None
    query: str | None = None


class CampaignAnalyticsQuery(ContractModel):
    from_: str = Field(alias="from")
    to: str
    id: str


class TemplateQuery(ContractModel):
    no_body: bool


class SubscriberPayload(ContractModel):
    email: str | None = None
    name: str | None = None
    status: str | None = None
    lists: list[int] | None = None
    list_uuids: list[str] | None = None
    preconfirm_subscriptions: bool | None = None
    attribs: dict[str, Any] | None = None


class SubscriberMutation(ContractModel):
    query: str | None = None
    ids: list[int] | None = None
    action: str | None = None
    target_list_ids: list[int] | None = None
    status: str | None = None


class ListPayload(ContractModel):
    name: str | None = None
    type: Literal["private", "public"] | None = None
    optin: Literal["single", "double"] | None = None
    tags: list[str] | None = None
    description: str | None = None


class CampaignPayload(ContractModel):
    name: str | None = None
    subject: str | None = None
    lists: list[int] | None = None
    from_email: str | None = None
    content_type: str | None = None
    messenger: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    send_later: bool | None = None
    send_at: str | None = None
    body: str | None = None
    template_id: int | None = None


class CreateCampaignPayload(ContractModel):
    """Fields Listmonk requires when creating a campaign."""

    name: str
    subject: str
    lists: list[int]
    type: Literal["regular", "optin"]
    content_type: Literal["richtext", "html", "markdown", "plain", "visual"]
    body: str
    from_email: str | None = None
    body_source: str | None = None
    altbody: str | None = None
    send_at: str | None = None
    messenger: str | None = None
    template_id: int | None = None
    tags: list[str] | None = None
    headers: list[dict[str, str]] | None = None
    attribs: dict[str, Any] | None = None


class CampaignPreviewPayload(ContractModel):
    template_id: int | None = None
    content_type: str | None = None
    body: str | None = None


class CampaignStatusPayload(ContractModel):
    status: str | None = None


class CampaignArchivePayload(ContractModel):
    archive: bool | None = None
    archive_template_id: int | None = None
    archive_meta: dict[str, Any] | None = None


class TemplatePayload(ContractModel):
    name: str
    type: Literal["campaign", "campaign_visual", "tx"]
    subject: str | None = None
    body_source: str | None = None
    body: str


class UpdateTemplatePayload(ContractModel):
    name: str | None = None
    type: Literal["campaign", "campaign_visual", "tx"] | None = None
    subject: str | None = None
    body_source: str | None = None
    body: str | None = None


class TemplatePreviewPayload(ContractModel):
    template_type: str | None = None
    body: str | None = None


class MaintenanceDatePayload(ContractModel):
    before_date: str | None = None


class TransactionalPayload(ContractModel):
    subscriber_email: str | None = None
    subscriber_id: int | None = None
    template_id: int | None = None
    from_email: str | None = None
    data: dict[str, Any] | None = None
    headers: list[dict[str, Any]] | None = None
    messenger: str | None = None
    content_type: str | None = None


class PublicSubscriptionPayload(ContractModel):
    name: str | None = None
    email: str | None = None
    list_uuids: list[str] | None = None


QUERY_MODELS: dict[str, type[ContractModel]] = {
    "api_list_subscribers": SubscriberQuery,
    "api_list_bounces": BounceQuery,
    "api_list_lists": ListQuery,
    "api_list_campaigns": CampaignQuery,
    "api_running_campaign_stats": create_model(
        "RunningCampaignStatsQuery", campaign_id=(float, ...), __base__=ContractModel
    ),
    "api_campaign_analytics": CampaignAnalyticsQuery,
    "api_list_templates": TemplateQuery,
    "api_delete_subscribers": create_model(
        "DeleteSubscribersQuery", id=(str, ...), __base__=ContractModel
    ),
}


BODY_MODELS: dict[str, type[ContractModel]] = {
    "api_create_subscriber": SubscriberPayload,
    "api_update_subscriber": SubscriberPayload,
    "api_patch_subscriber": SubscriberPayload,
    "api_update_subscriber_lists": SubscriberMutation,
    "api_update_subscribers_for_list": SubscriberMutation,
    "api_query_update_subscriber_lists": SubscriberMutation,
    "api_set_subscribers_blocklist": SubscriberMutation,
    "api_query_set_subscribers_blocklist": SubscriberMutation,
    "api_set_subscriber_blocklist": SubscriberMutation,
    "api_create_list": ListPayload,
    "api_update_list": ListPayload,
    "api_create_campaign": CreateCampaignPayload,
    "api_update_campaign": CampaignPayload,
    "api_render_campaign_preview": CampaignPreviewPayload,
    "api_render_campaign_text": CampaignPreviewPayload,
    "api_convert_campaign_content": CampaignPayload,
    "api_change_campaign_status": CampaignStatusPayload,
    "api_set_campaign_archive": CampaignArchivePayload,
    "api_test_campaign": CampaignPayload,
    "api_create_template": TemplatePayload,
    "api_update_template": UpdateTemplatePayload,
    "api_render_template_preview": TemplatePreviewPayload,
    "api_send_transactional": TransactionalPayload,
    "api_public_subscribe": PublicSubscriptionPayload,
    "api_delete_maintenance_analytics": MaintenanceDatePayload,
    "api_delete_unconfirmed_subscriptions": MaintenanceDatePayload,
}


def path_model(endpoint_name: str, endpoint: Endpoint) -> type[ContractModel] | None:
    """Build a typed model for an endpoint's fixed path placeholders."""
    fields: dict[str, tuple[Any, Any]] = {}
    for placeholder in endpoint.path.split("{")[1:]:
        name = placeholder.split("}", 1)[0]
        choices = dict(endpoint.path_enums).get(name)
        annotation: Any
        if choices:
            annotation = Literal.__getitem__(choices)
        else:
            annotation = str if name in {"lang", "maintenance_type"} else int
        fields[name] = (annotation, ...)
    if not fields:
        return None
    return create_model(
        f"{''.join(part.title() for part in endpoint_name.split('_'))}Path",
        __base__=ContractModel,
        **fields,
    )


def dump_contract(value: Any) -> Any:
    """Convert validated models back to request dictionaries."""
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True, exclude_none=True)
    return value
