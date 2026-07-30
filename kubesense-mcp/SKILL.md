---
name: kubesense-mcp
description: The KubeSense MCP tool layer — connection and auth, the full 29-tool inventory, tool selection, the discovery-first rule, the catalog-label field contract shared by every logs/traces query, WHERE syntax, multi-datasource formula queries, and how to read the TSV/columnar output formats. Read this when a tool returns a field-name or WHERE error.
metadata:
  version: "2.0.0"
  author: kubesense
  repository: https://github.com/kubesense-ai/kubesense-mcp-skills
  tags: kubesense,mcp,observability,tools,where-clause,discovery,field-catalog,auth
---

# KubeSense MCP

The tool layer every KubeSense query skill sits on. This skill owns the **shared
contract** — field names, WHERE syntax, output formats — so the per-signal skills don't
each have to redefine it.

## Routing

| The user is asking… | Read |
|---|---|
| logs, error messages, grep | [kubesense-logs](../kubesense-logs/SKILL.md) |
| latency, p99, requests, spans, which hop broke | [kubesense-traces](../kubesense-traces/SKILL.md) |
| CPU, memory, disk, PromQL | [kubesense-metrics](../kubesense-metrics/SKILL.md) |
| what's running, pod restarts, what changed | [kubesense-infra](../kubesense-infra/SKILL.md) |
| alerts — list, investigate, create | [kubesense-alerts](../kubesense-alerts/SKILL.md) |

## Connection

Served by kubeapi at **`/mcp`** over Streamable HTTP, mounted outside the `/api` group.
Same credentials as the REST API.

```bash
# API key — recommended for agents, does not expire
claude mcp add --scope user --transport http kubesense \
  https://<your-kubesense-host>/mcp \
  --header "x-api-key: <your-api-key>"

# JWT access token — expires
claude mcp add --scope user --transport http kubesense \
  https://<your-kubesense-host>/mcp \
  --header "Authorization: Bearer <access-token>"
```

Liveness: `GET /mcp_health`. To confirm *who* you are authenticated as, call
`get-current-user` — no arguments, cheap, resolved from the request credentials.

**RBAC** is resolved per tool call against the modules `logs`, `traces`,
`infrastructure` (metrics + nodes/pods), and `alerts`. A permission error names the
module. `analyze-telemetry` resolves every module its sub-queries touch.

Set `MCP_LOG_LEVEL=debug` server-side to log per-call argument payloads without raising
the global log level.

## Tools (29)

**Discovery — call before querying**

| Tool | Returns |
|---|---|
| `get-trace-or-log-fields` | Field catalog for logs or traces in a window |
| `get-available-metrics` | Metric names |
| `get-metric-labels` | Label names on one metric |

**Query**

| Tool | Returns |
|---|---|
| `search-logs` | Raw log rows (default 10) |
| `search-traces` | Raw span rows (default 10) |
| `analyze-logs` | Aggregated log series |
| `analyze-traces` | Aggregated span series |
| `analyze-metrics` | PromQL result |
| `analyze-telemetry` | Multiple queries + formulas in one call |
| `get-distributed-trace` | Full span tree for one `trace_id` |

**Inventory** — see [kubesense-infra](../kubesense-infra/SKILL.md)

`list-clusters` · `list-nodes` · `get-node-detail` · `list-pods` · `get-pod-detail` ·
`list-workloads` · `get-workload-detail` · `list-issues` · `get-infra-issues` ·
`get-recent-changes`

**Alerts** — see [kubesense-alerts](../kubesense-alerts/SKILL.md)

`list-alerts` (external Alertmanager) · `list-active-alerts` (native store, firing) ·
`list-alert-rules` (rule definitions) · `get-alert-details` · `get-alert-history` ·
`list-notification-channels` · `find-investigation-for-alert`

**Identity**

`get-current-user` — returns `username`, `name`, `email`, `role`, `auth_type`. Note
`username` and `email` are frequently **different**; ownership fields such as
`list-alert-rules`' `created_by` match on **username**.

**Write — mutates state**

`create-alert` — the only write tool. Carries write annotations and expects user
approval. State exactly what you are about to create before calling it.

## Discovery-First Rule

**Never guess a name.** Not a field, metric, cluster, or label.

