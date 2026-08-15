import anyio
from mcp import Client

from listmonk_mcp.endpoints import ENDPOINTS
from listmonk_mcp.server import mcp


def test_server_exposes_only_the_intended_tools() -> None:
    async def inspect_tools() -> set[str]:
        async with Client(mcp) as client:
            response = await client.list_tools()
            return {tool.name for tool in response.tools}

    expected = set(ENDPOINTS) | {
        "get_campaign",
        "list_campaigns",
        "create_newsletter_draft",
        "update_newsletter_draft",
        "preview_newsletter",
        "send_newsletter_test",
        "schedule_newsletter",
        "upload_media",
        "import_subscribers",
        "send_transactional_with_attachments",
    }
    assert anyio.run(inspect_tools) == expected
