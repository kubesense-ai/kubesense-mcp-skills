# Alert Rule Import JSON

The import/export format for KubeSense alert rules. This is the shape the **Export** button
produces, so an exported rule can be edited and re-imported.

Applied via **Alerts → Alert Rules → Import JSON** → review in the editor → Create. Nothing
is written until the user confirms.

> [!NOTE]
> This format is the **GET response shape**, not the API request body. The importer converts
> it to the POST body client-side (nesting the threshold, renaming durations to
> `*_prometheus_format`, renaming `notification_channel_ids` → `notificationChannels`). You
> write the flat form documented here.

> [!IMPORTANT]
> Run every document you build through **`validate-alert-json`** before handing it over.
> It checks this exact shape and reports each problem as a JSON Pointer plus a reason, so
> a rule that comes back `valid=true` is one the importer accepts. Everything documented
> below is a rule that check enforces for you.

## Top-Level Fields

```json
{
  "name": "High pod CPU {{pod}}",
  "description": "Pod CPU above 80% for 5 minutes",
  "enabled": true,
  "query_type": "metrics",
  "query_config": [ /* see below */ ],
  "metric_query_label": "A",
  "raw_query": "",
  "threshold_operator": "greater_than",
  "threshold_value": 0.8,
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "severity": "warning",
  "labels": {},
  "notification_channel_ids": [1],
  "route_by_labels": false,
  "no_data_state": "normal",
  "include_samples": false,
  "sample_limit": 5,
  "unit": "CPU"
}
```

| Field | Values / notes |
|---|---|
| `name` | **Required.** Editor enforces ≥ 3 characters. `{{field}}` placeholders resolve per firing series and must match a group-by key. |
| `description` | Free text, shown to whoever receives the page. |
| `enabled` | **Ignored** — the server hardcodes `true`. |
| `query_type` | **Ignored** — derived from `query_config[0].selectedMode`. |
| `query_config` | **Required, non-empty array.** |
| `metric_query_label` | Label of the thresholded query. Single query → `"A"`; formula → the formula's label. Not cross-checked against the queries. |
| `raw_query` | Ignored on import. |
| `threshold_operator` | `greater_than` \| `greater_than_or_equal` \| `less_than` \| `less_than_or_equal` \| `equals` \| `not_equals`. Anything else silently falls back to `greater_than`. (`above`/`below` work in the MCP tool but **not** here.) |
| `threshold_value` | Number. |
| `condition_type` | `threshold` (canonical) \| `change` \| `change_percent` \| `new_value`. `""` also resolves to threshold. |
| `compared_to` | Duration **string** (`"1h"`) — required for `change`, `change_percent`, `new_value`. |
| `evaluation_interval` | How often the rule runs: `30s`, `1m`, `5m`, `1h`, `1d`. Plain string. |
| `time_window` | How far back the query looks. Plain string. |
| `frequency_type` | `at_least_once` \| `more_than_once` \| `always`. See the `always` trap below. |
| `breaches_count` | Integer ≥ 2 — only with `more_than_once`. |
| `breach_counting_window_prometheus_format` | Optional window. With `more_than_once`, the span the breaches are counted over; with `always`, the span the condition must hold across. Ignored for `at_least_once`. Omitted → the engine falls back to `time_window`. **Note the name** — see round-trip trap. |
| `severity` | `critical` \| `error` \| `warning` \| `info`. (The MCP tool allows only critical/warning/info.) |
| `labels` | `{"team": "infra"}` |
| `notification_channel_ids` | Array of **integer** channel ids from `list-notification-channels`. **`[]` blocks a single-rule import.** |
| `route_by_labels` | `false` → route to the listed channels. `true` → route via each channel's own label matchers, and `notification_channel_ids` is **discarded**. |
| `no_data_state` | `normal` (default) \| `firing` \| `previous` |
| `include_samples` / `sample_limit` | **Logs only** — attach matching rows to notifications. `sample_limit` 1–100. |
| `unit` | Display only. Must be a real formatter value — see below. |

