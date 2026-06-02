---
name: kubesense-apm
description: Query and analyze distributed traces (APM) from Kubernetes clusters using KubeSense MCP tools. Covers field discovery, raw span search, latency/error analysis, and the UnifiedFilter syntax — including the ARRAY_MAP rule for trace attributes.
---

# KubeSense APM (Traces)

Tools for querying distributed traces and spans from Kubernetes clusters.

## Tools

| Tool                      | Purpose                                      |
| ------------------------- | -------------------------------------------- |
| `get-trace-or-log-fields` | Discover available fields for traces         |
| `search-traces`           | Browse raw trace/span records (default 10 rows) |
| `analyze-traces`          | Run aggregated analysis on traces            |

## Discovery-First Rule

**Always discover before querying.** Trace attribute keys vary by deployment and are window-scoped — pass the same `from_time`/`to_time` to discovery that you'll use for the follow-up call.

```
get-trace-or-log-fields  →  search-traces / analyze-traces
```

## Trace Attributes Are Special

Trace attributes are stored as parallel `attribute_names[]` / `attribute_values[]` arrays. They reject standard operators like `EQ` or `LIKE`. **Use only `ARRAY_MAP*` operators** on any leaf where `"type": "attribute"`:

| Operator             | Use                                        |
| -------------------- | ------------------------------------------ |
| `ARRAY_MAP`          | attribute equals one of the given values   |
| `NOT_ARRAY_MAP`      | attribute does not equal any given value   |
| `ARRAY_MAP_LIKE`     | wildcard match against attribute values    |
| `NOT_ARRAY_MAP_LIKE` | negated wildcard                           |
| `ARRAY_MAP_ILIKE`    | case-insensitive wildcard                  |
| `NOT_ARRAY_MAP_ILIKE`| negated case-insensitive wildcard          |

Trying `EQ` on a trace attribute will fail validation with a path-pointed error like `adv_filters.children[1]: operator "EQ" not allowed for traces attribute field "http.method"`. The `example` leaf returned by discovery already uses `ARRAY_MAP` for trace attributes — just clone it.

Top-level trace columns (`workload`, `namespace`, `duration`, etc.) keep using the standard operators.

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

Custom trace attribute keys (e.g. `http.method`, `db.statement`) are returned alongside these and must use `ARRAY_MAP*` operators.

## Step 2: Search Raw Traces

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "filters": {
    "type": "advanced",
    "adv_filters": {
      "operation": "AND",
      "children": [
        { "field": "status", "operation": "EQ", "values": ["error"], "type": "", "field_type": "string" },
        { "field": "protocol_type", "operation": "EQ", "values": ["HTTP"], "type": "", "field_type": "string" }
      ]
    }
  },
  "required_fields": [
    { "field": "workload", "type": "string" },
    { "field": "operation_name", "type": "string" },
    { "field": "duration", "type": "float" },
    { "field": "return_code", "type": "string" }
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
  "filters": {
    "type": "advanced",
    "adv_filters": {
      "operation": "AND",
      "children": [
        { "field": "protocol_type", "operation": "EQ", "values": ["HTTP"], "type": "", "field_type": "string" }
      ]
    }
  },
  "group_by_fields": [{ "field": "workload", "type": "string" }],
  "value_operation": "p99",
  "fields": [{ "field": "duration", "type": "float" }]
}
```

### Error count by service and status code (instant)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "filters": {
    "type": "advanced",
    "adv_filters": {
      "operation": "AND",
      "children": [
        { "field": "status", "operation": "EQ", "values": ["error"], "type": "", "field_type": "string" }
      ]
    }
  },
  "group_by_fields": [
    { "field": "workload", "type": "string" },
    { "field": "return_code", "type": "string" }
  ],
  "value_operation": "row_count"
}
```

### Filtering on a trace attribute (e.g. http.method)

Attribute leaves use `"type": "attribute"` and `ARRAY_MAP`:

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "filters": {
    "type": "advanced",
    "adv_filters": {
      "operation": "AND",
      "children": [
        { "field": "workload", "operation": "EQ", "values": ["api-server"], "type": "", "field_type": "string" },
        { "field": "http.method", "operation": "ARRAY_MAP", "values": ["GET"], "type": "attribute", "field_type": "string" }
      ]
    }
  },
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

## Filters (UnifiedFilter)

`filters` is a structured tree, not a SQL string. See the top-level [SKILL.md](../SKILL.md#filters-unifiedfilter) for the full reference. Key reminders for traces:

- Top-level columns → standard operators (`EQ`, `IN`, `LIKE`, comparisons, ...)
- Trace attributes (`"type": "attribute"`) → **`ARRAY_MAP*` operators only**
- Always check the field's `allowed_operators` returned by discovery, or clone the discovery `example` leaf
