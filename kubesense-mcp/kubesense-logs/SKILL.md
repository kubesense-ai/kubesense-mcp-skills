---
name: kubesense-logs
description: Query and analyze logs from Kubernetes clusters using KubeSense MCP tools. Covers field discovery, raw log search, aggregation analysis, and the UnifiedFilter syntax.
---

# KubeSense Logs

Tools for querying and analyzing logs from Kubernetes clusters.

## Tools

| Tool                      | Purpose                                     |
| ------------------------- | ------------------------------------------- |
| `get-trace-or-log-fields` | Discover available fields for logs          |
| `search-logs`             | Browse raw log records (default 10 rows)    |
| `analyze-logs`            | Run aggregated analysis on logs             |

## Discovery-First Rule

**Always discover before querying.** Never guess field names. Attribute keys are window-scoped — pass the same `from_time`/`to_time` to discovery that you'll use for the follow-up search/analyze call.

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

Each returned field includes its `field_type`, `is_attribute`, `allowed_operators`, and an `example` filter leaf you can clone.

### Built-in Log Fields

| Field            | Type   | Values                                        |
| ---------------- | ------ | --------------------------------------------- |
| `workload`       | string | Kubernetes workload name                      |
| `namespace`      | string | Kubernetes namespace                          |
| `cluster`        | string | Cluster name                                  |
| `pod_name`       | string | Pod name                                      |
| `container_name` | string | Container name                                |
| `node_name`      | string | Node name                                     |
| `level`          | string | INFO, WARN, ERROR, DEBUG, TRACE, FATAL, PANIC |
| `format`         | string | json, klog, nginx                             |
| `body_length`    | float  | Log body length in characters                 |

Custom log attribute keys are returned alongside these (set `"type": "attribute"` on attribute leaves).

## Step 2: Search Raw Logs

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "filters": {
    "type": "advanced",
    "adv_filters": {
      "operation": "AND",
      "children": [
        { "field": "level", "operation": "EQ", "values": ["ERROR"], "type": "", "field_type": "string" },
        { "field": "namespace", "operation": "EQ", "values": ["production"], "type": "", "field_type": "string" }
      ]
    }
  },
  "required_fields": [
    { "field": "level", "type": "string" },
    { "field": "workload", "type": "string" },
    { "field": "pod_name", "type": "string" }
  ],
  "page_size": 10
}
```

- `required_fields` is the projection — which columns to include in returned rows
- `page_size` defaults to 10

## Step 3: Analyze Logs

### Count errors by workload (time-series)

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
        { "field": "level", "operation": "EQ", "values": ["ERROR"], "type": "", "field_type": "string" }
      ]
    }
  },
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
  "filters": {
    "type": "advanced",
    "adv_filters": {
      "operation": "AND",
      "children": [
        { "field": "level", "operation": "EQ", "values": ["ERROR"], "type": "", "field_type": "string" }
      ]
    }
  },
  "value_operation": "unique_count",
  "fields": [{ "field": "pod_name", "type": "string" }]
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

## Filters (UnifiedFilter)

`filters` is a structured tree, not a SQL string. See the top-level [SKILL.md](../SKILL.md#filters-unifiedfilter) for the full reference. Quick rules:

- Group nodes: `operation` ∈ {`AND`, `OR`, `NOT`} + `children[]`
- Leaf nodes: `field`, `operation`, `values[]`, `type` (`""` for columns, `"attribute"` for log attributes), `field_type`
- Always use operators from the field's `allowed_operators` (returned by discovery)

### Common log operators

| Operator | Example values | Notes |
| -------- | -------------- | ----- |
| `EQ` | `["ERROR"]` | Exact match |
| `NEQ` | `["ok"]` | Not equal |
| `IN` | `["ERROR", "WARN"]` | Any of |
| `NIN` | `["kube-system"]` | None of |
| `LT` / `GT` / `LTE` / `GTE` | `[500]` | Numeric comparisons |
| `LIKE` | `["%api%"]` | Wildcard match (`%`) |
| `ILIKE` | `["%api%"]` | Case-insensitive wildcard |
| `EXIST` / `NOT_EXIST` | (none) | Presence check, no `values` |

Log attributes (with `"type": "attribute"`) accept the same standard operators — they're stored in attribute maps, not parallel arrays.
