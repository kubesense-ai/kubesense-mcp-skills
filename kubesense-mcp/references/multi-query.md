# Multi-Query and Formulas (`analyze-telemetry`)

Runs several queries across logs, traces, and metrics in **one** request, and composes them
with formulas. This is the only way to get a ratio, error rate, or percentage — no single
`analyze-*` call can divide one series by another.

## When to Use

- Any derived value: error rate, success rate, a share of total, a ratio
- Correlating two datasources in one call (e.g. log errors against request volume)
- Replacing several `analyze-*` round-trips

For one aggregation over one datasource, use `analyze-logs` / `analyze-traces` /
`analyze-metrics` — they are simpler and return the same shape.

## Structure

```json
{
  "from_time": "2026-07-30T10:00:00Z",
  "to_time": "2026-07-30T11:00:00Z",
  "query_type": "range",
  "queries": {
    "A": { "selectedMode": "traces", "where": "status = error", "value_operation": "row_count" },
    "B": { "selectedMode": "traces", "value_operation": "row_count" },
    "C": { "query_type": "formula", "expression": "(A/B)*100" }
  }
}
```

Top-level `from_time`, `to_time`, `query_type`, and `queries` are all required. The
top-level `query_type` is `range` or `instant` and applies to every sub-query.

Query keys are single-letter labels: `A`, `B`, `C`, …

## Discriminators — get these exactly right

| Sub-query kind | Discriminator |
|---|---|
| logs | `"selectedMode": "logs"` |
| traces | `"selectedMode": "traces"` |
| metrics | `"selectedMode": "metrics"` |
| formula | `"query_type": "formula"` (or `"queryType": "formula"`) |

> [!WARNING]
> **A formula is identified by `query_type`, not `selectedMode`.** And there is no
> `datasource` field — the tool's own description shows
> `{"datasource": "formula", "expression": "(A/B)*100"}`, which is **wrong**; `datasource`
> is never read.
>
> **An omitted `selectedMode` silently defaults to `metrics`.** A logs sub-query missing it
> is parsed as a metrics query and returns nothing useful. Always set it explicitly.

## Sub-Query Shapes

### Logs / traces

Same fields as `analyze-logs` / `analyze-traces`. `selectedMode` and `value_operation` are
required.

```json
{
  "selectedMode": "logs",
  "where": "type = ERROR",
  "group_by_fields": [ { "field": "workload", "is_attribute": false } ],
  "value_operation": "row_count",
  "clusters": [],
  "sort_direction": "DESC"
}
```

Field names follow the normal catalog-label contract — `type` for log severity, `service`
for trace identity. See [field-catalog.md](./field-catalog.md).

### Metrics

`selectedMode` and `promql` both required.

```json
{ "selectedMode": "metrics", "promql": "sum(rate(container_cpu_usage_seconds_total{container!=''}[5m])) by (namespace)" }
```

### Formula

`query_type` and `expression` required.

```json
{ "query_type": "formula", "expression": "(A/B)*100" }
```

Expressions reference other labels in the **same** request. Arithmetic: `+ - * /` and
parentheses.

## Matching Group-By Across Queries

> [!IMPORTANT]
> Queries combined in a formula must use the **same `group_by_fields`**. The formula engine
> matches series by their labels — mismatched grouping produces empty or nonsensical
> results, not an error.

If `A` groups by `workload` and `B` doesn't group at all, `A/B` cannot pair the series.
Either group both, or group neither.

## Examples

### Trace error rate per workload

```json
{
  "from_time": "2026-07-30T10:00:00Z",
  "to_time": "2026-07-30T11:00:00Z",
  "query_type": "range",
  "queries": {
    "A": {
      "selectedMode": "traces",
      "where": "status = error",
      "group_by_fields": [ { "field": "workload", "is_attribute": false } ],
      "value_operation": "row_count"
    },
    "B": {
      "selectedMode": "traces",
      "group_by_fields": [ { "field": "workload", "is_attribute": false } ],
      "value_operation": "row_count"
    },
    "C": { "query_type": "formula", "expression": "(A/B)*100" }
  }
}
```

### Log error rate as a share of all logs

