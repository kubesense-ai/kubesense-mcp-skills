---
name: kubesense-multi-query
description: Run multiple correlated queries across logs, traces, and metrics in a single request, and compute derived values (error rate, ratios) with formula queries via the analyze-telemetry tool.
---

# KubeSense Multi-Query (`analyze-telemetry`)

One MCP call that runs N sub-queries and optionally composes their results with arithmetic. Use when one number depends on another — error rate, success ratio, latency-per-request — or when you'd otherwise issue several `analyze-*` calls and join the results in your head.

## Tools

| Tool                | Purpose                                      |
| ------------------- | -------------------------------------------- |
| `analyze-telemetry` | Multi-datasource queries with formula support |

(`get-trace-or-log-fields` and `get-available-metrics` are still used to discover the field/metric names that go *inside* each sub-query.)

## Three Hard Rules (always)

> **1. Discover before querying.** Each non-formula sub-query targets logs / traces / metrics. Run the appropriate discovery tool BEFORE writing the sub-query (`get-trace-or-log-fields` for logs/traces; `get-available-metrics` + `get-metric-labels` for metrics). Pass the same window you'll use here — attribute keys and metric series are window-scoped.
>
> **2. Write `where`, `group_by_fields`, `fields`, and `sort_by` with catalog labels, never raw storage names.** Same field-name contract as the single-signal tools — `type` not `level`, `instance` not `pod_name`, `service` not `app_service`, `method` not `subtype`, `status_code` not `return_code`. Sending a storage column gets a "use catalog label X" error.
>
> **3. For app identity, group by `service` — not `workload`.** Cross-platform; always populated. `workload` is K8s-specific — use only when the question is explicitly about K8s topology.

## When to Use

- **Computing derived values** — error rate (`errors / total * 100`), success ratio, p99-of-p50.
- **Correlating across datasources** — `errors-in-logs / requests-in-traces` in one call.
- **Replacing multiple `analyze-*` calls** that you'd otherwise stitch together by hand.

If your question is a single aggregation against one signal, use `analyze-logs` / `analyze-traces` / `analyze-metrics` directly — `analyze-telemetry` adds wire-format overhead for no benefit.

## Structure

Queries are keyed by short labels (`A`, `B`, `C`, …). The top-level `from_time` / `to_time` / `query_type` apply to every non-formula sub-query — do **NOT** repeat them inside each sub-query.

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time":   "2026-04-23T10:30:00Z",
  "query_type": "range",
  "queries": {
    "A": { "selectedMode": "logs",   "value_operation": "row_count", "where": "type = ERROR" },
    "B": { "selectedMode": "traces", "value_operation": "row_count", "where": "status = error" },
    "C": { "query_type": "formula",  "expression": "(A / B) * 100",  "label": "error_rate_pct" }
  }
}
```

## Sub-Query Shapes

### logs / traces

Same shape as `analyze-logs` / `analyze-traces`, minus `from_time` / `to_time` / `query_type` (which live at the top level). Use `selectedMode` (not `datasource`) to pick the backend, and pass filters as a `where` string.

```json
{
  "selectedMode": "logs",
  "where": "type = ERROR",
  "group_by_fields": [{ "field": "service", "type": "string" }],
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

Uses `query_type: "formula"` and references other sub-query labels by name. Labels are case-sensitive and must match the keys of sibling sub-queries in the same request.

```json
{
  "query_type": "formula",
  "expression": "(A / B) * 100",
  "label": "error_rate_pct"
}
```

## Example: Error Rate by Service

Count error traces (A) and all traces (B), then compute `(A / B) * 100`. Grouping uses `service` (cross-platform), not `workload` (K8s-only):

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time":   "2026-04-23T10:30:00Z",
  "query_type": "range",
  "queries": {
    "A": {
      "selectedMode": "traces",
      "where": "status = error",
      "group_by_fields": [{ "field": "service", "type": "string" }],
      "value_operation": "row_count"
    },
    "B": {
      "selectedMode": "traces",
      "group_by_fields": [{ "field": "service", "type": "string" }],
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

## Example: Errors-in-Logs vs Requests-in-Traces

Cross-signal — count error log lines (A) and successful trace requests (B), then ratio:

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time":   "2026-04-23T10:30:00Z",
  "query_type": "instant",
  "queries": {
    "A": {
      "selectedMode": "logs",
      "where": "type = ERROR AND namespace = production",
      "value_operation": "row_count"
    },
    "B": {
      "selectedMode": "traces",
      "where": "status = ok AND namespace = production",
      "value_operation": "row_count"
    },
    "C": {
      "query_type": "formula",
      "expression": "A / B",
      "label": "errors_per_request"
    }
  }
}
```

## Discriminator Reference

| Sub-query type | Discriminator field | Value       |
| -------------- | ------------------- | ----------- |
| logs           | `selectedMode`      | `"logs"`    |
| traces         | `selectedMode`      | `"traces"`  |
| metrics        | `selectedMode`      | `"metrics"` |
| formula        | `query_type`        | `"formula"` |

## Tips

- Formula queries can only reference labels (`A`, `B`, …) defined in the **same request** — no cross-request references.
- Use **matching `group_by_fields` across sub-queries** that feed a formula. Mismatched groups produce unexpected joins or empty results.
- Validate every logs/traces `where` clause against discovery's `allowed_operators` (trace attributes use the `@` prefix; the server auto-remaps them to `ARRAY_MAP*`).
- Sub-queries inherit `from_time` / `to_time` / `query_type` from the top level — do not repeat.
- Range queries with formulas return one series per group key per result label — keep group cardinality small or you'll exhaust the LLM token budget.

## See Also

- [kubesense-logs](../kubesense-logs/SKILL.md) — single-signal log queries
- [kubesense-apm](../kubesense-apm/SKILL.md) — single-signal trace queries
- [kubesense-metrics](../kubesense-metrics/SKILL.md) — PromQL discovery and execution