```
logs / traces:  get-trace-or-log-fields  →  search-* / analyze-*
metrics:        get-available-metrics     →  get-metric-labels  →  analyze-metrics
clusters:       list-clusters             →  anything with a "clusters" filter
```

Two reasons this matters more than usual here:

1. Field names are **rejected** with an error naming the correct label — good, but only
   if you read it rather than retrying.
2. A wrong **cluster** name or **metric** name is *not* an error — it returns an empty
   result indistinguishable from "the value is zero".

Pass the **same time window** to `get-trace-or-log-fields` that you will use for the
query: attribute keys are window-scoped and differ across windows.

## The Field-Name Contract

Logs/traces inputs — `where`, `required_fields`, `group_by_fields`, `fields`, `sort_by` —
accept **catalog labels only**. Storage column names are rejected:

```
field "pod_name" is a storage column; use the catalog label "instance" instead
  (call get-trace-or-log-fields to see all labels)

unknown field "service" for signal=logs; call get-trace-or-log-fields to discover
  valid fields (attributes carry an @ prefix)
```

| Concept | Logs | Traces |
|---|---|---|
| severity / outcome | `type` (`ERROR` — **UPPER**) | `status` (`error` — **lower**) |
| pod | `instance` | `instance` |
| container | `container` | `container` |
| **node** | **`node`** | **`node_name`** |
| **service identity** | **not available** — use `workload` | **`service`** |
| workload | `workload` | `workload` |
| HTTP method | — | `method` |
| HTTP status | — | `status_code` |
| endpoint | — | `resource` |
| span role | — | `role` |
| protocol | — | `protocol` |
| message text | `body` | not available |
| latency | — | `duration` |

The full per-signal tables, including hidden-but-accepted fields and every storage
mapping, are in **[references/field-catalog.md](./references/field-catalog.md)**.

> [!WARNING]
> The two signals disagree on `node`/`node_name` and on severity name *and* casing, and
> `service` exists only on traces. Carrying a field name from one signal to the other is
> the most common failure.

Read enum casing from the **`enum_values`** column of discovery output, never the
`example` column — the example generator silently returns blanks for several enum fields
(logs `type`; traces `method`, `protocol`, `status_code`).

## WHERE Syntax

```
type = ERROR AND namespace = production
status = error AND role = server
namespace IN (production, staging)
NOT (env_type = dev)
body ILIKE "%timeout%"
duration > 500
@user.id = abc-123
```

**Operators the parser accepts:** `=` `!=` `<` `>` `<=` `>=` `LIKE` `ILIKE`
`SUBSTR_ILIKE` `IN` — combined with `AND` / `OR` / `NOT` and parentheses.

> [!WARNING]
> Discovery's `operators` column **over-advertises**. `HAS_TOKEN`, `HAS_ALL`, `HAS_ANY`,
> `LIKE_AND`, `ILIKE_LOG`, `IS_IP_ADDRESS`, `EXIST` appear in the legend but have **no
> WHERE-string syntax**. `body HAS_TOKEN oom` is a parse error. `exist(@field)` is broken
> on both signals (it emits a value-bearing `EXIST` the validator rejects) — there is no
> working existence check.

**Quoting.** Bare values may contain only letters, digits, `_`, `.`, `-`. Anything with a
slash, colon, `%`, or space must be double-quoted:

```
resource = "/api/v1/checkout"           ✓
timestamp > "2026-07-30T10:00:00Z"      ✓
resource = /api/v1/checkout             ✗ parse error
```

**`NOT IN` is not a leaf operator.** Write `NOT (namespace IN (kube-system, default))`.

**Attributes** carry `@` in WHERE — **but only on logs.** On traces, `@attr` filters are
rejected as unknown fields (a server-side defect; the tool descriptions claim otherwise).
Trace attributes still work in `group_by_fields` / `fields` / `required_fields` /
`sort_by` via `{"field": "db.system", "is_attribute": true}` — no `@` there, for either
signal.

**`duration` is millisecond-in, nanosecond-out** — see
[kubesense-traces](../kubesense-traces/SKILL.md).

## Choosing a Tool

