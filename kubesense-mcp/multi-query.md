# Multi-Query Reference (analyze-telemetry)

`analyze-telemetry` runs multiple queries across logs, traces, and metrics in a single request and supports **formula queries** that compute derived values from other query results.

## When to Use

- Computing derived values (e.g. error rate = errors / total \* 100)
- Correlating data across datasources in one call
- Replacing multiple separate `analyze-*` calls with a single request

## Structure

Queries are keyed by short labels (`A`, `B`, `C`, etc.):

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "range",
  "queries": {
    "A": { "selectedMode": "logs",    "value_operation": "row_count", "where": "type = ERROR" },
    "B": { "selectedMode": "traces",  "value_operation": "row_count", "where": "status = error" },
    "C": { "query_type": "formula", "expression": "(A / B) * 100" }
  }
}
```

Top-level `from_time` / `to_time` / `query_type` apply to every non-formula sub-query — do **not** repeat them inside each sub-query.

## Sub-Query Shapes

### logs / traces

Same shape as `analyze-logs` / `analyze-traces`, minus `from_time`/`to_time`/`query_type` (which live at the top level). Use `selectedMode` (not `datasource`) to pick the backend, and pass filters as a `where` string:

```json
{
  "selectedMode": "logs",
  "where": "type = ERROR",
  "group_by_fields": [{ "field": "workload", "type": "string" }],
  "value_operation": "row_count"
}
```

### metrics

```json
{
  "selectedMode": "metrics",
  "promql": "sum(rate(http_requests_total[5m])) by (service)"
}
```

### formula

Uses `query_type: "formula"` and references other sub-query labels:

```json
{
  "query_type": "formula",
  "expression": "(A / B) * 100",
  "label": "error_rate_pct"
}
```

## Example: Error Rate by Workload

Count error traces (A) and all traces (B), then compute `(A / B) * 100`:

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "query_type": "range",
  "queries": {
    "A": {
      "selectedMode": "traces",
      "where": "status = error",
      "group_by_fields": [{ "field": "workload", "type": "string" }],
      "value_operation": "row_count"
    },
    "B": {
      "selectedMode": "traces",
      "group_by_fields": [{ "field": "workload", "type": "string" }],
      "value_operation": "row_count"
    },
    "C": {
      "query_type": "formula",
      "expression": "(A / B) * 100",
      "label": "error_rate_pct"
    }
  }
}
```

## Discriminator Reference

| Sub-query type | Discriminator field          | Value                |
| -------------- | ---------------------------- | -------------------- |
| logs           | `selectedMode`               | `"logs"`             |
| traces         | `selectedMode`               | `"traces"`           |
| metrics        | `selectedMode`               | `"metrics"`          |
| formula        | `query_type`                 | `"formula"`          |

## Tips

- Formula queries can only reference labels defined in the same request
- Use matching `group_by_fields` across queries in a formula — mismatched groups produce unexpected results
- Validate any logs/traces `where` clause against the discovery `allowed_operators` (trace attributes use the `@` prefix; the server auto-remaps them to `ARRAY_MAP*`)
- Sub-queries inherit `from_time`/`to_time`/`query_type` from the top level