### `unit` values

The enum is the dashboard y-axis formatter list. Common valid values:

```
auto  number  raw  percentage
nanoseconds  microseconds  milliseconds  seconds  minutes  hours  days
bytes  bytes_iec  bytes_si  kilobytes  megabytes  gigabytes
bytes/sec  packets_per_sec
mCPU  CPU
```

> [!WARNING]
> `ns`, `ms`, `percent`, `percent_unit`, `short` **do not exist** and silently become
> `auto`. Use `nanoseconds`, `milliseconds`, `percentage`, `number`.

Pick to match the value: `nanoseconds` for trace latency · `bytes` for byte metrics ·
`percentage` for a formula that already multiplies by 100 · `CPU`/`mCPU` for CPU ·
`number`/`raw` for plain counts.

### The `always` trap

Import maps only `more_than_once` specially; **everything else becomes
`at_least_once`**. To actually get `always`, send both:

```json
"frequency_type": "always",
"threshold_frequency": "always"
```

Export emits only `frequency_type`, so `always` silently downgrades on a round-trip.

An `always` rule also honours `breach_counting_window_prometheus_format` — the condition
must hold across that whole span, and without one the engine falls back to `time_window`.
Set it whenever the "must hold for N minutes" part is the point of the rule; leave it out
when `time_window` already is that span.

### The `breach_counting_window` trap

Import reads **`breach_counting_window_prometheus_format`**; export writes
`breach_counting_window`. The round-trip is broken for this one field — re-add the
`_prometheus_format` name when re-importing an exported rule that used it.

**Send both keys.** webapp#2081 (open against `dev` as of 2026-08-13) flips import to read
the plain `breach_counting_window`, which fixes the round-trip but inverts this trap. A
document carrying both names imports correctly before and after that change; the unread key
is ignored either way.

## `query_config[]`

Every entry carries these keys. **`label` is not one of them** — labels bind
**positionally**: index 0 → `A`, index 1 → `B`, index 2 → `C`. `labelOptions: {"label": "A"}`
is conventional but is rewritten to `{"type": "auto"}` on save, so position is the only
durable identity.

Shared keys: `variables` (`[]`), `visible` (bool), `filters` (`{}`), `raw_filters` (`{}`),
`selectedMeasurement`, `selectedMode`, `labelOptions`.

`selectedMeasurement` is `count` | `sum` | `avg` | `min` | `max` — a legacy field; set
`count` for logs/traces/formula and `avg` for metrics.

`visible` controls only chart visibility. Set `true` on the thresholded query and `false` on
formula helpers so the chart shows the evaluated line alone — the engine ignores it for
evaluation.

### `filters` vs `raw_filters`

Only **`raw_filters`** is read for logs/traces. For metrics it is `raw_filters ?? filters`.
The product's own templates set both, which is harmless — do the same for safety, but know
that `raw_filters` is the load-bearing one.

### Metrics query

```json
{
  "variables": [], "visible": true, "filters": {}, "raw_filters": {},
  "selectedMeasurement": "avg", "selectedMode": "metrics",
  "queryMode": "code",
  "promql": "sum(rate(container_cpu_usage_seconds_total{container!=\"\"}[5m])) by (pod)",
  "labelOptions": { "label": "A" }
}
```

