---
name: kubesense-mcp
description: How to use KubeSense MCP tools to query logs, traces, and metrics from Kubernetes clusters. Covers tool selection, the discovery-first workflow, the UnifiedFilter format, and links to datasource-specific skills.
---

# KubeSense MCP

KubeSense MCP provides observability tools for querying logs, traces, and metrics from Kubernetes clusters.

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

## Discovery-First Rule

**Always discover before querying.** Never guess field names, attribute keys, or metric names — they vary by deployment.

```
logs/traces:  get-trace-or-log-fields  →  search-logs / search-traces / analyze-logs / analyze-traces
metrics:      get-available-metrics    →  get-metric-labels  →  analyze-metrics
```

The discovery response gives each field's `allowed_operators` and an `example` filter leaf you can copy directly into your query.

## Choosing the Right Tool

- **Show me recent logs** → `search-logs`
- **How many errors in the last hour?** → `analyze-logs` with `row_count` + error filter
- **P99 latency for a service** → `analyze-traces` with `p99` aggregation on `duration`
- **CPU / memory usage** → `get-available-metrics` → `analyze-metrics`
- **Error rate as a percentage** → `analyze-telemetry` with a formula query

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

## Filters (UnifiedFilter)

Filter parameters in `search-logs`, `search-traces`, `analyze-logs`, and `analyze-traces` use a **structured tree**, not a SQL string. The shape is called `UnifiedFilter`.

### Basic shape

```json
{
  "type": "advanced",
  "adv_filters": {
    "operation": "AND",
    "children": [
      {
        "field": "level",
        "operation": "EQ",
        "values": ["ERROR"],
        "type": "",
        "field_type": "string"
      }
    ]
  }
}
```

- Group nodes set `operation` to `AND` / `OR` / `NOT` and provide `children[]`.
- Leaf nodes set `field`, `operation`, `values[]`, `type` (`""` for top-level columns, `"attribute"` for dynamic attributes), and `field_type`.
- `NOT` groups take exactly one child. `AND` / `OR` groups take two or more.

### Operators

The exact operators allowed depend on the signal + field kind. Always check the field's `allowed_operators` in the discovery response. Common ones:

| Operator       | Use                            | Notes                                                |
| -------------- | ------------------------------ | ---------------------------------------------------- |
| `EQ`           | `field = value`                | Exact match                                          |
| `NEQ`          | `field != value`               | Not equal                                            |
| `IN`           | `field IN (a, b, c)`           | Matches any value in `values[]`                      |
| `NIN`          | `field NOT IN (a, b, c)`       | Excludes values in `values[]`                        |
| `LT` `GT` `LTE` `GTE` | Comparisons             | Use unquoted numbers in `values[]` for float fields  |
| `LIKE`         | Case-sensitive pattern match   | `%` wildcard                                         |
| `ILIKE`        | Case-insensitive pattern match | `%` wildcard                                         |
| `EXIST`        | Field is present               | No `values[]`                                        |
| `NOT_EXIST`    | Field is absent                | No `values[]`                                        |
| `ARRAY_MAP`    | Trace-attribute equality       | **Only operator allowed on trace attributes**        |

**Trace attributes are special.** They're stored as parallel arrays, so they reject `EQ`/`LIKE` and only accept `ARRAY_MAP*` operators. Trying `EQ` on a trace attribute fails validation with a path-pointed error.

### Combining conditions

Nest groups for `AND` / `OR` mixing. Example: `status = 'error' AND (workload = 'api' OR workload = 'auth')`:

```json
{
  "type": "advanced",
  "adv_filters": {
    "operation": "AND",
    "children": [
      { "field": "status", "operation": "EQ", "values": ["error"], "type": "", "field_type": "string" },
      {
        "operation": "OR",
        "children": [
          { "field": "workload", "operation": "EQ", "values": ["api"], "type": "", "field_type": "string" },
          { "field": "workload", "operation": "EQ", "values": ["auth"], "type": "", "field_type": "string" }
        ]
      }
    ]
  }
}
```

### Tip: clone the example from discovery

`get-trace-or-log-fields` returns an `example` leaf for every field, pre-filled with the right `operation` and `type`. Copy it and just swap your value in:

```json
"example": {
  "field": "namespace",
  "operation": "EQ",
  "values": ["example"],
  "type": "",
  "field_type": "string"
}
```

## Datasource Skills

For detailed field references, examples, and query patterns, read the datasource-specific skill:

- **[kubesense-logs](./kubesense-logs/SKILL.md)** — Discover fields, search raw logs, aggregate with counts/percentiles
- **[kubesense-apm](./kubesense-apm/SKILL.md)** — Discover fields, search raw spans, analyze latency and errors
- **[kubesense-metrics](./kubesense-metrics/SKILL.md)** — Discover metrics, get labels, write PromQL queries

## Multi-Query Reference

- [multi-query.md](multi-query.md) — Multi-datasource queries and formula expressions with `analyze-telemetry`
