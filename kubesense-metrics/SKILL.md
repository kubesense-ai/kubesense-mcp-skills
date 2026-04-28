---
name: kubesense-metrics
description: Query and analyze Kubernetes metrics using KubeSense MCP tools. Covers metric discovery, label inspection, and PromQL queries.
---

# KubeSense Metrics

Tools for discovering and querying Kubernetes metrics via PromQL.

## Tools

| Tool                   | Purpose                               |
| ---------------------- | ------------------------------------- |
| `get-available-metrics`| Discover available metric names       |
| `get-metric-labels`    | Get label names for a specific metric |
| `analyze-metrics`      | Execute PromQL queries on metrics     |

## Discovery-First Rule

**Always discover before querying.** Never guess metric names or labels.

```
get-available-metrics  →  get-metric-labels  →  analyze-metrics
```

## Step 1: Discover Metrics

All keywords are AND-matched (case-insensitive):

```json
{ "search_keywords": ["cpu"] }
```

```json
{ "search_keywords": ["request", "duration"] }
```

## Step 2: Get Labels

```json
{ "name": "container_cpu_usage_seconds_total" }
```

Returns label names like `namespace`, `pod`, `container`. Use these in PromQL selectors.

## Step 3: Query with PromQL

### CPU usage rate by namespace

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "range",
  "promql": "sum(rate(container_cpu_usage_seconds_total[5m])) by (namespace)"
}
```

### Memory usage by pod in a namespace

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "instant",
  "promql": "sum(container_memory_usage_bytes{namespace='production'}) by (pod)"
}
```

### HTTP request rate by service

```json
{
  "from_time": "2026-04-23T10:00:00Z",
  "to_time": "2026-04-23T10:30:00Z",
  "queryType": "range",
  "promql": "sum(rate(http_requests_total[5m])) by (service)"
}
```

## Common PromQL Patterns

| Pattern                                             | Use Case                     |
| --------------------------------------------------- | ---------------------------- |
| `rate(metric[5m])`                                  | Per-second rate of a counter |
| `sum(...) by (label)`                               | Aggregate across series      |
| `histogram_quantile(0.99, rate(metric_bucket[5m]))` | P99 from a histogram         |
| `increase(metric[1h])`                              | Total increase over a window |
| `topk(10, metric)`                                  | Top 10 series by value       |
| `metric{label="value"}`                             | Exact label filter           |
| `metric{label=~"regex.*"}`                          | Regex label filter           |

## Query Types

- `"range"` — time-series values over the given window (for trends)
- `"instant"` — single point-in-time snapshot (for current values)

## Time Ranges

All tools require `from_time` and `to_time` as ISO 8601 strings. Start narrow (15–30 min) and widen if needed.

## Tips

- Always use `get-available-metrics` first — don't guess metric names
- Use `get-metric-labels` before writing label filters in PromQL
- Use `[5m]` in `rate()` for general use; `[1m]` for high-resolution, `[15m]` for smoother results
