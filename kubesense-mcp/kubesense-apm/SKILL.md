---
name: kubesense-apm
description: Query and analyze distributed traces (APM) from Kubernetes clusters using KubeSense MCP tools. Covers field discovery, raw span search, latency/error analysis, and the WHERE-clause filter syntax — including how trace-attribute filters are auto-remapped.
---

# KubeSense APM (Traces)

Tools for querying distributed traces and spans from Kubernetes clusters.

## Tools

| Tool                      | Purpose                                      |
| ------------------------- | -------------------------------------------- |
| `get-trace-or-log-fields` | Discover available fields for traces         |
| `search-traces`           | Browse raw trace/span records (default 10 rows) |
| `analyze-traces`          | Run aggregated analysis on traces            |

## Three Hard Rules (always)

> **1. Discover before querying.** Call `get-trace-or-log-fields` BEFORE every `search-traces` / `analyze-traces`. Trace attribute keys vary by deployment and are window-scoped — pass the same `from_time`/`to_time` you'll use for the follow-up call.
>
> **2. Write `where`, `group_by_fields`, `fields`, `required_fields`, and `sort_by` with catalog labels, never raw storage names.** Use the `field` value exactly as discovery returned it. Sending a storage column gets you a "use the catalog label 'X' instead" error.
> - `service = checkout-api` (not `app_service`)
> - `instance = my-pod-xxxx` (not `pod_name`)
> - `protocol = HTTP` (not `protocol_type`)
> - `role = server` (not `kind`)
> - `method = POST` (not `subtype`)
> - `status_code = 500` (not `return_code`)
> - `resource = "/api/v1/users"` (not `clustered_resource`)
> - `container = ...` (not `container_name`)
>
> **3. For app identity, group by `service` — not `workload`.** `service` is cross-platform (k8s, docker, legacy) and is always populated. `workload` is K8s-specific. Use `workload` ONLY when the user explicitly asks about K8s topology ("group by deployment", "errors per statefulset"). For *any* "top services", "errors by app", "P99 by service", "which microservice…" question — group by `service`.

```
get-trace-or-log-fields  →  search-traces / analyze-traces
```

## Trace Attributes

Trace attributes are stored as parallel `attribute_names[]` / `attribute_values[]` arrays internally, but in the WHERE clause **you write them with the same syntax as everything else** — just carry an `@` prefix:

```
@http.method = GET
@db.system = postgresql
@user.id IN ("abc-123", "def-456")
@http.target LIKE "/api/v1/%"
```

The server transparently remaps these to the internal `ARRAY_MAP*` operators. You no longer need to know about `ARRAY_MAP`, `ARRAY_MAP_LIKE`, or any of the parallel-array machinery.

Top-level trace columns (`workload`, `namespace`, `duration`, etc.) use the bare name without `@`.

## Step 1: Discover Fields

```json
{
  "signal": "traces",
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "search": "",
  "limit": 0
}
```

### Built-in Trace Fields

| Field            | Type   | Notes                                                |
| ---------------- | ------ | ---------------------------------------------------- |
| `status`         | string | `error`, `ok`                                        |
| `protocol`       | string | HTTP, gRPC, TCP, MongoDB, Redis, MySQL, PostgreSQL   |
| `duration`       | int    | Span duration in microseconds                        |
| `service`        | string | **PREFERRED for app identity** — cross-platform (k8s, docker, legacy). Use this for "top services", "errors by app", "P99 by service". (storage: `app_service`) |
| `workload`       | string | Kubernetes workload name. Use ONLY when the question is explicitly about K8s topology (deployment/statefulset). For app identity, prefer `service`. |
| `namespace`      | string | Kubernetes namespace                                 |
| `cluster`        | string | Cluster name                                         |
| `instance`       | string | Pod instance (storage column: `pod_name`)            |
| `container`      | string | Container name                                       |
| `role`           | string | `client`, `server` (storage column: `kind`)          |
| `method`         | string | GET, POST, PUT, DELETE, PATCH, … (storage: `subtype`)|
| `status_code`    | int    | HTTP/RPC return code (storage: `return_code`)        |
| `server`         | string | Server workload name                                 |
| `client`         | string | Client workload name                                 |
| `operation_name` | string | Span operation name                                  |
| `resource`       | string | Resource path, e.g. `/api/v1/users` (storage: `clustered_resource`) |
| `source`         | string | Trace source (`eBPF`, `OTel`)                        |
| `request_type`   | bool   | External vs internal (storage: `is_external`)        |

