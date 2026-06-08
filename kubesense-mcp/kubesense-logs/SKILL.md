---
name: kubesense-logs
description: Query and analyze logs from Kubernetes clusters using KubeSense MCP tools. Covers field discovery, raw log search, aggregation analysis, and the WHERE-clause filter syntax.
---

# KubeSense Logs

Tools for querying and analyzing logs from Kubernetes clusters.

## Tools

| Tool                      | Purpose                                     |
| ------------------------- | ------------------------------------------- |
| `get-trace-or-log-fields` | Discover available fields for logs          |
| `search-logs`             | Browse raw log records (default 10 rows)    |
| `analyze-logs`            | Run aggregated analysis on logs             |

## Two Hard Rules (always)

> **1. Discover before querying.** Call `get-trace-or-log-fields` BEFORE every `search-logs` / `analyze-logs`. Attribute keys are window-scoped — pass the same `from_time`/`to_time` you'll use for the follow-up call.
>
> **2. Write `where` with field labels, never raw storage names.** Use the `field` value exactly as discovery returned it: `type = ERROR` (not `level`), `instance = my-pod-xxxx` (not `pod_name`), `node = ...` (not `host`), `container = ...` (not `container_name`).

```
get-trace-or-log-fields  →  search-logs / analyze-logs
```

## Step 1: Discover Fields

```json
{
  "signal": "logs",
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "search": "",
  "limit": 0
}
```

- `signal` — `"logs"` or `"traces"` (required)
- `search` — optional case-insensitive substring filter on field names (e.g. `"namespace"`)
- `limit` — optional cap on returned fields (0 = no cap)

Each returned field includes its `field_type`, `is_attribute`, `allowed_operators`, and an `example` WHERE snippet you can paste straight into the `where` argument.

### Built-in Log Fields

| Field         | Type   | Notes                                          |
| ------------- | ------ | ---------------------------------------------- |
| `workload`    | string | Kubernetes workload name                       |
| `namespace`   | string | Kubernetes namespace                           |
| `cluster`     | string | Cluster name                                   |
| `instance`    | string | Pod instance (storage column: `pod_name`)      |
| `container`   | string | Container name                                 |
| `node`        | string | Node / host name                               |
| `type`        | string | Log level: ERROR, WARN, INFO, DEBUG, TRACE, FATAL, PANIC |
| `format`      | string | json, klog, nginx                              |
| `source`      | string | Log source                                     |
| `region`      | string | Region                                         |
| `app_version` | string | App version                                    |
| `env_type`    | string | Environment type                               |

Custom log attribute keys are returned alongside these — reference them with an `@` prefix in the WHERE clause (e.g. `@request.id = "abc-123"`).

## Step 2: Search Raw Logs

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "where": "type = ERROR AND namespace = production",
  "required_fields": [
    { "field": "type", "type": "string" },
    { "field": "workload", "type": "string" },
    { "field": "instance", "type": "string" }
  ],
  "page_size": 10
}
```

- `where` is a single SQL-style WHERE-clause string. Empty / omitted = match every row in the window.
- `required_fields` is the projection — which columns to include in returned rows.
- `page_size` defaults to 10.

## Step 3: Analyze Logs

### Count errors by workload (time-series)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "range",
  "where": "type = ERROR",
  "group_by_fields": [{ "field": "workload", "type": "string" }],
  "value_operation": "row_count"
}
```

### Count unique pods with errors (instant)

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "where": "type = ERROR",
  "value_operation": "unique_count",
  "fields": [{ "field": "instance", "type": "string" }]
}
```

### Filter on a log attribute

Attributes use the `@` prefix:

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "where": "type = ERROR AND @request.id = \"abc-123\"",
  "value_operation": "row_count"
}
```

### Series cap on range queries

`analyze-logs` with `query_type=range` returns the top 20 series by max value (after dropping all-zero series). The response includes `total_series` and `truncated` so you know if the list was cut. Pass `"limit": <N>` to change the cap.

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

For aggregations that need operand fields, pass them in the top-level `fields` array.

## Filters (WHERE clause)

`where` is a SQL-style string, not a JSON tree. See the top-level [SKILL.md](../SKILL.md#filters-where-clause) for the full reference. Quick rules:

- Combine leaves with `AND`, `OR`, `NOT`; group with parentheses.
- Use the field name as discovery returned it: `type = ERROR`, `instance = my-pod-xxxx`.
- Log attributes use the `@` prefix: `@request.id = "abc-123"`.
- Identifier-shaped values can be bare; anything with spaces or wildcards must be double-quoted: `body ILIKE "%timeout%"`.

### Common log operators

| Operator      | Example                              |
| ------------- | ------------------------------------ |
| `=`           | `type = ERROR`                       |
| `!=`          | `type != INFO`                       |
| `IN`          | `type IN (ERROR, WARN, FATAL)`       |
| `NOT IN`      | `namespace NOT IN (kube-system)`     |
| `<` `>` `<=` `>=` | numeric comparisons              |
| `LIKE`        | `body LIKE "%error%"`                |
| `ILIKE`       | `workload ILIKE "%api%"`             |
| `SUBSTR_ILIKE`| `body SUBSTR_ILIKE timeout`          |

Always check the field's `allowed_operators` in the discovery response — not every operator is valid on every field.
