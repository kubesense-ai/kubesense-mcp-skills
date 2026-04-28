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
  "from_time": "...",
  "to_time": "...",
  "queryType": "range",
  "queries": {
    "A": { "datasource": "logs", ... },
    "B": { "datasource": "traces", ... },
    "C": { "datasource": "formula", "expression": "(A / B) * 100" }
  }
}
```

## Datasource Query Shapes

**logs / traces** — same as `analyze-logs` / `analyze-traces` plus a `datasource` field:

```json
{
  "datasource": "logs",
  "filters": "level = 'ERROR'",
  "groupBy": [{ "field": "workload", "type": "string" }],
  "aggregation": { "function": "row_count" }
}
```

**metrics**:

```json
{
  "datasource": "metrics",
  "promql": "sum(rate(http_requests_total[5m])) by (service)"
}
```

**formula** — references other query labels:

```json
{
  "datasource": "formula",
  "expression": "(A / B) * 100"
}
```

## Example: Error Rate

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "range",
  "queries": {
    "A": {
      "datasource": "traces",
      "filters": "status = 'error'",
      "groupBy": [{ "field": "workload", "type": "string" }],
      "aggregation": { "function": "row_count" }
    },
    "B": {
      "datasource": "traces",
      "groupBy": [{ "field": "workload", "type": "string" }],
      "aggregation": { "function": "row_count" }
    },
    "C": {
      "datasource": "formula",
      "expression": "(A / B) * 100"
    }
  }
}
```

## Tips

- Formula queries can only reference labels defined in the same request
- Use matching `groupBy` fields across queries in a formula — mismatched groups produce unexpected results
