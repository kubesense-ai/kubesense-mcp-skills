---
name: kubesense-logs
description: Query and analyze logs from Kubernetes clusters using KubeSense MCP tools. Covers field discovery, raw log search, aggregation analysis, and filter syntax.
---

# KubeSense Logs

Tools for querying and analyzing logs from Kubernetes clusters.

## Tools

| Tool                      | Purpose                              |
| ------------------------- | ------------------------------------ |
| `get-trace-or-log-fields` | Discover available fields for logs   |
| `search-logs`             | Browse raw log records (max 10 rows) |
| `analyze-logs`            | Run aggregated analysis on logs      |

## Discovery-First Rule

**Always discover before querying.** Never guess field names.

```
get-trace-or-log-fields  →  search-logs / analyze-logs
```

## Step 1: Discover Fields

```json
{
  "datasource": "logs",
  "search": "",
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z"
}
```

Use `search` to filter by field name (e.g. `"search": "namespace"`). Pass `""` to get all fields.

### Built-in Log Fields

| Field            | Type    | Values                                        |
| ---------------- | ------- | --------------------------------------------- |
| `workload`       | string  | Kubernetes workload name                      |
| `namespace`      | string  | Kubernetes namespace                          |
| `cluster`        | string  | Cluster name                                  |
| `pod_name`       | string  | Pod name                                      |
| `container_name` | string  | Container name                                |
| `node_name`      | string  | Node name                                     |
| `level`          | string  | INFO, WARN, ERROR, DEBUG, TRACE, FATAL, PANIC |
| `format`         | string  | json, klog, nginx                             |
| `body_length`    | float   | Log body length in characters                 |
| `body`           | string  | Log body                                      |

Custom attribute fields may be returned by the API alongside these.

## Step 2: Search Raw Logs

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "filters": "level = 'ERROR' AND namespace = 'production'",
  "fields": [
    { "field": "level", "type": "string" },
    { "field": "workload", "type": "string" },
    { "field": "pod_name", "type": "string" }
  ]
}
```

- `fields` is required — use names from discovery
- Returns max 10 rows, sorted by timestamp descending

### Search log body for a keyword

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "filters": "body LIKE '%connection refused%'",
  "fields": [
    { "field": "body", "type": "string" },
    { "field": "workload", "type": "string" },
    { "field": "pod_name", "type": "string" }
  ]
}
```

### Search log body excluding noisy patterns

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "filters": "body LIKE '%timeout%' AND body NOT LIKE '%healthcheck%'",
  "fields": [
    { "field": "body", "type": "string" },
    { "field": "level", "type": "string" },
    { "field": "workload", "type": "string" }
  ]
}
```

### Find unusually large log lines

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "filters": "body_length > 2000 AND namespace = 'production'",
  "fields": [
    { "field": "body", "type": "string" },
    { "field": "body_length", "type": "float" },
    { "field": "pod_name", "type": "string" }
  ]
}
```

## Step 3: Analyze Logs

### Count errors by workload (time-series)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "range",
  "filters": "level = 'ERROR'",
  "groupBy": [{ "field": "workload", "type": "string" }],
  "aggregation": { "function": "row_count" }
}
```

### Count unique pods with errors (instant)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "instant",
  "filters": "level = 'ERROR'",
  "aggregation": {
    "function": "unique_count",
    "fields": [{ "field": "pod_name", "type": "string" }]
  }
}
```

### Count logs matching a body pattern, by workload (time-series)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "range",
  "filters": "body LIKE '%OOMKilled%'",
  "groupBy": [{ "field": "workload", "type": "string" }],
  "aggregation": { "function": "row_count" }
}
```

### Average body length by namespace (instant)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "instant",
  "groupBy": [{ "field": "namespace", "type": "string" }],
  "aggregation": {
    "function": "avg",
    "fields": [{ "field": "body_length", "type": "float" }]
  }
}
```

## Query Types

- `"range"` — time-series values over the given window (for trends)
- `"instant"` — single point-in-time snapshot (for totals/counts)

## Time Ranges

All tools require `from_time` and `to_time` as ISO 8601 strings. Start narrow (15–30 min) and widen if needed.

## Aggregation Functions

| Function                          | Fields Required       | Description               |
| --------------------------------- | --------------------- | ------------------------- |
| `row_count`                       | No                    | Count of matching records |
| `unique_count`                    | Yes (string or float) | Count of distinct values  |
| `avg`, `sum`, `min`, `max`        | Yes (float only)      | Numeric aggregations      |
| `p99`, `p95`, `p90`, `p75`, `p50` | Yes (float only)      | Percentile calculations   |

## Filters

The `filters` parameter accepts a SQL-like WHERE clause.

| Operator          | Example                            | Notes                                              |
| ----------------- | ---------------------------------- | -------------------------------------------------- |
| `=`               | `level = 'ERROR'`                  | Exact match                                        |
| `!=`              | `status != 'ok'`                   | Not equal                                          |
| `>` `<` `>=` `<=` | `body_length > 500`                | Comparisons; use unquoted numbers for float fields |
| `IN`              | `level IN ('ERROR', 'WARN')`       | Matches any value in list                          |
| `NOT IN`          | `namespace NOT IN ('kube-system')` | Excludes values in list                            |
| `LIKE`            | `workload LIKE '%api%'`            | `%` is wildcard                                    |
| `NOT LIKE`        | `pod_name NOT LIKE '%debug%'`      | Negative pattern match                             |

Combine with `AND` / `OR` (use parentheses for grouping):

```
level = 'ERROR' AND namespace = 'production'
```

- **Strings** — always single-quoted: `workload = 'my-service'`
- **Numbers** — unquoted: `body_length > 500`