```json
{
  "from_time": "2026-07-30T10:00:00Z",
  "to_time": "2026-07-30T11:00:00Z",
  "query_type": "instant",
  "queries": {
    "A": { "selectedMode": "logs", "where": "type = ERROR", "value_operation": "row_count" },
    "B": { "selectedMode": "logs", "value_operation": "row_count" },
    "C": { "query_type": "formula", "expression": "(A/B)*100" }
  }
}
```

### 5xx share of HTTP requests

```json
{
  "from_time": "2026-07-30T10:00:00Z",
  "to_time": "2026-07-30T11:00:00Z",
  "query_type": "range",
  "queries": {
    "A": {
      "selectedMode": "traces",
      "where": "protocol = HTTP AND status_code LIKE \"5%\"",
      "group_by_fields": [ { "field": "service", "is_attribute": false } ],
      "value_operation": "row_count"
    },
    "B": {
      "selectedMode": "traces",
      "where": "protocol = HTTP",
      "group_by_fields": [ { "field": "service", "is_attribute": false } ],
      "value_operation": "row_count"
    },
    "C": { "query_type": "formula", "expression": "(A/B)*100" }
  }
}
```

### Log errors against request volume (cross-signal)

```json
{
  "from_time": "2026-07-30T10:00:00Z",
  "to_time": "2026-07-30T11:00:00Z",
  "query_type": "range",
  "queries": {
    "A": {
      "selectedMode": "logs",
      "where": "type = ERROR",
      "group_by_fields": [ { "field": "workload", "is_attribute": false } ],
      "value_operation": "row_count"
    },
    "B": {
      "selectedMode": "traces",
      "group_by_fields": [ { "field": "workload", "is_attribute": false } ],
      "value_operation": "row_count"
    },
    "C": { "query_type": "formula", "expression": "A/B" }
  }
}
```

Both sides group by `workload` — the one identity field that means the same thing on both
signals. Grouping logs by `workload` and traces by `service` would not pair.

### Latency alongside throughput (no formula)

Formulas are optional; use `analyze-telemetry` purely to save round-trips:

```json
{
  "from_time": "2026-07-30T10:00:00Z",
  "to_time": "2026-07-30T11:00:00Z",
  "query_type": "range",
  "queries": {
    "A": {
      "selectedMode": "traces",
      "group_by_fields": [ { "field": "service", "is_attribute": false } ],
      "fields": [ { "field": "duration", "is_attribute": false } ],
      "value_operation": "p95"
    },
    "B": {
      "selectedMode": "traces",
      "group_by_fields": [ { "field": "service", "is_attribute": false } ],
      "value_operation": "row_count"
    }
  }
}
```

`A`'s values are in **nanoseconds** (aggregated trace `duration`).

## Output

Columnar JSON with one `results` entry per label you supplied — including the formula's.
For `range` queries there is additionally a `series_meta` keyed by the same labels.

Each entry holds `series` (an array of `{labels, ...}`) plus `bucket_duration_seconds`, and
optionally `promql`, `resource`, or `error_message`.

- `range`: a shared `timestamps` array (Unix seconds, emitted once) with each series
  carrying a positionally aligned `values` array; `null` = no data in that bucket.
- `instant`: each series carries one scalar `value`.

A sub-query that fails reports an `error_message` on its own entry rather than failing the
whole call — check for it before trusting a formula that depends on it.

## RBAC

`analyze-telemetry` resolves permissions for **every module its sub-queries touch** —
`logs`, `traces`, and `infrastructure` for metrics. A mixed request needs access to all of
them; the error names the module that failed.

## Rules

1. `selectedMode` on every logs/traces/metrics sub-query — omitting it silently defaults to
   `metrics`.
2. Formulas use `query_type: "formula"`, never `selectedMode`. There is no `datasource`
   field.
3. Formula operands need **matching `group_by_fields`**, or the series cannot pair.
4. `value_operation` is required on logs/traces sub-queries, and it is `row_count`, not
   `count`.
5. One top-level `query_type` (`range` or `instant`) governs every sub-query.
6. Check each entry for `error_message` before reporting a formula result.
7. Use `analyze-*` for a single aggregation; reach for this tool when you need a ratio or
   want to save round-trips.
