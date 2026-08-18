# Listmonk MCP Server

A comprehensive MCP interface for Listmonk. It exposes the documented API through explicit,
allow-listed tools while retaining safer, higher-level tools for common newsletter workflows.
There is no arbitrary URL or HTTP request tool.

## API coverage

The server registers 74 endpoint tools and covers all 72 operations in Listmonk's current
Swagger specification, plus operations documented on Listmonk's narrative API pages:

- health, configuration, dashboard statistics, settings, logs, and administrative reload
- subscribers, subscription state, list memberships, blocklists, exports, and opt-in mail
- public and administrative mailing-list operations
- subscriber imports and import logs
- campaigns, HTML and text previews, content conversion, status changes, archives, running
  statistics, and analytics
- saved templates, template rendering, and default-template selection
- media uploads and management
- bounce records and bounce ingestion
- transactional messages
- language packs and subscriber, analytics, and subscription maintenance

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
unregistered path. OpenAPI-derived nested models give MCP clients typed schemas for documented
query and body fields while allowing forward-compatible fields that may appear in newer
Listmonk versions. Required query parameters, required request bodies, field types, and
documented enums are validated before a request is sent. Endpoints documented as
`application/x-www-form-urlencoded`, including unsaved template and campaign previews, use
form encoding rather than JSON.

All four paginated Listmonk collections have explicit pagination schemas:

- `api_list_subscribers`
- `api_list_campaigns`
- `api_list_lists`
- `api_list_bounces`

Pass `page` and `per_page` as top-level arguments. For example:

```json
{
  "page": 2,
  "per_page": 50,
  "list_ids": [1],
  "subscription_status": "confirmed",
  "order_by": "created_at",
  "order": "DESC"
}
```

Pages are one-based. These tools always forward both `page` and `per_page` to Listmonk. Integer
page sizes are limited to 1–100, and the documented string value `"all"` is also supported.
Because `"all"` can produce a large response, prefer bounded pages for interactive MCP use.
The higher-level `list_campaigns` tool also accepts a top-level `page` argument.

## Higher-level newsletter tools

| Tool | Behavior |
| --- | --- |
| `get_campaign` | Reads one campaign and its status |
| `list_campaigns` | Lists campaigns with optional filters and explicit page selection |
| `create_newsletter_draft` | Creates a draft only |
| `update_newsletter_draft` | Updates only campaigns that remain drafts |
| `preview_newsletter` | Returns Listmonk's rendered preview |
| `send_newsletter_test` | Sends only to explicitly supplied existing subscribers; requires `confirm=true` and the sensitive-tools setting |
| `schedule_newsletter` | Schedules a draft at an explicit ISO-8601 time |

The higher-level scheduling tool verifies that the campaign is a draft before updating its
`send_at` value and changing its status to `scheduled`.

Three binary-safe tools accept base64 data rather than arbitrary host paths:

- `upload_media`
- `import_subscribers`
- `send_transactional_with_attachments`

`import_subscribers` supports Listmonk's documented `subscription_status` import option. Its
accepted values are `confirmed`, `unconfirmed`, and `unsubscribed`; the default is
`confirmed`. Subscribe-mode imports require at least one target list. Blocklist-mode imports
do not, matching Listmonk's import behavior.

The endpoint contracts distinguish subscriber creation, full replacement (`PUT`), and partial
updates (`PATCH`). They also enforce Listmonk's conditional mutation rules—for example,
`status` is required when adding subscribers to lists. Transactional sends require a
`template_id` and at least one recipient selector, and include Listmonk's single-recipient,
multi-recipient, subscriber-mode, subject, and alternate-body fields.

## Sensitive-operation policy

Destructive, delivery, settings, and administrative endpoint tools are disabled by default.
They require two independent gates:

1. The server administrator sets `LISTMONK_ENABLE_SENSITIVE_TOOLS=true`.
2. Each individual tool call includes `confirm=true`.

This applies to deletes, campaign status transitions, test and transactional sends, bulk query
mutations, SMTP tests, settings updates, and administrative reloads. Use a Listmonk API role
with only the permissions this MCP instance actually needs; Listmonk remains the final
authorization boundary.

For `send_newsletter_test`, pass raw subscriber email addresses or standard display-name
addresses such as `Rhyann Stewart <rhyann@example.com>`; the helper normalizes them to raw
email addresses. Each address must already belong to a subscriber visible to the Listmonk API
user. The helper loads the saved campaign and sends Listmonk the complete campaign payload,
as required by Listmonk's test endpoint.

## Requirements

- Python 3.11+
- Listmonk API user and token
- An MCP host that supports stdio servers, such as Hermes

Create a dedicated Listmonk API account instead of using your primary administrator account.

## Install with uv (recommended)