Custom trace attribute keys (e.g. `http.method`, `db.statement`) are returned alongside these — reference them with `@http.method = GET` in the WHERE clause.

## Step 2: Search Raw Traces

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "where": "status = error AND protocol = HTTP",
  "required_fields": [
    { "field": "workload", "type": "string" },
    { "field": "operation_name", "type": "string" },
    { "field": "duration", "type": "float" },
    { "field": "status_code", "type": "string" }
  ],
  "page_size": 10
}
```

## Step 3: Analyze Traces

### P99 latency by workload (time-series)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "range",
  "where": "protocol = HTTP",
  "group_by_fields": [{ "field": "workload", "type": "string" }],
  "value_operation": "p99",
  "fields": [{ "field": "duration", "type": "float" }]
}
```

### Top 5 services by error count (instant)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "where": "status = error",
  "group_by_fields": [{ "field": "service", "type": "string" }],
  "value_operation": "row_count",
  "sort_direction": "DESC",
  "limit": 5
}
```

### Error count by service and status code (instant)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "where": "status = error",
  "group_by_fields": [
    { "field": "service", "type": "string" },
    { "field": "status_code", "type": "string" }
  ],
  "value_operation": "row_count"
}
```

### Filtering on a trace attribute (e.g. http.method)

Attributes use the `@` prefix and the same operators as columns — the server handles the array-map remap:

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "where": "workload = api-server AND @http.method = GET",
  "value_operation": "avg",
  "fields": [{ "field": "duration", "type": "float" }]
}
```

### Series cap on range queries

`analyze-traces` with `query_type=range` returns the top 20 series by max value (after dropping all-zero series). The response includes `total_series` and `truncated`. Pass `"limit": <N>` to change the cap.

## Duration Units

`duration` is in **microseconds**. Divide by 1,000 for ms, by 1,000,000 for seconds.

## Query Types

- `"range"` — time-series values over the given window (for trends)
- `"instant"` — single point-in-time snapshot (for totals/counts)

## Aggregation Functions (`value_operation`)

| Function                          | Fields Required       | Description               |
| --------------------------------- | --------------------- | ------------------------- |
| `row_count`                       | No                    | Count of matching records |
| `unique_count`                    | Yes (string or float) | Count of distinct values  |
| `avg`, `sum`, `min`, `max`        | Yes (float only)      | Numeric aggregations      |
| `p99`, `p95`, `p90`, `p75`, `p50` | Yes (float only)      | Percentile calculations   |

## Filters (WHERE clause)

`where` is a SQL-style string. See the top-level [SKILL.md](../SKILL.md#filters-where-clause) for the full reference. Key reminders for traces:

- Top-level columns use the catalog labels: `status = error`, `service = checkout-api`, `instance = my-pod-xxxx`, `role = server`, `method = POST`.
- Trace attributes use the `@` prefix: `@http.method = POST`, `@db.statement ILIKE "%select%"`. The server remaps these to the internal `ARRAY_MAP*` operators automatically.
- Identifier-shaped values can be bare; anything with spaces, quotes, or wildcards must be double-quoted: `@http.target LIKE "/api/v1/%"`.
- Always check the field's `allowed_operators` returned by discovery, or copy the discovery `example` snippet verbatim.
