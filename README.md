# Listmonk MCP Server

A comprehensive MCP interface for Listmonk. It exposes the documented API through explicit,
allow-listed tools while retaining safer, higher-level tools for common newsletter workflows.
There is no arbitrary URL or HTTP request tool.

## API coverage

The server registers 65 endpoint tools across:

- health, configuration, dashboard statistics, settings, logs, and administrative reload
- subscribers, subscription state, list memberships, blocklists, exports, and opt-in mail
- public and administrative mailing-list operations
- subscriber imports and import logs
- campaigns, previews, status changes, archives, running statistics, and analytics
- saved templates, template rendering, and default-template selection
- media uploads and management
- bounce records and bounce ingestion
- transactional messages

Endpoint tools use an `api_` prefix, such as `api_list_subscribers`, `api_create_list`,
`api_campaign_analytics`, and `api_get_settings`. Each accepts only the fields relevant to
transporting that endpoint call:

```json
{
  "path_params": {"subscriber_id": 42},
  "query": {"source": "mcp"},
  "body": {"name": "Ada"}
}
```

The path itself is fixed in the server's endpoint registry. Callers cannot substitute an
unregistered path.

## Higher-level newsletter tools

| Tool | Behavior |
| --- | --- |
| `get_campaign` | Reads one campaign and its status |
| `list_campaigns` | Lists recent campaigns with optional filters |
| `create_newsletter_draft` | Creates a draft only |
| `update_newsletter_draft` | Updates only campaigns that remain drafts |
| `preview_newsletter` | Returns Listmonk's rendered preview |
| `send_newsletter_test` | Sends only to explicitly supplied test addresses |
| `schedule_newsletter` | Schedules a draft at an explicit ISO-8601 time |

The higher-level scheduling tool verifies that the campaign is a draft before updating its
`send_at` value and changing its status to `scheduled`.

Two binary-safe tools accept base64 data rather than arbitrary host paths:

- `upload_media`
- `import_subscribers`
- `send_transactional_with_attachments`

## Sensitive-operation policy

Destructive, delivery, settings, and administrative endpoint tools are disabled by default.
They require two independent gates:

1. The server administrator sets `LISTMONK_ENABLE_SENSITIVE_TOOLS=true`.
2. Each individual tool call includes `confirm=true`.

This applies to deletes, campaign status transitions, test and transactional sends, bulk query
mutations, SMTP tests, settings updates, and administrative reloads. Use a Listmonk API role
with only the permissions this MCP instance actually needs; Listmonk remains the final
authorization boundary.

## Requirements

- Python 3.11+
- Listmonk API user and token
- An MCP host that supports stdio servers, such as Hermes

Create a dedicated Listmonk API account instead of using your primary administrator account.

## Install

```bash
git clone <your-repository-url> listmonk-mcp
cd listmonk-mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e '.[dev]'
pytest
```

The default test command enforces 100% statement coverage. A coverage regression makes the
test run fail.

## Configuration

The server reads these environment variables:

```bash
export LISTMONK_URL="https://listmonk.example.com"
export LISTMONK_USER="hermes_newsletter"
export LISTMONK_TOKEN="replace-me"
export LISTMONK_ENABLE_SENSITIVE_TOOLS="false"
```

Test the credentials independently before configuring MCP:

```bash
curl -u "$LISTMONK_USER:$LISTMONK_TOKEN" \
  "$LISTMONK_URL/api/campaigns?page=1&per_page=5"
```

Do not commit `.env`; it is ignored by Git. `.env.example` contains safe placeholders.

## Run

The installed entry point starts a stdio MCP server:

```bash
listmonk-mcp
```

It will wait silently for an MCP host to communicate over standard input/output.

## Hermes configuration

Install this repository on the same host as the restricted Hermes gateway, outside the
newsletter workspace. For example, clone it to `/home/rhyann/mcp/listmonk-mcp` and install its
virtual environment there.

Add the server to the newsletter profile's Hermes configuration:

```yaml
mcp_servers:
  listmonk:
    command: "/home/rhyann/mcp/listmonk-mcp/.venv/bin/listmonk-mcp"
    env:
      LISTMONK_URL: "${LISTMONK_URL}"
      LISTMONK_USER: "${LISTMONK_USER}"
      LISTMONK_TOKEN: "${LISTMONK_TOKEN}"
      LISTMONK_ENABLE_SENSITIVE_TOOLS: "false"
    tools:
      include:
        - get_campaign
        - list_campaigns
        - create_newsletter_draft
        - update_newsletter_draft
        - preview_newsletter
        - send_newsletter_test
        - schedule_newsletter
```

The example intentionally includes only the original newsletter workflow. Add endpoint tools
to Hermes's `include` list by capability instead of exposing every tool to a Discord-facing
profile. For example, a subscriber-management profile might add:

```yaml
        - api_list_subscribers
        - api_get_subscriber
        - api_create_subscriber
        - api_patch_subscriber
        - api_update_subscriber_lists
```

For a trusted administrative profile, omit the Hermes `include` filter or enumerate the full
endpoint set and explicitly set `LISTMONK_ENABLE_SENSITIVE_TOOLS` to `true`.

Keep credentials in the newsletter Hermes profile's private environment file rather than in
the repository or Discord. Do not mount this repository into the newsletter Docker sandbox;
Hermes should launch it as a host-side subprocess.

Restart the gateway, then test read-only behavior first:

```text
Show me the five most recent Listmonk campaigns and their status.
```

Only after reads work should you test draft creation, preview, and a test email. Treat
`schedule_newsletter` as privileged: request an explicit campaign ID and timestamp, including
the timezone offset.

## Development

The 60 tests use `httpx.MockTransport`, so they never contact a real Listmonk server. They verify
authentication, payload construction, draft-only guards, the endpoint registry, path-injection
protection, sensitive-operation gates, multipart uploads, scheduling order, MCP tool exposure,
environment configuration, wrapper delegation, the stdio entry point, and HTTP error
propagation. The current suite covers 203 of 203 source statements (100%).

```bash
pytest
```

Expected coverage summary:

```text
Name                            Stmts   Miss  Cover
---------------------------------------------------
src/listmonk_mcp/__init__.py        1      0   100%
src/listmonk_mcp/api.py           117      0   100%
src/listmonk_mcp/endpoints.py      11      0   100%
src/listmonk_mcp/server.py         74      0   100%
---------------------------------------------------
TOTAL                             203      0   100%
```

The internal HTTP helper is never exposed as an MCP tool. Add new Listmonk endpoints to the
explicit registry and include tests for their authorization and state checks.

## References

- [Listmonk API documentation](https://listmonk.app/docs/apis/apis/)
- [Listmonk OpenAPI/Swagger specification](https://listmonk.app/docs/swagger/)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
