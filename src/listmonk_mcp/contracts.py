"""Typed request contracts derived from Listmonk's OpenAPI schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, create_model

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
    status: Literal["active", "archived"] | None = None
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
    id: list[int]


class TemplateQuery(ContractModel):
    no_body: bool | None = None


class CreateSubscriberPayload(ContractModel):
    email: str
    name: str
    status: Literal["enabled", "blocklisted"]
    lists: list[int] | None = None
    list_uuids: list[str] | None = None
    preconfirm_subscriptions: bool | None = None
    attribs: dict[str, Any] | None = None


class UpdateSubscriberPayload(ContractModel):
    email: str
    name: str
    status: Literal["enabled", "disabled", "blocklisted"]
    lists: list[int]
    list_uuids: list[str] | None = None
    preconfirm_subscriptions: bool | None = None
    attribs: dict[str, Any] | None = None


class PatchSubscriberPayload(ContractModel):
    email: str | None = None
    name: str | None = None
    status: Literal["enabled", "disabled", "blocklisted"] | None = None
    lists: list[int] | None = None
    list_uuids: list[str] | None = None
    preconfirm_subscriptions: bool | None = None
    attribs: dict[str, Any] | None = None


class SubscriberListMutation(ContractModel):
    ids: list[int]
    action: Literal["add", "remove", "unsubscribe"]
    target_list_ids: list[int]
    status: Literal["confirmed", "unconfirmed", "unsubscribed"] | None = None

    @model_validator(mode="after")
    def require_add_status(self) -> "SubscriberListMutation":
        if self.action == "add" and self.status is None:
            raise ValueError("status is required when action is 'add'")
        return self


class SubscriberListByQueryMutation(ContractModel):
    query: str | None = None
    search: str | None = None
    list_ids: list[int] | None = None
    subscription_status: str | None = None
    action: Literal["add", "remove", "unsubscribe"]
    target_list_ids: list[int]
    status: Literal["confirmed", "unconfirmed", "unsubscribed"] | None = None

    @model_validator(mode="after")
    def require_add_status(self) -> "SubscriberListByQueryMutation":
        if self.action == "add" and self.status is None:
            raise ValueError("status is required when action is 'add'")
        return self


class SubscriberListForOneMutation(ContractModel):
    ids: list[int]
    action: Literal["add", "remove", "unsubscribe"]
    status: Literal["confirmed", "unconfirmed", "unsubscribed"] | None = None

    @model_validator(mode="after")
    def require_add_status(self) -> "SubscriberListForOneMutation":
        if self.action == "add" and self.status is None:
            raise ValueError("status is required when action is 'add'")
        return self


class SubscriberIdsPayload(ContractModel):
    ids: list[int]


class SubscriberQueryPayload(ContractModel):
    query: str
    list_ids: list[int] | None = None


class SubscriberQueryDeletePayload(ContractModel):
    query: str | None = None
    list_ids: list[int] | None = None
    all: bool | None = None

    @model_validator(mode="after")
    def require_selection(self) -> "SubscriberQueryDeletePayload":
        if not self.query and not self.list_ids and self.all is not True:
            raise ValueError("query, list_ids, or all=true is required")
        return self


class CreateListPayload(ContractModel):
    name: str
    type: Literal["private", "public"]
    optin: Literal["single", "double"]
    status: Literal["active", "archived"] | None = None
    tags: list[str] | None = None
    description: str | None = None


class UpdateListPayload(ContractModel):
    name: str | None = None
    type: Literal["private", "public"] | None = None
    optin: Literal["single", "double"] | None = None
    status: Literal["active", "archived"] | None = None
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
    status: Literal["draft", "scheduled", "running", "paused", "cancelled"]


class CampaignArchivePayload(ContractModel):
    archive: bool
    archive_template_id: int | None = None
    archive_meta: dict[str, Any] | None = None
    archive_slug: str | None = None


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
    subscriber_emails: list[str] | None = None
    subscriber_ids: list[int] | None = None
    subscriber_mode: Literal["default", "fallback", "external"] | None = None
    template_id: int
    from_email: str | None = None
    subject: str | None = None
    data: dict[str, Any] | None = None
    headers: list[dict[str, Any]] | None = None
    messenger: str | None = None
    content_type: str | None = None
    altbody: str | None = None

    @model_validator(mode="after")
    def require_recipient(self) -> "TransactionalPayload":
        if not any(
            (self.subscriber_email, self.subscriber_id, self.subscriber_emails, self.subscriber_ids)
        ):
            raise ValueError("at least one subscriber recipient is required")
        return self


class IdsOrQueryDelete(ContractModel):
    id: list[int] | None = None
    query: str | None = None

    @model_validator(mode="after")
    def require_selection(self) -> "IdsOrQueryDelete":
        if not self.id and not self.query:
            raise ValueError("id or query is required")
        return self


class BounceDeleteQuery(ContractModel):
    id: list[int] | None = None
    all: bool | None = None

    @model_validator(mode="after")
    def require_selection(self) -> "BounceDeleteQuery":
        if not self.id and self.all is not True:
            raise ValueError("id or all=true is required")
        return self


class SubscriberDeleteQuery(ContractModel):
    id: list[int]


class PublicSubscriptionPayload(ContractModel):
    name: str | None = None
    email: str
    list_uuids: list[str]


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
    "api_get_campaign": create_model(
        "GetCampaignQuery", no_body=(bool | None, None), __base__=ContractModel
    ),
    "api_get_template": TemplateQuery,
    "api_delete_subscribers": SubscriberDeleteQuery,
    "api_delete_lists": IdsOrQueryDelete,
    "api_delete_campaigns": IdsOrQueryDelete,
    "api_delete_bounces": BounceDeleteQuery,
}


BODY_MODELS: dict[str, type[ContractModel]] = {
    "api_create_subscriber": CreateSubscriberPayload,
    "api_update_subscriber": UpdateSubscriberPayload,
    "api_patch_subscriber": PatchSubscriberPayload,
    "api_update_subscriber_lists": SubscriberListMutation,
    "api_update_subscribers_for_list": SubscriberListForOneMutation,
    "api_query_update_subscriber_lists": SubscriberListByQueryMutation,
    "api_set_subscribers_blocklist": SubscriberIdsPayload,
    "api_query_set_subscribers_blocklist": SubscriberQueryPayload,
    "api_query_delete_subscribers": SubscriberQueryDeletePayload,
    "api_create_list": CreateListPayload,
    "api_update_list": UpdateListPayload,
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
