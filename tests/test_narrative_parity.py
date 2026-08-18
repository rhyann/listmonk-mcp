"""Regression checks for Listmonk's narrative API guides.

Swagger parity catches endpoint drift. These checks cover required fields, conditional rules,
and documented details that are absent from or stale in the Swagger document.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from listmonk_mcp.contracts import BODY_MODELS, QUERY_MODELS
from listmonk_mcp.endpoints import ENDPOINTS


def required(model: type) -> set[str]:
    return set(model.model_json_schema().get("required", []))


def test_subscriber_create_update_and_patch_are_distinct() -> None:
    assert required(BODY_MODELS["api_create_subscriber"]) == {"email", "name", "status"}
    assert required(BODY_MODELS["api_update_subscriber"]) == {
        "email", "name", "status", "lists"
    }
    assert required(BODY_MODELS["api_patch_subscriber"]) == set()


@pytest.mark.parametrize(
    "endpoint",
    ["api_update_subscriber_lists", "api_update_subscribers_for_list", "api_query_update_subscriber_lists"],
)
def test_add_to_list_requires_subscription_status(endpoint: str) -> None:
    model = BODY_MODELS[endpoint]
    fields = {"ids": [1]} if endpoint != "api_query_update_subscriber_lists" else {}
    if endpoint == "api_update_subscriber_lists":
        fields["target_list_ids"] = [2]
    if endpoint == "api_query_update_subscriber_lists":
        fields["target_list_ids"] = [2]
    with pytest.raises(ValidationError, match="status is required"):
        model.model_validate({**fields, "action": "add"})
    assert model.model_validate({**fields, "action": "add", "status": "confirmed"})
    assert model.model_validate({**fields, "action": "remove"})


def test_list_and_campaign_mutation_contracts_match_guides() -> None:
    assert required(BODY_MODELS["api_create_list"]) == {"name", "type", "optin"}
    assert "status" in BODY_MODELS["api_update_list"].model_fields
    assert required(BODY_MODELS["api_change_campaign_status"]) == {"status"}
    assert required(BODY_MODELS["api_set_campaign_archive"]) == {"archive"}
    assert "archive_slug" in BODY_MODELS["api_set_campaign_archive"].model_fields


def test_analytics_templates_transactional_and_bulk_delete_contracts() -> None:
    analytics = QUERY_MODELS["api_campaign_analytics"].model_json_schema()
    assert analytics["properties"]["id"]["type"] == "array"
    assert required(QUERY_MODELS["api_list_templates"]) == set()
    transactional = BODY_MODELS["api_send_transactional"]
    assert required(transactional) == {"template_id"}
    assert {"subscriber_emails", "subscriber_ids", "subscriber_mode", "subject", "altbody"} <= set(
        transactional.model_fields
    )
    with pytest.raises(ValidationError, match="recipient"):
        transactional.model_validate({"template_id": 1})
    assert transactional.model_validate({"template_id": 1, "subscriber_ids": [2]})
    for endpoint in ("api_delete_subscribers", "api_delete_lists", "api_delete_campaigns", "api_delete_bounces"):
        assert ENDPOINTS[endpoint].query_required
        assert endpoint in QUERY_MODELS


def test_conditional_delete_selections() -> None:
    for endpoint in ("api_delete_lists", "api_delete_campaigns"):
        model = QUERY_MODELS[endpoint]
        with pytest.raises(ValidationError, match="id or query"):
            model.model_validate({})
        assert model.model_validate({"id": [1]})
        assert model.model_validate({"query": "weekly"})
    bounce = QUERY_MODELS["api_delete_bounces"]
    with pytest.raises(ValidationError, match="id or all=true"):
        bounce.model_validate({})
    assert bounce.model_validate({"all": True})
    subscriber_query_delete = BODY_MODELS["api_query_delete_subscribers"]
    with pytest.raises(ValidationError, match="query, list_ids, or all=true"):
        subscriber_query_delete.model_validate({})
    assert subscriber_query_delete.model_validate({"all": True})


def test_bounce_ordering_is_lowercase_in_contract() -> None:
    schema = QUERY_MODELS["api_list_bounces"].model_json_schema()
    assert schema["properties"]["order"]["anyOf"][0]["enum"] == ["asc", "desc"]
