import anyio
from mcp import Client

from listmonk_mcp.endpoints import ENDPOINTS
from listmonk_mcp import server
from listmonk_mcp.server import mcp


def test_server_exposes_only_the_intended_tools() -> None:
    async def inspect_tools():
        async with Client(mcp) as client:
            response = await client.list_tools()
            return response.tools

    expected = set(ENDPOINTS) | {
        "get_campaign",
        "list_campaigns",
        "create_newsletter_draft",
        "update_newsletter_draft",
        "replace_campaign_html_from_base64",
        "replace_campaign_html_from_workspace",
        "preview_newsletter",
        "send_newsletter_test",
        "schedule_newsletter",
        "upload_media",
        "import_subscribers",
        "send_transactional_with_attachments",
    }
    tools = anyio.run(inspect_tools)
    assert {tool.name for tool in tools} == expected
    for tool_name in (
        "api_list_subscribers",
        "api_list_campaigns",
        "api_list_lists",
        "api_list_bounces",
    ):
        paginated_tool = next(tool for tool in tools if tool.name == tool_name)
        properties = paginated_tool.input_schema["properties"]
        assert properties["page"]["default"] == 1
        assert properties["per_page"]["default"] == 20
        assert properties["page"]["type"] == "integer"

    campaign_tool = next(tool for tool in tools if tool.name == "list_campaigns")
    assert campaign_tool.input_schema["properties"]["page"]["default"] == 1

    analytics_tool = next(
        tool for tool in tools if tool.name == "api_campaign_analytics"
    )
    analytics_schema = analytics_tool.input_schema
    assert set(analytics_schema["required"]) == {"path_params", "query"}
    assert analytics_schema["$defs"]["ApiCampaignAnalyticsPath"]["properties"][
        "analytics_type"
    ]["enum"] == ["links", "views", "clicks", "bounces"]
    assert analytics_schema["$defs"]["CampaignAnalyticsQuery"]["required"] == [
        "from",
        "to",
        "id",
    ]

    template_tool = next(tool for tool in tools if tool.name == "api_create_template")
    assert template_tool.input_schema["required"] == ["body"]
    assert set(template_tool.input_schema["$defs"]["TemplatePayload"]["required"]) == {
        "name",
        "type",
        "body",
    }

    create_campaign_tool = next(
        tool for tool in tools if tool.name == "api_create_campaign"
    )
    assert create_campaign_tool.input_schema["required"] == ["body"]
    assert set(
        create_campaign_tool.input_schema["$defs"]["CreateCampaignPayload"]["required"]
    ) == {"name", "subject", "lists", "type", "content_type", "body"}


def test_mcp_invocation_validates_and_unwraps_typed_contracts(monkeypatch) -> None:
    captured = {}

    def fake_call(method, endpoint_name, **kwargs):
        captured.update(method=method, endpoint_name=endpoint_name, **kwargs)
        return {"data": []}

    monkeypatch.setattr(server, "_call", fake_call)

    async def invoke_tool():
        async with Client(mcp) as client:
            return await client.call_tool(
                "api_campaign_analytics",
                {
                    "path_params": {"analytics_type": "views"},
                    "query": {
                        "from": "2026-01-01",
                        "to": "2026-02-01",
                        "id": [1],
                    },
                },
            )

    result = anyio.run(invoke_tool)
    assert not result.is_error
    assert captured == {
        "method": "call_endpoint",
        "endpoint_name": "api_campaign_analytics",
        "path_params": {"analytics_type": "views"},
        "query": {"from": "2026-01-01", "to": "2026-02-01", "id": [1]},
        "body": None,
        "confirm": False,
    }