[`uv tool install`](https://docs.astral.sh/uv/guides/tools/) creates a persistent, isolated
environment and exposes the `listmonk-mcp` command without modifying system Python packages.

Install the current release directly from GitHub:

```bash
uv tool install \
  --python 3.12 \
  "git+https://github.com/rhyann/listmonk-mcp.git@v0.5.1"
```

Verify the installation and find the executable Hermes should launch:

```bash
uv tool list
command -v listmonk-mcp
```

The executable is normally installed as:

```text
/home/rhyann/.local/bin/listmonk-mcp
```

Use the path returned by `command -v` rather than assuming it is on the service account's
`PATH`. Hermes starts this stdio server when needed, so `listmonk-mcp` does not need a separate
systemd service.

To reinstall or move to a newer release, replace the tag and run:

```bash
uv tool install --reinstall \
  --python 3.12 \
  "git+https://github.com/rhyann/listmonk-mcp.git@v0.5.1"
```

To uninstall:

```bash
uv tool uninstall listmonk-mcp
```

## Install for development

```bash
git clone https://github.com/rhyann/listmonk-mcp.git
cd listmonk-mcp
python3 -m venv .venv
source .venv/bin/activate
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
export LISTMONK_TOOL_GROUPS="all"
```

### Limit exposed tool groups

`LISTMONK_TOOL_GROUPS` controls which tools the MCP server advertises. It accepts a
comma-separated list of capability groups:

- `system`
- `subscribers`
- `lists`
- `imports`
- `campaigns`
- `templates`
- `media`
- `bounces`
- `transactional`
- `maintenance`

The default, `all`, preserves the complete tool surface. To expose only campaign tools:

```bash
export LISTMONK_TOOL_GROUPS="campaigns"
```

Groups can be combined:

```bash
export LISTMONK_TOOL_GROUPS="campaigns,subscribers,lists"
```

Use `read-only` by itself to expose read-only tools across every group:

```bash
export LISTMONK_TOOL_GROUPS="read-only"
```

Combine it with capability groups to apply it as a restriction. This example exposes only
read-only campaign and subscriber tools:

```bash
export LISTMONK_TOOL_GROUPS="campaigns,subscribers,read-only"
```

Tool groups reduce agent context and prevent hidden tools from being invoked through MCP. They
do not replace Listmonk API-user permissions, which remain the authorization boundary. Restart
the MCP process (and reload the MCP client if it caches tool schemas) after changing this value.

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

Install the tool on the same host and under the same Linux account as the restricted Hermes
gateway. Keep source checkouts, if any, outside the newsletter workspace.

Add the server to the newsletter profile's Hermes configuration:

```yaml
mcp_servers:
  listmonk:
    command: "/home/rhyann/.local/bin/listmonk-mcp"
    env:
      LISTMONK_URL: "${LISTMONK_URL}"
      LISTMONK_USER: "${LISTMONK_USER}"
      LISTMONK_TOKEN: "${LISTMONK_TOKEN}"
      LISTMONK_ENABLE_SENSITIVE_TOOLS: "false"
      LISTMONK_TOOL_GROUPS: "campaigns"
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

## Development and contract checks

The 86 default tests use `httpx.MockTransport`, so they never contact a real Listmonk server.
They verify
authentication, payload construction, draft-only guards, the endpoint registry, path-injection
protection, sensitive-operation gates, multipart uploads, scheduling order, MCP tool exposure,
environment configuration, form encoding, Swagger endpoint parity, request-contract validation,
typed MCP schemas, wrapper delegation, the stdio entry point, and HTTP error propagation. The
current suite covers 437 of 437 source statements (100%).

```bash
pytest
```

Expected coverage summary:

```text
Name                            Stmts   Miss  Cover
---------------------------------------------------
src/listmonk_mcp/__init__.py        1      0   100%
src/listmonk_mcp/api.py           128      0   100%
src/listmonk_mcp/contracts.py     135      0   100%
src/listmonk_mcp/endpoints.py      15      0   100%
src/listmonk_mcp/server.py        158      0   100%
---------------------------------------------------
TOTAL                             437      0   100%
```

Check the local contract against Listmonk's current upstream Swagger document:

```bash
python scripts/check_openapi_drift.py
```

The checker compares operations, form-versus-JSON encoding, required bodies and query fields,
and path enums. CI runs it on every push and pull request and weekly so upstream additions or
contract changes are visible even when this repository is idle. The known erroneous request body
on Swagger's `GET /templates/{id}/preview` is ignored because the narrative documentation and
HTTP behavior use a bodyless GET.

## Pinned Docker integration test

The safe live smoke test runs against `listmonk/listmonk:v6.2.0` and `postgres:17-alpine`. It
checks Listmonk's public health endpoint and public lists without performing writes or requiring
an API token.

```bash
docker compose -f tests/integration/docker-compose.yml up -d
LISTMONK_INTEGRATION=1 pytest -m integration --no-cov
docker compose -f tests/integration/docker-compose.yml down -v
```

The integration test is skipped during the normal unit suite and runs as a separate CI job. The
internal HTTP helper is never exposed as an MCP tool. Add new Listmonk endpoints to the explicit
registry and include tests for their authorization and state checks.

## References

- [Listmonk API documentation](https://listmonk.app/docs/apis/apis/)
- [Listmonk OpenAPI/Swagger specification](https://listmonk.app/docs/swagger/)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
