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
| **kubesense-sql** | Raw ClickHouse SQL over logs and traces — joins, CTEs, window functions |
| **kubesense-infra** | Clusters, nodes, pods, workloads, infra failures, recent deploys |
| **kubesense-alerts** | List/investigate/create alerts, generate import JSON, migrate Datadog monitors |
| **kubesense-dashboards** | Create dashboards, or generate preset JSON to import |

## Install

> [!IMPORTANT]
> **Always pass `--full-depth`.** This repo has a root `SKILL.md` (the umbrella index), and
> the installer stops there unless told to search deeper — so without the flag it finds
> **1** skill instead of **9**, and does so *silently*. Every command below includes it.
>
> `references/` directories are **not** the reason for the flag. They are copied
> automatically as part of a skill, nested subdirectories included.

### All skills

```bash
npx skills add kubesense-ai/kubesense-mcp-skills --full-depth
```

You will be asked which agents to install to and whether to install **project** (current
directory) or **global** (home directory, available everywhere). Pick global if you want
the skills in every repo you work in.

### Individual skills

```bash
npx skills add kubesense-ai/kubesense-mcp-skills \
  --skill kubesense-mcp \
  --skill kubesense-logs \
  --skill kubesense-traces \
  --skill kubesense-metrics \
  --skill kubesense-sql \
  --skill kubesense-infra \
  --skill kubesense-alerts \
  --skill kubesense-dashboards \
  --full-depth
```

Just the dashboard generator:

```bash
npx skills add kubesense-ai/kubesense-mcp-skills --skill kubesense-dashboards --full-depth
```

### Verify

```bash
npx skills add kubesense-ai/kubesense-mcp-skills --list --full-depth
```

Should report **9 skills**. If it says 1, the `--full-depth` flag is missing.

### Unattended installs

`-y` skips every prompt, and the scope it falls back to is **project**, not a smart
default — so `-y` alone always installs into the current directory. Pair it with `-g`
for a global install:

```bash
npx skills add kubesense-ai/kubesense-mcp-skills --full-depth -g -y
```

Coding agents (Claude Code, Cursor, …) are detected and run non-interactively whether or
not you pass `-y`, so an agent installing on your behalf also lands project-scoped unless
it passes `-g`.

Other useful flags: `--copy` copies files instead of symlinking; `-a claude-code` targets
a specific agent.

## Connect the MCP Server

Every skill except `kubesense-dashboards` and `kubesense-alerts` needs the KubeSense MCP
server — those two work offline for generating JSON, but need it to validate, create, or
discover real field names. It is served by kubeapi at **`/mcp`** over Streamable HTTP, outside the `/api`
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
| "this alert fired, what's wrong?" | kubesense-alerts, then kubesense-infra |

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
SKILL.md                          umbrella index (installable on its own)
kubesense-mcp/SKILL.md            hub: connection, tools, query contract
  references/field-catalog.md
  references/multi-query.md
kubesense-logs/SKILL.md
kubesense-traces/SKILL.md
kubesense-metrics/SKILL.md
  references/metric-catalog.md
kubesense-infra/SKILL.md
kubesense-alerts/SKILL.md
  references/import-json.md
  references/datadog-migration.md
kubesense-dashboards/SKILL.md
  references/panel-config.md
drafts/                           not installable — see drafts/README.md
```

Each top-level directory containing a `SKILL.md` is an independently installable skill
with its own frontmatter `name`. Skills cross-reference each other by relative path but
**degrade gracefully** — every skill states its own hard facts rather than depending on a
sibling being installed.

`drafts/` holds work-in-progress skills. Nothing in it has a `SKILL.md`, so the installer
does not discover it and `--list` will not show it.

## License

MIT