`queryMode` is `builder` | `code` only — anything else falls back to `builder`. Use `code`
with `promql` (the UI's builder compiles to PromQL anyway, so PromQL is the contract). Put
grouping in the PromQL `by (...)`; each series is one firing instance.

### Logs query

```json
{
  "variables": [], "visible": true,
  "filters": { "level": ["ERROR"] },
  "raw_filters": { "level": ["ERROR"] },
  "selectedMeasurement": "count", "selectedMode": "logs",
  "value_operation": "row_count",
  "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
  "labelOptions": { "label": "A" }
}
```

### Traces query

```json
{
  "variables": [], "visible": true, "filters": {}, "raw_filters": {},
  "selectedMeasurement": "count", "selectedMode": "traces",
  "value_operation": "p95",
  "fields": [ { "field": "duration", "type": "float", "is_attribute": false } ],
  "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
  "labelOptions": { "label": "A" }
}
```

### Formula query

```json
{
  "variables": [], "visible": true, "filters": {}, "raw_filters": {},
  "selectedMeasurement": "count", "selectedMode": "formula",
  "expression": "A / B * 100",
  "labelOptions": { "label": "C" }
}
```

Set `metric_query_label` to the formula's label. The queries it references must share the
same `groupBy` for the formula engine to match series.

### `value_operation`

```
row_count  unique_count  avg  sum  max  min  p99  p95  p90  p75  p50
```

- `row_count` — no `fields`.
- `unique_count` — `fields` required (≥ 1).
- Numeric ops — `fields` required, and `type` must be literally **`"float"`**.

An unrecognised name falls back to `avg`. Missing or malformed `fields` on a numeric op
silently degrades the whole aggregation to **`row_count`**.

### `groupBy` / `fields` entry shape

All three keys are mandatory:

```json
{ "field": "workload", "type": "string", "is_attribute": false }
```

> [!WARNING]
> One malformed `groupBy` entry **empties the entire array**, so the rule fires as a single
> global series instead of per-label. This is silent.

Valid field names are in [SKILL.md](../SKILL.md) — the alert engine's lists, not the query
tools' catalog labels.

## Condition Types

| `condition_type` | Meaning | Extra |
|---|---|---|
| `threshold` | current value vs threshold | — |
| `change` | absolute change vs `compared_to` ago | `compared_to: "1h"` |
| `change_percent` | % change vs `compared_to` ago | `compared_to` |
| `new_value` | a group-by value unseen in the `compared_to` window appears | `compared_to`; logs/traces only |

## Bulk Import

A top-level **JSON array** bulk-imports:

```json
[ { "name": "…", "query_config": [ … ], … }, { "name": "…", … } ]
```

Each element is the same object shape as a single rule. The flow:

1. Client converts each element and POSTs to `/api/alerts/rules/bulk` with
   `{"dry_run": true, "rules": [...]}`.
2. The server validates without writing and returns a per-rule review:
   `{dry_run, total, valid, created: 0, failed, results}` where each `results` entry is
   `{index, name, valid, created, rule_id, errors}`.
3. The user reviews, then a second call with `dry_run: false` creates the valid ones.
   Invalid rules are reported per index, not silently dropped.

Limits: **500 rules**, **2 MB** payload.

> [!NOTE]
> The bulk path does **not** run the editor's validation, so the `[]`-channel and
> 3-character-name checks don't apply there — but the Go field-name validation does. Bulk
> and single-rule imports have genuinely different effective validation.

Emit **one array** even for two rules; a bare object only for exactly one.

## Verified Examples

### Metrics threshold

```json
{
  "name": "High pod CPU",
  "description": "Pod CPU usage sustained above 80% for 5 minutes",
  "enabled": true,
  "query_type": "metrics",
  "query_config": [
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "avg", "selectedMode": "metrics", "queryMode": "code",
      "promql": "sum(rate(container_cpu_usage_seconds_total{container!=\"\"}[5m])) by (pod)",
      "labelOptions": { "label": "A" } }
  ],
  "metric_query_label": "A",
  "raw_query": "",
  "threshold_operator": "greater_than",
  "threshold_value": 0.8,
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "severity": "warning",
  "labels": {},
  "notification_channel_ids": [1],
  "route_by_labels": false,
  "no_data_state": "normal",
  "include_samples": false,
  "sample_limit": 5,
  "unit": "CPU"
}
```

### Logs count, per workload

```json
{
  "name": "Log errors by workload {{workload}}",
  "description": "More than 10 ERROR logs in 5 minutes",
  "enabled": true,
  "query_type": "logs",
  "query_config": [
    { "variables": [], "visible": true,
      "filters": { "level": ["ERROR"] },
      "raw_filters": { "level": ["ERROR"] },
      "selectedMeasurement": "count", "selectedMode": "logs",
      "value_operation": "row_count",
      "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
      "labelOptions": { "label": "A" } }
  ],
  "metric_query_label": "A",
  "raw_query": "",
  "threshold_operator": "greater_than",
  "threshold_value": 10,
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "severity": "error",
  "labels": {},
  "notification_channel_ids": [1],
  "route_by_labels": false,
  "no_data_state": "normal",
  "include_samples": true,
  "sample_limit": 5,
  "unit": "number"
}
```

Text-search variant — replace both filter maps:

```json
"filters":     { "advanced_query": ["body SUBSTR_ILIKE \"timeout\" OR body SUBSTR_ILIKE \"connection refused\""] },
"raw_filters": { "advanced_query": ["body SUBSTR_ILIKE \"timeout\" OR body SUBSTR_ILIKE \"connection refused\""] }
```

### Trace p95 latency (500 ms)

```json
{
  "name": "High p95 latency {{workload}}",
  "description": "Service p95 latency above 500ms over 5m",
  "enabled": true,
  "query_type": "traces",
  "query_config": [
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "count", "selectedMode": "traces",
      "value_operation": "p95",
      "fields": [ { "field": "duration", "type": "float", "is_attribute": false } ],
      "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
      "labelOptions": { "label": "A" } }
  ],
  "metric_query_label": "A",
  "raw_query": "",
  "threshold_operator": "greater_than",
  "threshold_value": 500000000,
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "severity": "warning",
  "labels": {},
  "notification_channel_ids": [1],
  "route_by_labels": false,
  "no_data_state": "normal",
  "include_samples": false,
  "sample_limit": 5,
  "unit": "nanoseconds"
}
```

### Formula error rate (5xx share per workload)

```json
{
  "name": "API 5xx error rate {{workload}}",
  "description": "Share of HTTP requests returning 5xx, per workload",
  "enabled": true,
  "query_type": "formula",
  "query_config": [
    { "variables": [], "visible": false,
      "filters":     { "return_code": ["500","501","502","503","504"], "protocol_type": ["HTTP"] },
      "raw_filters": { "return_code": ["500","501","502","503","504"], "protocol_type": ["HTTP"] },
      "selectedMeasurement": "count", "selectedMode": "traces",
      "value_operation": "row_count",
      "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
      "labelOptions": { "label": "A" } },
    { "variables": [], "visible": false,
      "filters":     { "protocol_type": ["HTTP"] },
      "raw_filters": { "protocol_type": ["HTTP"] },
      "selectedMeasurement": "count", "selectedMode": "traces",
      "value_operation": "row_count",
      "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
      "labelOptions": { "label": "B" } },
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "count", "selectedMode": "formula",
      "expression": "A / B * 100",
      "labelOptions": { "label": "C" } }
  ],
  "metric_query_label": "C",
  "raw_query": "A / B * 100",
  "threshold_operator": "greater_than",
  "threshold_value": 5,
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "severity": "critical",
  "labels": {},
  "notification_channel_ids": [1],
  "route_by_labels": false,
  "no_data_state": "normal",
  "include_samples": false,
  "sample_limit": 5,
  "unit": "percentage"
}
```

Note: A and B are positionally `A` and `B`, the formula is index 2 → `C`, both counting
queries share the same `groupBy`, and the helpers are `visible: false` so the chart shows
only the error-rate line.

## Endpoints

| Purpose | Call |
|---|---|
| Create one rule | `POST /api/alerts/rules` |
| Bulk create | `POST /api/alerts/rules/bulk` — `{dry_run, rules}` |
| List rules | `GET /api/alerts/rules` |
| One rule | `GET /api/alerts/rules/:id` |
| List channels | `GET /api/alerts/notification-channels` |

Prefer the MCP tools (`list-alert-rules`, `list-notification-channels`) over raw HTTP when
the server is connected.
