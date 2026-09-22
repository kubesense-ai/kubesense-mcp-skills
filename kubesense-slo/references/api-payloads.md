# KubeSense SLO API — payloads

Every field, every shape, and a working example per SLI type. See
[SKILL.md](../SKILL.md) for the semantics and the traps.

## Auth

Same credentials as the MCP server and the rest of the REST API:

```bash
curl -sS https://<host>/api/slo \
  -H "x-api-key: $KUBESENSE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @slo.json
# or: -H "Authorization: Bearer $ACCESS_TOKEN"
```

Responses are uniformly `{"data": …, "message": "…", "error": false}`. `POST /api/slo`
puts the new id in `data` as a bare string.

## Create / Update body

`POST /api/slo` creates. `PUT /api/slo` updates and is a **full replace** — the id
goes in the body as `id`, and every column is written from what you send.

| Field | Type | Notes |
|---|---|---|
| `id` | string | **PUT only.** The SLO uuid. |
| `name` | string | Required in practice; shown everywhere. |
| `description` | string | Free text. |
| `slo_type` | string | `by_count` (default) \| `time_slice` \| `alert`. |
| `metric` | string | A **label**, not a query. `requests` for traces, the PromQL metric name for metrics, `alert_uptime` for alert SLOs. Filterable on the list page. |
| `slo_target_percentage` | number | e.g. `99.9`. Percentage, not fraction. |
| `warning_target_percentage` | number \| null | Must be **above** the target (UI enforces ≥ target + 0.1). Omit for none. |
| `operation` | string | `time_slice` only: `GT` \| `GTE` \| `LT` \| `LTE` \| `EQ` \| `NEQ` (long forms `less_than`, `greater_than_or_equal`, … also accepted). Send `""` otherwise. |
| `threshold_value` | integer | `time_slice` only — the value `operation` compares against. `0` otherwise. |
| `evaluation_window_days` | integer | Rolling compliance window. 7 / 30 / 90 … |
| `evaluation_time_interval_seconds` | integer | Bucket size; **must be > 0**. Slice size for `time_slice` (use 60 or 300). |
| `evaluate_from` | RFC3339 | Where evaluation starts. Backfilled from here — do not set it months back casually. Defaults to now rounded down to the interval. |
| `evaluation_start_time` | RFC3339 | Clamped forward to `evaluate_from` if earlier. Send the same value. |
| `status` | string | `active` — anything else is never evaluated. |
| `good_events_filter` | QueryConfig | Numerator. `by_count` only (send an empty metrics config for the other types). |
| `total_events_filter` | QueryConfig | Denominator — and the *only* query for `time_slice`; carries `alert_ids` for `alert`. |
| `alert_types` | string[] | `burn_rate_fast`, `burn_rate_slow`, `error_budget_critical`, `error_budget_low`. Generates alert rules. |
| `notification_channels` | integer[] | Channel ids the generated rules page. Must already exist. |
| `workload`, `namespace`, `cluster`, `customer_identifier` | string | **Metadata only** — they label and filter the SLO on the list page, they do **not** scope the query. Put the real scope in the filters. Send `""` when unused. |
| `value` | number | Legacy column. Send `0`. |

### QueryConfig

Identical to an alert rule's `query_config` entry.

```jsonc
{
  "label": "A",                    // positional/cosmetic
  "selectedMode": "traces",        // traces | logs | metrics — DEFAULTS TO traces
  "value_operation": "row_count",  // row_count | unique_count | avg | sum | min | max | p95 | p99
  "fields": [],                    // required for any non-count value_operation: [{"field":"duration","type":"float"}]
  "groupBy": [],                   // [{"field":"workload","type":"string","is_attribute":false}]
  "unified_filter": {              // traces/logs only
    "type": "common",              // "common" | "advanced"
    "common_filter": [ {"field": "app_service", "operation": "IN", "values": ["checkout"]} ],
    "adv_filters": {}
  },
  "queryMode": "code",             // metrics only
  "promql": "",                    // metrics only
  "alert_ids": []                  // alert SLOs only
}
```

`is_free_search` is derived server-side from the filter tree — you do not need to
send it, and a top-level `is_free_search` on the SLO body is ignored.

**Filter operations** (`common_filter[].operation`): `IN`, `NIN`, `EQ`, `NEQ`, `LT`,
`LTE`, `GT`, `GTE`, `LIKE`, `ILIKE`, `NOT_LIKE`, `SUBSTR_ILIKE`, `HAS_TOKEN`,
`HAS_ANY_TOKENS`, `HAS_ALL_TOKENS`. `IN` with a values array is the normal case.

For a nested AND/OR tree set `"type": "advanced"` and fill `adv_filters`:

```json
{
  "type": "advanced",
  "common_filter": [],
  "adv_filters": {
    "operation": "AND",
    "children": [
      {"operation": "IN",  "field": "app_service", "field_type": "string", "values": ["checkout"], "type": "filter"},
      {"operation": "NIN", "field": "return_code", "field_type": "string", "values": ["200"],      "type": "filter"}
    ]
  }
}
```

