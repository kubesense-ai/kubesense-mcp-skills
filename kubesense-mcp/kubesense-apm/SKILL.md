---
name: kubesense-apm
description: Query and analyze distributed traces (APM) from Kubernetes clusters using KubeSense MCP tools. Covers field discovery, raw span search, latency/error analysis, and filter syntax.
---

# KubeSense APM (Traces)

Tools for querying distributed traces and spans from Kubernetes clusters.

## Tools

| Tool                      | Purpose                                     |
| ------------------------- | ------------------------------------------- |
| `get-trace-or-log-fields` | Discover available fields for traces        |
| `search-traces`           | Browse raw trace/span records (max 10 rows) |
| `analyze-traces`          | Run aggregated analysis on traces           |

## Discovery-First Rule

**Always discover before querying.** Never guess field names.

```
get-trace-or-log-fields  →  search-traces / analyze-traces
```

## Step 1: Discover Fields

```json
{
  "datasource": "traces",
  "search": "",
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z"
}
```

### Built-in Trace Fields

| Field                | Type   | Values                                             |
| -------------------- | ------ | -------------------------------------------------- |
| `status`             | string | ok, error                                          |
| `protocol_type`      | string | HTTP, gRPC, TCP, MongoDB, Redis, MySQL, PostgreSQL |
| `duration`           | float  | Span duration in **microseconds**                  |
| `workload`           | string | Kubernetes workload name                           |
| `namespace`          | string | Kubernetes namespace                               |
| `cluster`            | string | Cluster name                                       |
| `pod_name`           | string | Pod name                                           |
| `node_name`          | string | Node name                                          |
| `role`               | string | client, server                                     |
| `subtype`            | string | GET, POST, PUT, DELETE, PATCH, etc.                |
| `return_code`        | string | 200, 400, 401, 403, 404, 500, 502, 503, 504        |
| `server`             | string | Server workload name                               |
| `client`             | string | Client workload name                               |
| `operation_name`     | string | Span operation name                                |
| `clustered_resource` | string | Resource path (e.g. `/api/v1/users`)               |
| `source`             | string | Trace source (eBPF, OTel)                          |

## Step 2: Search Raw Traces

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "filters": "status = 'error' AND protocol_type = 'HTTP'",
  "fields": [
    { "field": "workload", "type": "string" },
    { "field": "operation_name", "type": "string" },
    { "field": "duration", "type": "float" },
    { "field": "return_code", "type": "string" }
  ]
}
```

## Step 3: Analyze Traces

### P99 latency by workload (time-series)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "range",
  "filters": "protocol_type = 'HTTP'",
  "groupBy": [{ "field": "workload", "type": "string" }],
  "aggregation": {
    "function": "p99",
    "fields": [{ "field": "duration", "type": "float" }]
  }
}
```

### Error count by service and status code (instant)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "instant",
  "filters": "status = 'error'",
  "groupBy": [
    { "field": "workload", "type": "string" },
    { "field": "return_code", "type": "string" }
  ],
  "aggregation": { "function": "row_count" }
}
```

### Average latency for a specific endpoint

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "instant",
  "filters": "workload = 'api-server' AND subtype = 'GET' AND clustered_resource = '/api/v1/users'",
  "aggregation": {
    "function": "avg",
    "fields": [{ "field": "duration", "type": "float" }]
  }
}
```

## Duration Units

`duration` is in **microseconds**. Divide by 1,000 for ms, by 1,000,000 for seconds.

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
| `=`               | `status = 'error'`                 | Exact match                                        |
| `!=`              | `status != 'ok'`                   | Not equal                                          |
| `>` `<` `>=` `<=` | `duration > 1000000`               | Comparisons; use unquoted numbers for float fields |
| `IN`              | `return_code IN ('500', '502')`    | Matches any value in list                          |
| `NOT IN`          | `namespace NOT IN ('kube-system')` | Excludes values in list                            |
| `LIKE`            | `workload LIKE '%api%'`            | `%` is wildcard                                    |
| `NOT LIKE`        | `pod_name NOT LIKE '%debug%'`      | Negative pattern match                             |

Combine with `AND` / `OR` (use parentheses for grouping):

```
status = 'error' AND (workload = 'api-server' OR workload = 'auth-service')
```

- **Strings** — always single-quoted: `workload = 'my-service'`
- **Numbers** — unquoted: `duration > 5000000`
