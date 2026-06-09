---
name: kubesense-mcp
description: How to use KubeSense MCP tools to query logs, traces, and metrics from Kubernetes clusters. Covers tool selection, the discovery-first workflow, the WHERE-clause filter syntax, and links to datasource-specific skills.
---

# KubeSense MCP

KubeSense MCP provides observability tools for querying logs, traces, and metrics from Kubernetes clusters.

## Two Hard Rules (always)

> **1. Discover before querying.** Always call `get-trace-or-log-fields` (or `get-available-metrics` / `get-metric-labels` for metrics) BEFORE every `search-*` or `analyze-*` call. Field names, attribute keys, and metric names vary by deployment and by time window — never guess, never reuse from a different window without re-discovering.

> **2. Write `where` with field labels, never raw storage names.** Use the `field` value EXACTLY as discovery returned it — that's the catalog label, the same string the explorer's UI shows. Don't substitute synonyms or "what it's called in the DB":
> - logs: write `type = ERROR`, NOT `level = ERROR`
> - pods: write `instance = my-pod-xxxx`, NOT `pod_name = my-pod-xxxx`
> - traces: write `service = checkout`, NOT `app_service = checkout`; `protocol = HTTP`, NOT `protocol_type = HTTP`; `role = server`, NOT `kind = server`; `method = GET`, NOT `subtype = GET`; `status_code = 500`, NOT `return_code = 500`; `resource = "/api/v1/users"`, NOT `clustered_resource = ...`
>
> Writing labels means the `where` string round-trips into "View in Explorer" verbatim — no translation needed at the call site, no divergence between MCP and UI.

If you're unsure of a field's label, paste the discovery `example` snippet — it always uses the correct label.

## Tools

| Tool                      | Purpose                                       |
| ------------------------- | --------------------------------------------- |
| `get-trace-or-log-fields` | Discover available fields for logs or traces  |
| `get-available-metrics`   | Discover available metric names               |
| `get-metric-labels`       | Get label names for a specific metric         |
| `search-logs`             | Browse raw log records (default 10 rows)      |
| `search-traces`           | Browse raw trace/span records (default 10 rows) |
| `analyze-logs`            | Run aggregated analysis on logs               |
| `analyze-traces`          | Run aggregated analysis on traces             |
| `analyze-metrics`         | Execute PromQL queries on metrics             |
| `analyze-telemetry`       | Multi-datasource queries with formula support |

## Discovery Flow

```
logs/traces:  get-trace-or-log-fields  →  search-logs / search-traces / analyze-logs / analyze-traces
metrics:      get-available-metrics    →  get-metric-labels  →  analyze-metrics
```

Each field in the discovery response carries its `allowed_operators` and an `example` WHERE snippet — the snippet is always written with the correct label, so pasting it is the safest way to start.

## Choosing the Right Signal (decide FIRST)

> **Hard Rule.** Before any search/analyze call, decide which signal the question is about. The user's vocabulary tells you. Picking the wrong signal wastes the call — every field name will be wrong and discovery has to be redone.

| The user says…                                                                                                  | Signal      | Tools                              |
| --------------------------------------------------------------------------------------------------------------- | ----------- | ---------------------------------- |
| request, response, span, **latency**, p99 / p95 / p50, HTTP method, status code, endpoint, resource, downstream call, service-to-service | **traces**  | `search-traces`, `analyze-traces`  |
| log line, error message, body, panic, stack trace, log level, **WARN / INFO / DEBUG**, log format               | **logs**    | `search-logs`, `analyze-logs`      |
| CPU, memory, disk, RPS, time-series labels, PromQL, scrape                                                       | **metrics** | `analyze-metrics`                  |
| error **rate** (count ÷ total), ratio across two datasources                                                     | mixed       | `analyze-telemetry` with a formula |

When the user changes phrasing mid-conversation ("now show me requests…"), re-decide signal — don't carry forward the last one.

## Choosing the Right Tool

- **Show me recent logs** → `search-logs`
- **How many errors in the last hour?** → `analyze-logs` with `row_count` + error filter
- **P99 latency for a service** → `analyze-traces` with `p99` aggregation on `duration`
- **Top services by errors / requests** → `analyze-traces` (NOT logs)
- **CPU / memory usage** → `get-available-metrics` → `analyze-metrics`
- **Error rate as a percentage** → `analyze-telemetry` with a formula query

## Service vs Workload (traces)

> **Prefer `service` over `workload` for app identity.** `service` is the cross-platform identifier — it's present in K8s, Docker, and legacy deployments. `workload` is K8s-specific (deployment / statefulset / daemonset name) and is empty for non-K8s sources.
>
> Use `workload` ONLY when the user explicitly asks about K8s topology ("group by deployment", "errors per statefulset"). For *any* question about a "service", an "app", a "microservice", or the top-N by traffic / errors / latency — group by `service`.

## Query Types

All `analyze-*` tools accept a `query_type`:

- `"range"` — time-series values over the given window (for trends)
- `"instant"` — single point-in-time snapshot (for totals/counts)