**Field names come from the alert engine's allow-lists** (`app_service`, `level`,
`return_code`, `pod_name`, …), not the query tools' catalog labels. See
[kubesense-alerts](../../kubesense-alerts/SKILL.md#field-names--a-different-vocabulary).

## Example 1 — `by_count` over traces, grouped

Availability of the checkout service, split per workload.

```json
{
  "name": "Checkout availability",
  "description": "Non-error checkout spans / all checkout spans",
  "slo_type": "by_count",
  "metric": "requests",
  "slo_target_percentage": 99.9,
  "warning_target_percentage": 99.95,
  "evaluation_window_days": 30,
  "evaluation_time_interval_seconds": 60,
  "evaluate_from": "2026-09-01T00:00:00Z",
  "evaluation_start_time": "2026-09-01T00:00:00Z",
  "status": "active",
  "operation": "",
  "threshold_value": 0,
  "value": 0,
  "workload": "", "namespace": "", "cluster": "", "customer_identifier": "",
  "good_events_filter": {
    "label": "A",
    "selectedMode": "traces",
    "value_operation": "row_count",
    "groupBy": [{"field": "workload", "type": "string", "is_attribute": false}],
    "unified_filter": {
      "type": "common",
      "common_filter": [
        {"field": "app_service", "operation": "IN", "values": ["checkout"]},
        {"field": "role",        "operation": "IN", "values": ["server"]},
        {"field": "status",      "operation": "IN", "values": ["ok"]}
      ],
      "adv_filters": {}
    }
  },
  "total_events_filter": {
    "label": "B",
    "selectedMode": "traces",
    "value_operation": "row_count",
    "groupBy": [{"field": "workload", "type": "string", "is_attribute": false}],
    "unified_filter": {
      "type": "common",
      "common_filter": [
        {"field": "app_service", "operation": "IN", "values": ["checkout"]},
        {"field": "role",        "operation": "IN", "values": ["server"]}
      ],
      "adv_filters": {}
    }
  },
  "alert_types": ["burn_rate_fast", "burn_rate_slow", "error_budget_low"],
  "notification_channels": [1]
}
```

The good filter is the total filter **plus** the goodness condition. Keep the two
`groupBy` lists identical.

A latency SLO is the same shape with a duration filter on the good side — trace
`duration` is in **nanoseconds** here, as it is for alerts:

```json
{"field": "duration", "operation": "LTE", "values": [500000000]}
```

## Example 2 — `by_count` over metrics

Both sides are PromQL. Use counters, and the same `[window]` on both.

```json
{
  "name": "Ingress 5xx budget",
  "slo_type": "by_count",
  "metric": "nginx_ingress_controller_requests",
  "slo_target_percentage": 99.5,
  "evaluation_window_days": 30,
  "evaluation_time_interval_seconds": 60,
  "status": "active",
  "operation": "", "threshold_value": 0, "value": 0,
  "good_events_filter": {
    "label": "A", "selectedMode": "metrics", "queryMode": "code", "fields": [],
    "promql": "sum(increase(nginx_ingress_controller_requests{status!~\"5..\"}[1m]))"
  },
  "total_events_filter": {
    "label": "B", "selectedMode": "metrics", "queryMode": "code", "fields": [],
    "promql": "sum(increase(nginx_ingress_controller_requests[1m]))"
  },
  "alert_types": ["burn_rate_fast"],
  "notification_channels": [1]
}
```

Grouped metrics SLOs infer their groups from the **PromQL result labels** — add
`by (…)` to both queries and the label set becomes the group key. No `groupBy` entry
is needed for a metrics SLI.

## Example 3 — `time_slice`

One query, scored once per slice against `operation` + `threshold_value`. A slice is
good when `value <operation> threshold_value`.

```json
{
  "name": "Checkout p99 under 500ms",
  "slo_type": "time_slice",
  "metric": "latency_p99",
  "slo_target_percentage": 99.0,
  "operation": "LTE",
  "threshold_value": 500,
  "evaluation_window_days": 30,
  "evaluation_time_interval_seconds": 60,
  "status": "active",
  "value": 0,
  "good_events_filter": {"label": "A", "selectedMode": "metrics", "queryMode": "code", "promql": "", "fields": []},
  "total_events_filter": {
    "label": "B", "selectedMode": "metrics", "queryMode": "code", "fields": [],
    "promql": "histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket{service=\"checkout\"}[1m]))) * 1000"
  },
  "alert_types": ["error_budget_low"],
  "notification_channels": [1]
}
```

- `good_events_filter` is unused but must be **present** — send the empty metrics
  config above.
- `threshold_value` is an integer in whatever unit the query returns. Make the query
  return the unit you want to write in (the `* 1000` above turns seconds into ms).
- Slice size = `evaluation_time_interval_seconds`. 60 or 300.
- **Missing data counts as uptime.** For a traces/logs `time_slice`, a `row_count`
  of 0 is treated as missing, so a zero-traffic slice is good.

## Example 4 — `alert` (uptime)

Compliance is the share of seconds the named alert rules were **not** firing.

```json
{
  "name": "Payments API uptime",
  "slo_type": "alert",
  "metric": "alert_uptime",
  "slo_target_percentage": 99.9,
  "evaluation_window_days": 30,
  "evaluation_time_interval_seconds": 60,
  "status": "active",
  "operation": "", "threshold_value": 0, "value": 0,
  "total_events_filter": { "alert_ids": ["9f1c…", "2b77…"] },
  "alert_types": ["error_budget_critical"],
  "notification_channels": [1]
}
```

- The ids are **alert rule** uuids — get them from `list-alert-rules` (MCP) or
  `GET /api/alerts/rules`.
- They belong on `total_events_filter.alert_ids`. A top-level `alert_rule_ids` is
  what the UI's *preview* helper emits and the API **ignores** it.
- With an empty `alert_ids` the evaluator skips the SLO entirely rather than
  reporting a perfect 100%.

## Preview — always do this first

`POST /api/slo/preview` computes what compliance *would have been*, over real data,
storing nothing.

```json
{
  "slo_type": "by_count",
  "slo_target_percentage": 99.9,
  "evaluation_window_days": 7,
  "evaluation_time_interval_seconds": 60,
  "operation": "",
  "threshold_value": 0,
  "good_events_filter":  { …same as create… },
  "total_events_filter": { …same as create… }
}
```

Optional `from_time` / `to_time` (RFC3339) override the window; otherwise it is the
last `evaluation_window_days` (defaulting to **7**, not 30).

Response:

```json
{
  "compliance_percentage": 99.93,
  "error_budget_balance": 30.0,
  "total_events": 1284301,
  "good_events": 1283402,
  "bad_events": 899,
  "status": "normal",
  "window_days": 7,
  "groups": [ {"group_key": "…", "group_labels": {"workload": "checkout"}, "compliance_percentage": 99.9, "…": "…"} ]
}
```

`status` is `normal` | `warning` | `breached` | `no_data`. A `no_data` preview with
`total_events: 0` almost always means a wrong field name or an over-narrow filter —
fix that before creating, not after.

> [!NOTE]
> Preview runs through the API's explore engine; the evaluator runs through the
> rule-engine executors. They agree on the common cases but not on every field alias,
> so a clean preview is necessary, not sufficient. Check the first real bucket after
> creating (`GET /api/slo/{id}/metrics`).

## Reading

### List

```bash
curl -sS -X POST "https://<host>/api/slo/list?status=active&current_time=2026-09-22T10:00:00Z&page=1&page_size=25&sort_by=name&sort_order=ASC" \
  -H "x-api-key: $KEY" -H 'Content-Type: application/json' \
  -d '{"filters": [{"field": "status", "operation": "IN", "values": ["breached"]}]}'
```

- `status` (lifecycle) and `current_time` are **query params and required**.
- Body `filters` accept only: `workload`, `namespace`, `cluster`, `name`, `metric`,
  `status`/`status_eval` (`normal` \| `warning` \| `breached` \| `no_data`),
  `burn_rate`/`burn_rate_status`. Anything else is dropped silently.
- `sort_by` must be a real column name (`name`, `workload`, `created`, …); it is not
  validated against an allow-list, so a typo surfaces as a 500.
- Page size defaults to 10.

Each row carries the config plus precomputed rollups:
`total_evaluated_events_last_{2_hour,24_hour,7_days,28_days}`, the matching
`total_good_events_*` / `total_bad_events_*`, `error_budget_balance_percent_*`,
`slo_compliance_percentage_*`, `primary_slo_compliance_percentage`,
`primary_error_budget_balance`, `status_eval`, `burn_rate_status`, `last_evaluated`,
and `count_unit` (`events` \| `slices` \| `seconds`).

### Other reads

| Call | Returns |
|---|---|
| `GET /api/slo/{id}?current_time=…` | one SLO, same shape as a list row |
| `GET /api/slo/search?search=check&limit=50` | `[{id, name}]`; `?id=<uuid>` resolves one name |
| `POST /api/slo/stats` (body `{"filters": []}`) | `{normal, breached, warning, no_data, groups[]}` |
| `GET /api/slo/{id}/metrics?from_time=&to_time=` | good/bad/total, budget, compliance, per-group |
| `GET /api/slo/{id}/groups?windows=last_24_hour,last_7_days` | per group, one figure per window, one scan |
| `GET /api/slo/{id}/metrics/series?current_time=…&stat_duration=daily\|weekly\|monthly` | frame-by-frame history |
| `GET /api/slo/{id}/timeseries?from_time=&to_time=&group_key=&bucket_duration_seconds=` | compliance over time |
| `GET /api/slo/{id}/burn-rate/timeseries?…` | burn rate over time |

`from_time`/`to_time` are required on `/metrics`; the timeseries endpoints default to
the last 7 days and pick their own bucket size when `bucket_duration_seconds` is 0.

### Delete

`DELETE /api/slo/{id}` — soft delete (sets `removed`), and removes the generated
burn-rate alert rules. Evaluations already written to ClickHouse stay until their TTL.
