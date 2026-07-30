# KubeSense Skills for AI Agents

KubeSense observability skills for Claude Code, Cursor, OpenCode, Codex CLI, Gemini CLI,
Windsurf, and other AI agents.

Skills are grouped by **telemetry surface** — one skill per thing you query, plus a hub
skill for the tool layer they share.

## Skills

| Skill | Description |
|---|---|
| **kubesense-mcp** | Tool layer — connection, auth, full tool inventory, the WHERE/field-name contract |
| **kubesense-logs** | Search and aggregate logs |
| **kubesense-traces** | Spans, latency percentiles, error rates, distributed traces |
| **kubesense-metrics** | PromQL/MetricsQL over Kubernetes and infrastructure metrics |
| **kubesense-infra** | Clusters, nodes, pods, workloads, infra failures, recent deploys |
| **kubesense-alerts** | List/investigate/create alerts, generate import JSON, migrate Datadog monitors |
| **kubesense-dashboards** | Generate dashboard preset JSON |
| **kubesense-investigate** | End-to-end incident workflow across all of the above |

## Install

### All skills

```bash
npx skills add kubesense-ai/kubesense-mcp-skills --full-depth -y
```

### Individual skills

```bash
npx skills add kubesense-ai/kubesense-mcp-skills \
  --skill kubesense-mcp \
  --skill kubesense-logs \
  --skill kubesense-traces \
  --skill kubesense-metrics \
  --skill kubesense-infra \
  --skill kubesense-alerts \
  --skill kubesense-dashboards \
  --skill kubesense-investigate \
  --full-depth -y
```

`--full-depth` matters: each skill carries a `references/` directory with the detailed
field catalogs and JSON schemas. Without it you get the SKILL.md but not the references
it points at.

Just the dashboard generator:

```bash
npx skills add kubesense-ai/kubesense-mcp-skills --skill kubesense-dashboards --full-depth -y
```

## Connect the MCP Server

Every skill except `kubesense-dashboards` and `kubesense-alerts` needs the KubeSense MCP
server. It is served by kubeapi at **`/mcp`** over Streamable HTTP, outside the `/api`
group, and authenticates with the same credentials as the REST API.

**API key** (recommended for agents — does not expire):

```bash
claude mcp add --scope user --transport http kubesense \
  https://<your-kubesense-host>/mcp \
  --header "x-api-key: <your-api-key>"
```

**JWT access token** (expires; fine for short sessions):

```bash
claude mcp add --scope user --transport http kubesense \
  https://<your-kubesense-host>/mcp \
  --header "Authorization: Bearer <access-token>"
```

Verify with `GET /mcp_health`, then ask your agent to call `get-current-user` — it
returns the identity the session resolved to and needs no arguments.

Access is scoped by the same RBAC as the UI: `logs`, `traces`, `infrastructure`, and
`alerts` modules are resolved per tool call. A permission error names the module.

## Which Skill Do I Want?

| Question | Skill |
|---|---|
| "show me errors in checkout" | kubesense-logs |
| "p99 latency by service", "which hop is slow" | kubesense-traces |
| "memory usage", "am I near the limit" | kubesense-metrics |
| "what's running", "why is this pod restarting", "did we deploy" | kubesense-infra |
| "alert me when 5xx > 1%", "what's firing", "port this Datadog monitor" | kubesense-alerts |
| "build a dashboard for the payments service" | kubesense-dashboards |
| "this alert fired, what's wrong?" | kubesense-investigate |

## Field Names: The One Thing To Know

Logs and traces queries take **catalog labels**, not storage column names. The server
rejects storage names at every input slot rather than silently returning nothing:

| Concept | Use | Not |
|---|---|---|
| log severity | `type` | `level` |
| pod | `instance` | `pod_name` |
| service identity | `service` | `app_service` |
| HTTP method | `method` | `subtype` |
| HTTP status | `status_code` | `return_code` |
| span role | `role` | `kind` |
| node | `node` | `host` |

Run `get-trace-or-log-fields` to get the authoritative list for your window — attribute
keys are window-scoped and differ between deployments.

The **alert engine accepts a different set** from the query engine. See
[kubesense-alerts](./kubesense-alerts/SKILL.md).

## Repository Layout

```
SKILL.md                      umbrella index (installable on its own)
kubesense-mcp/                hub: connection, tools, query contract
  references/
kubesense-logs/
  references/
kubesense-traces/
  references/
kubesense-metrics/
  references/metric-catalog.md
kubesense-infra/
kubesense-alerts/
  references/
kubesense-dashboards/
  references/
kubesense-investigate/
```

Each top-level directory is an independently installable skill with its own
frontmatter `name`. Skills cross-reference each other by relative path but **degrade
gracefully** — every skill states its own hard facts rather than depending on a sibling
being installed.

## License

MIT