## Time Ranges

All tools require `from_time` and `to_time` as RFC3339 strings, e.g.:

```json
"from_time": "2026-04-23T10:00:00Z",
"to_time":   "2026-04-23T10:30:00Z"
```

Start narrow (15–30 min) and widen if needed. Discovery responses for attributes are window-scoped — pass the SAME window you'll use for the follow-up search/analyze call.

## Filters (WHERE clause)

`search-logs`, `search-traces`, `analyze-logs`, and `analyze-traces` take a single `where` string — the same SQL-style syntax the explorer's advanced-query mode uses. The server parses it into the internal filter tree, so the LLM never has to assemble JSON operator trees.

Empty / missing `where` matches every row in the window.

### Basic shape

```
where = "<field> <op> <value>"
```

Combine leaves with `AND`, `OR`, and `NOT`, group with parentheses.

```json
"where": "type = ERROR AND namespace = production"
```

```json
"where": "status = error AND (service = checkout-api OR service = auth-api)"
```

### Operators

| Operator        | Use                            | Example                                  |
| --------------- | ------------------------------ | ---------------------------------------- |
| `=`             | Exact match                    | `type = ERROR`                           |
| `!=`            | Not equal                      | `status != ok`                           |
| `<` `>` `<=` `>=` | Numeric comparisons          | `duration > 1000`, `status_code >= 500`  |
| `IN`            | Match any value in a list      | `type IN (ERROR, WARN)`                  |
| `NOT IN`        | Exclude values in a list       | `namespace NOT IN (kube-system, default)`|
| `LIKE`          | Case-sensitive wildcard (`%`)  | `body LIKE "%timeout%"`                  |
| `ILIKE`         | Case-insensitive wildcard      | `service ILIKE "%api%"`                  |
| `SUBSTR_ILIKE`  | Case-insensitive substring     | `body SUBSTR_ILIKE timeout`              |

Check the field's `allowed_operators` in the discovery response — not every operator is allowed on every field.

### Attributes use the `@` prefix

Dynamic attribute keys (log attributes, trace attributes) carry an `@` prefix in the WHERE clause:

```
@http.method = GET
@db.system = postgresql
@user.id = "abc-123"
```

**Trace attributes are special** — they're stored as parallel arrays internally. You still write them with `@` and `=` / `IN` / `LIKE`; the server remaps them to the internal `ARRAY_MAP*` operators automatically. You no longer write `ARRAY_MAP` by hand.

### Quoting values

- Identifier-shaped values (`error`, `production`, `api-server`, `200`) can be **bare**.
- Values with spaces, punctuation, or wildcards must be **double-quoted**: `body ILIKE "%db timeout%"`.
- Single quotes are accepted but double quotes are preferred for consistency with the explorer UI.

### Common label translations

Discovery returns the catalog labels (the names the explorer's advanced-query mode accepts). A few common ones differ from the raw storage column names you may have seen elsewhere:

| Catalog label (write this) | Concept              | Notes                                            |
| -------------------------- | -------------------- | ------------------------------------------------ |
| `instance`                 | Pod name             | Storage column is `pod_name` — write `instance`. |
| `type` *(logs)*            | Log level            | Storage column is `level` — write `type`.        |
| `node` *(logs)*            | Host / node name     | Storage column is `host` — write `node`.         |
| `protocol` *(traces)*      | Protocol kind        | Storage column is `protocol_type`.               |
| `role` *(traces)*          | client / server      | Storage column is `kind`.                        |
| `method` *(traces)*        | HTTP / RPC method    | Storage column is `subtype`.                     |
| `status_code` *(traces)*   | HTTP / RPC code      | Storage column is `return_code`.                 |
| `service` *(traces)*       | App service name     | Storage column is `app_service`.                 |
| `resource` *(traces)*      | Resource path        | Storage column is `clustered_resource`.          |
| `container`                | Container name       | Storage column is `container_name`.              |

When in doubt, copy the discovery `example` snippet verbatim — it always uses the right label.

### Tip: clone the example from discovery

`get-trace-or-log-fields` returns an `example` snippet for every field, pre-formatted with the right prefix, operator, and a representative value. Paste it into your `where` string and tweak:

```json
"example": "@http.method = GET"
```

```json
"where": "type = ERROR AND @http.method = POST"
```

## Datasource Skills

For detailed field references, examples, and query patterns, read the datasource-specific skill:

- **[kubesense-logs](./kubesense-logs/SKILL.md)** — Discover fields, search raw logs, aggregate with counts/percentiles
- **[kubesense-apm](./kubesense-apm/SKILL.md)** — Discover fields, search raw spans, analyze latency and errors
- **[kubesense-metrics](./kubesense-metrics/SKILL.md)** — Discover metrics, get labels, write PromQL queries
- **[kubesense-multi-query](./kubesense-multi-query/SKILL.md)** — Run correlated queries across logs/traces/metrics and compute derived values (error rate, ratios) with `analyze-telemetry`