| Question | Tool |
|---|---|
| "show me recent errors" | `search-logs` |
| "how many errors in the last hour" | `analyze-logs`, `row_count` |
| "p99 latency for checkout" | `analyze-traces`, `p99` over `duration` |
| "why did this request fail" | `get-distributed-trace` |
| "CPU usage" | `get-available-metrics` → `analyze-metrics` |
| "error rate as a percentage" | `analyze-telemetry` with a formula |
| "what's running / what's broken / what changed" | inventory tools — one call for what would otherwise be several queries |

**Aggregate with `analyze-*`, don't paginate `search-*`.** Reading raw rows to compute a
count is slower, costs far more tokens, and — because paged scans are ordered
hour-bucket-first across clusters — is not even guaranteed complete.

`query_type` on every `analyze-*`: `range` = time series (trends), `instant` = one value
per series (totals, current state, top-N).

Time ranges are RFC3339 (`2026-07-30T10:00:00Z`). Start narrow (15–30 min) and widen.
Discovery tools default to the last hour; inventory tools too.

## Multi-Datasource Queries and Formulas

`analyze-telemetry` runs several queries in one call and composes them. This is the only
way to get a ratio, error rate, or percentage.

```json
{
  "from_time": "2026-07-30T10:00:00Z",
  "to_time": "2026-07-30T11:00:00Z",
  "query_type": "instant",
  "queries": {
    "A": { "selectedMode": "traces", "value_operation": "row_count" },
    "B": { "selectedMode": "traces", "where": "status = error", "value_operation": "row_count" },
    "C": { "query_type": "formula", "expression": "(B/A)*100" }
  }
}
```

Queries are keyed by single-letter labels. Formula entries use
`"query_type": "formula"` with an `expression` referencing other labels. See
**[references/multi-query.md](./references/multi-query.md)** for cross-signal examples.

## Reading the Output

Three shapes, all designed to save tokens:

**TSV** (`search-*`, all inventory and alert list tools) — a `# key=value` metadata line,
then a header row, then one row per record. Empty cell = field absent. A `## name` line
starts a labelled sub-table (e.g. `## services`, `## silences`).

**Columnar JSON** (all `analyze-*`) — `results` keyed by query label:

- `range`: one shared `timestamps` array (Unix seconds, emitted **once**), and each series
  carries a bare `values` array aligned positionally — `values[i]` is the value at
  `timestamps[i]`, `null` = no data in that bucket.
- `instant`: no `timestamps`; each series carries a single scalar `value`.
- `total_series` / `truncated` report how many non-zero series existed **before** the
  top-N cap.

**Record with sub-tables** (`get-*-detail`) — `field<TAB>value` lines for scalars, `## name`
TSV blocks for nested arrays, compact JSON for maps. Empty fields omitted.

Timestamps are always RFC3339 UTC at millisecond precision — exactly the format
`from_time`/`to_time` accept, so a cell can be copied straight back as a cursor.

## Pagination

`search-logs` / `search-traces` have **no `page` or `offset`**. You page by narrowing
`to_time`; the window is half-open so the cursor row isn't repeated.

Take the **minimum** timestamp from the page (`timestamp` for logs, `start_timestamp` for
traces) and pass it verbatim as the next `to_time`. Copy the millisecond precision exactly.

Inventory and alert tools *do* paginate conventionally, with `page`/`page_size` (default
50) or `limit`/`offset`.

See the per-signal skills for the ordering caveats that make exhaustive raw scans
unreliable — and prefer aggregation whenever the answer is a number.

## Rules

1. Discover before querying — fields, metrics, clusters. Never guess.
2. Pass the same window to `get-trace-or-log-fields` that you'll query.
3. Catalog labels only. On a field error, read the suggested label; don't retry the same
   name.
4. Never carry a field name across signals (`node` vs `node_name`; `type` vs `status`;
   `service` is traces-only).
5. Enum casing from `enum_values`, not `example`.
6. WHERE operators: `= != < > <= >= LIKE ILIKE SUBSTR_ILIKE IN` only. Quote values with
   `/`, `:`, `%`, or spaces. `NOT (x IN (...))`, never `x NOT IN (...)`.
7. `value_operation` is `row_count` — never `count`.
8. `analyze-*` for numbers, `search-*` only to read records.
9. `analyze-telemetry` + formula for ratios and percentages.
10. An empty result is not zero — verify names and widen the window before reporting a
    value.
11. `create-alert` mutates state: say what you're creating, and call
    `list-notification-channels` first or it will notify nobody.
