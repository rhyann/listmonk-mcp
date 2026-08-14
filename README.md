# Listmonk MCP Server

A small, deliberately restricted MCP server for managing Listmonk newsletter campaigns.
It is designed for a host-side Hermes profile connected to Discord. It does **not** expose
arbitrary API requests, subscriber management, list deletion, campaign deletion, or Listmonk
administration.

## Available tools

| Tool | Behavior |
| --- | --- |
| `get_campaign` | Reads one campaign and its status |
| `list_campaigns` | Lists recent campaigns with optional filters |
| `create_newsletter_draft` | Creates a draft only |
| `update_newsletter_draft` | Updates only campaigns that remain drafts |
| `preview_newsletter` | Returns Listmonk's rendered preview |
| `send_newsletter_test` | Sends only to explicitly supplied test addresses |
| `schedule_newsletter` | Schedules a draft at an explicit ISO-8601 time |

Scheduling is the only operation that queues real delivery. The server verifies that the
campaign is a draft before updating its `send_at` value and changing its status to `scheduled`.

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

## Configuration

The server reads three environment variables:

```bash
export LISTMONK_URL="https://listmonk.example.com"
export LISTMONK_USER="hermes_newsletter"
export LISTMONK_TOKEN="replace-me"
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

The tests use `httpx.MockTransport`, so they never contact a real Listmonk server. They verify
authentication, payload construction, draft-only guards, scheduling order, and HTTP error
propagation.

```bash
pytest --cov=listmonk_mcp --cov-report=term-missing
```

The API surface intentionally contains no generic request helper exposed as an MCP tool. Add
new actions as narrowly scoped methods and include tests for their authorization and state
checks.

## References

- [Listmonk campaign API](https://listmonk.app/docs/apis/campaigns/)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

