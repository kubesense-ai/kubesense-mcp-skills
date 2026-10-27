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
| `name` | **Required.** Editor enforces ≥ 3 characters. `{{field}}` placeholders resolve per firing series against a group-by key or a rule label; one matching nothing stays literal. The alert's own facts take an `Alert.` prefix (`{{Alert.value}}`, `{{Alert.evaluatedFrom}}`) — see the placeholder section of the SKILL. |
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
| `breach_counting_window_prometheus_format` | With `more_than_once`, the span the breaches are counted over; with `always`, the span the condition must hold across; with `at_least_once`, the span checked for *resolution*. It is read by all three — **always send it**, and see the trap below for why omitting it is not the same as leaving it to `time_window`. **Note the name.** |
| `severity` | `critical` \| `error` \| `warning` \| `info`. (The MCP tool allows only critical/warning/info.) |
| `labels` | `{"team": "infra"}` |
| `notification_channel_ids` | Array of **integer** channel ids from `list-notification-channels`. **`[]` blocks a single-rule import.** |
| `route_by_labels` | `false` → route to the listed channels. `true` → route via each channel's own label matchers, and `notification_channel_ids` is **discarded**. |
| `no_data_state` | `normal` (default) \| `firing` \| `previous` |
| `include_samples` / `sample_limit` | **Logs only** — attach matching rows to notifications. `sample_limit` 1–100. |
| `unit` | Display only. Must be a real formatter value — see below. |
| `conditions` / `condition_expression` / `join_by` | Several thresholds combined with AND / OR. Absent on an ordinary rule. See [Composite Conditions](#composite-conditions-and--or). |
| `warning_threshold_value` | A second, lower level on a single threshold. See [Two Levels on One Threshold](#two-levels-on-one-threshold). |

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
must hold across that whole span. **Set it explicitly, always**, even when `time_window`
already is that span: the engine's fallback to `time_window` is not what an import gets.
See the trap below.

### The `breach_counting_window` trap

**Send both keys, and never omit them.** `breach_counting_window` is what import reads;
`breach_counting_window_prometheus_format` is what the POST body and the export carry.
Measured on `convertAlertConfigToFormValues`, which is what a bulk import runs per rule:

| the document carries | the window the rule gets |
|---|---|
| `breach_counting_window_prometheus_format: "15m"` **only** | **5 minutes** |
| `breach_counting_window: "15m"` only | 15 minutes |
| neither | 5 minutes |

So the `_prometheus_format` name alone — the name an earlier version of this document
called "the one import reads" — is **ignored**, and the rule silently gets five minutes.
Not an error, not a blank field: a plausible number the reviewer has no reason to question.
A 15-minute hold becomes a 5-minute one and the rule fires three times sooner than asked.

The plain name alone works today. Send both anyway: the Export button emits both
(`helper.ts`), so a document carrying both is exactly what a round-tripped rule looks like,
and it survives the reader changing which one it prefers.

The engine *does* fall back to `time_window` when the column is null — that fallback
protects rules created by other routes. An import never reaches it, because the editor has
already filled the field.

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

A rule with `conditions` or `warning_threshold_value` must be a plain `threshold` — the
other three are refused with either.

## Composite Conditions (AND / OR)

Several thresholds in one rule: a **band** on one query ("p95 below 1ms OR above 500ms"),
or conditions on **different queries** that must hold for the same series ("p95 above
500ms AND more than 10 req/s, per service"). The second is not expressible any other way —
and no formula fakes it: `(A/500) * (B/10) > 1` passes at A=10000, B=0.5.

> [!IMPORTANT]
> **Off by default.** Saving a rule with conditions is refused unless the deployment sets
> `ALERT_COMPOSITE_CONDITIONS_ENABLED=true`. Check first:
> `GET /api/alerts/rules/capabilities` → `data.composite_conditions` (and
> `data.dual_threshold`, the switch for the next section). No MCP tool reports this. If you
> cannot call it, say the rule needs the feature — the import's dry-run review names the
> switch if it is off — and offer the fallback in SKILL.md.

### The three fields

```json
"conditions": [
  { "id": "c1", "query": "A", "operator": "less_than",    "value": 1000000,   "unit": "ms" },
  { "id": "c2", "query": "A", "operator": "greater_than", "value": 500000000, "unit": "ms" }
],
"condition_expression": { "op": "or", "conditions": ["c1", "c2"] },
"join_by": null
```

| Field | Shape and rules |
|---|---|
| `conditions[].id` | Non-empty, unique. Only the expression refers to it; it is never an alert label. Use `c1`, `c2`, … |
| `conditions[].query` | A query **label** — `A`, `B` — which is the query's **position** in `query_config` (index 0 → `A`). Must exist, and must **not** be a formula. |
| `conditions[].operator` | The six threshold operators. `above`/`below` are refused. |
| `conditions[].value` | **Native units** — trace `duration` is **nanoseconds**, exactly as `threshold_value`. |
| `conditions[].unit` | Optional, **display only**: `ns` \| `us` \| `ms` \| `s`, and **only** on a condition reading a traces query that aggregates `duration`. See the unit trap below. |
| `condition_expression.op` | `and` \| `or`. |
| `condition_expression.conditions` | Condition ids. Every condition must be used, **exactly once**. |
| `condition_expression.children` | Nested sub-expressions: accepted by the API and engine, and kept by a **bulk (array) import**. The editor flattens them (see "Which import path" below). |
| `join_by` | Tri-state, and `null` is **not** `[]` — see below. |

Also required on a composite rule, because the document still has to be a valid single
rule:

- `threshold_operator` / `threshold_value` = **condition 1's** operator and value. The API
  overwrites them from condition 1 anyway; the engine reads only `conditions`.
- `metric_query_label` = **condition 1's** query.
- `condition_type: "threshold"`.
- `frequency_type` `at_least_once` or `more_than_once` — **`always` is refused**.
- **No** `warning_threshold_value` — conditions plus levels is refused.
- **One signal**: every non-formula query shares `query_type`, as in any rule. A logs
  condition AND a metrics condition cannot be one rule.
- At least **two** conditions — the editor refuses fewer, though the API alone would
  accept one.

### `join_by` — how two queries' series pair

| Conditions read | `join_by` | Result |
|---|---|---|
| **one** query (a band) | `null`, or omit it | Each series is judged on its own. Alert labels = that series' labels, as usual. `[]` or a list here is **refused**. |
| several queries, each returning **one ungrouped value** | `[]` | One rule-level verdict, one alert with no series labels. |
| several **grouped** queries | `["service"]` — label names | Series pair when they agree **exactly** on every listed label. The alert's labels are **exactly those labels** (plus the rule's `labels`). |

Several queries with `join_by` missing or `null` is **refused** by the API. How an import
surfaces that depends on the path (see "Which import path" below). Label names must be exact: no blanks,
no surrounding whitespace, no duplicates.

**Which label names?** Whatever the queries' series actually carry:

- **Metrics** — the PromQL `by (...)` labels. Aggregate **every** query to exactly the
  join labels: `sum by (service) (...)`, and for a histogram
  `histogram_quantile(0.95, sum by (service, le) (...))`. A query that keeps an extra
  label (`pod`) returns several series per service, and that service is dropped.
- **Logs / traces** — the `groupBy[].field` exactly as written (`workload`; an attribute
  is `@name`). Give every query the **same** `groupBy`, and join on those fields.

**What the engine does with data that does not pair** — it never guesses, and it never
freezes the whole rule. Each of these is **left out** with a warning shown on the rule
page (never in MCP output):

- a series missing a join label (it is never matched as `""`);
- two or more series of one query on the same key — a service scaling to a second pod
  when the query was not aggregated to `service`;
- an ungrouped value in a labelled join, or a grouped / multi-series query under `[]`.

A key left out, or missing from one query, is **unknown** for that query's conditions —
never 0, never false:

| | one side unknown |
|---|---|
| `and` | unknown → that series gets **no data**, and the rule's `no_data_state` decides it (`normal` resolves it) |
| `or` | fires if the other side is true; otherwise unknown |

So `no_data_state: "normal"` is the right default here too: a series that briefly loses
one side should resolve, not fire. Nothing checks at save time that the `join_by` labels
exist on the queries — a label no query returns leaves out **every** series and the rule
simply goes quiet. Check the condition chart.

**Each condition reads its own window.** For metrics, a `>`/`>=` condition reads the
window's **maximum** and a `<`/`<=` the **minimum** — a band runs its query twice. An AND
across queries compares each query's peak within `time_window`, not readings at one
instant.

### Units — the dangerous part

`value` is **always native**. `unit` never converts anything the engine sees; it only
tells the editor how to *display* the stored number.

| You mean | `value` | `unit` |
|---|---|---|
| trace p95 above 500 ms | `500000000` | `"ms"` (or omit) |
| trace p95 below 1 ms | `1000000` | `"ms"` |
| trace p99 above 2 s | `2000000000` | `"s"` |
| PromQL histogram (seconds) above 500 ms | `0.5` | **omit** |
| request count at least 100 | `100` | **omit** |

- `"value": 500, "unit": "ms"` is **500 ns**. The rule breaches on every evaluation — the
  single-threshold KUBE-2435 bug, one condition at a time. The editor gives it away by
  showing `0.0005 ms`.
- Put a `unit` **only** on a condition reading a traces `duration` aggregate. On any
  other condition it means nothing. On webapps before #2530 it is also dangerous: the
  editor divided the value by the unit and saved the divided number (`0.5` with
  `"unit": "s"` on a PromQL query was stored as `5e-10`). From #2530 on, a bulk import
  sends the value as written and the editor converts only trace-duration conditions.
- Condition `unit` uses `ns`/`us`/`ms`/`s`. The rule's own `unit` is the chart formatter
  (`nanoseconds`, `seconds`, …). Do not swap the vocabularies.
- `threshold_input_unit` is re-derived from condition 1's `unit` by the importer — you do
  not need to send it.

### Which import path

The same file is treated differently depending on how it is imported. Write it so it is
right on all three.

| Path | What happens to the composite fields |
|---|---|
| **Array** (bulk import, webapp #2530 and later) | `conditions`, `condition_expression` and `join_by` are sent **exactly as written**, and the API's dry-run refuses what is invalid: a missing `join_by` on a cross-query rule, a stray `join_by` on a band, unused ids. Nesting is kept. |
| **Single object** (opens the editor) | The editor holds the rule. It **flattens** a nested expression to one level (and says so before saving), **will not save** a cross-query rule with no match labels, resets `join_by` to `null` on a single-query band, and converts a `unit` only on a trace-duration condition. The import's own check before the editor opens is shape-only. |
| **Any path, webapp before #2530** | A missing `join_by` on a cross-query rule became `[]` ("every query ungrouped") without being refused, so grouped queries were all left out and the rule never fired. Nesting was flattened. A `unit` on a non-duration condition rescaled its value. |

### Composite traps

| Trap | Consequence |
|---|---|
| Cross-query rule with `join_by` omitted or `null` | Refused by a bulk import's dry-run; the editor will not save it. **Before #2530 the importer rewrote it to `[]`** so it was not refused. With grouped queries every series is then left out as "wrong-shaped" and the rule never fires. **Always write `join_by` on a cross-query rule.** |
| `join_by: []` or a list on a single-query band | Refused at a direct POST and by a bulk import's dry-run; the editor quietly resets it to `null`. Write `null`. |
| `condition_expression.children` (nested) | Evaluated by the engine and kept by a **bulk** import. The **editor flattens** it to one level under the top `op`: `(c1 AND c2) OR c3` becomes `c1 OR c2 OR c3`. That happens on a single-rule import and whenever the rule is later edited in the UI, and on every import before #2530. Tell the user a UI edit changes the rule. |
| A formula as a condition's query | Refused. Put the formula's arithmetic in PromQL, or threshold the formula as a single-threshold rule. |
| Grouped logs/traces `less_than` count | A key with zero matching rows returns **no series**, not 0 — so "count dropped below N" cannot see it drop to zero. |
| A `{{label}}` placeholder not in `join_by` | Stays literal on a cross-query rule — the alert carries only the join labels. |
| `validate-alert-json` says `valid=true` | It checks the shape (ids non-empty, operator and `op` vocabulary) but **none** of the cross-field rules: missing `join_by`, unused or unknown ids, formula operands, `always`, a warning level. Those surface only in the import's dry-run review. Check them by hand against the list above. |

### Composite example: trace latency band (one query, OR)

```json
{
  "name": "p95 latency out of band {{workload}}",
  "description": "p95 below 1ms (requests short-circuiting) or above 500ms, per workload, over 5m",
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
  "threshold_operator": "less_than",
  "threshold_value": 1000000,
  "conditions": [
    { "id": "c1", "query": "A", "operator": "less_than",    "value": 1000000,   "unit": "ms" },
    { "id": "c2", "query": "A", "operator": "greater_than", "value": 500000000, "unit": "ms" }
  ],
  "condition_expression": { "op": "or", "conditions": ["c1", "c2"] },
  "join_by": null,
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "breach_counting_window": "5m",
  "breach_counting_window_prometheus_format": "5m",
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

1 ms = `1000000` ns, 500 ms = `500000000` ns. One query, so `join_by: null`, and each
workload alerts under its own labels. `threshold_*` repeat condition 1.

### Composite example: slow AND busy, per service (metrics, two queries)

```json
{
  "name": "Slow under load {{service}}",
  "description": "p95 above 500ms AND more than 10 req/s, paired per service",
  "enabled": true,
  "query_type": "metrics",
  "query_config": [
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "avg", "selectedMode": "metrics", "queryMode": "code",
      "promql": "histogram_quantile(0.95, sum by (service, le) (rate(http_server_request_duration_seconds_bucket[5m])))",
      "labelOptions": { "label": "A" } },
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "avg", "selectedMode": "metrics", "queryMode": "code",
      "promql": "sum by (service) (rate(http_server_request_duration_seconds_count[5m]))",
      "labelOptions": { "label": "B" } }
  ],
  "metric_query_label": "A",
  "raw_query": "",
  "threshold_operator": "greater_than",
  "threshold_value": 0.5,
  "conditions": [
    { "id": "c1", "query": "A", "operator": "greater_than", "value": 0.5 },
    { "id": "c2", "query": "B", "operator": "greater_than", "value": 10 }
  ],
  "condition_expression": { "op": "and", "conditions": ["c1", "c2"] },
  "join_by": ["service"],
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "breach_counting_window": "5m",
  "breach_counting_window_prometheus_format": "5m",
  "severity": "critical",
  "labels": {},
  "notification_channel_ids": [1],
  "route_by_labels": false,
  "no_data_state": "normal",
  "include_samples": false,
  "sample_limit": 5,
  "unit": "seconds"
}
```

The metric and label names are illustrative — **discover** them with
`get-available-metrics` / `get-metric-labels` and substitute. Both queries aggregate to
exactly `service` (plus `le` inside the quantile), so each service is one series per
query. Values are in the metric's own unit — Prometheus histograms are **seconds**, so
500 ms is `0.5` and there is no condition `unit`. The alert carries only `service`, which
is why `{{service}}` resolves.

### Composite example: slow with real traffic, per workload (traces, two queries)

```json
{
  "name": "Slow with real traffic {{workload}}",
  "description": "p95 above 500ms AND at least 100 spans in 5m, paired per workload",
  "enabled": true,
  "query_type": "traces",
  "query_config": [
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "count", "selectedMode": "traces",
      "value_operation": "p95",
      "fields": [ { "field": "duration", "type": "float", "is_attribute": false } ],
      "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
      "labelOptions": { "label": "A" } },
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "count", "selectedMode": "traces",
      "value_operation": "row_count",
      "groupBy": [ { "field": "workload", "type": "string", "is_attribute": false } ],
      "labelOptions": { "label": "B" } }
  ],
  "metric_query_label": "A",
  "raw_query": "",
  "threshold_operator": "greater_than",
  "threshold_value": 500000000,
  "conditions": [
    { "id": "c1", "query": "A", "operator": "greater_than",          "value": 500000000, "unit": "ms" },
    { "id": "c2", "query": "B", "operator": "greater_than_or_equal", "value": 100 }
  ],
  "condition_expression": { "op": "and", "conditions": ["c1", "c2"] },
  "join_by": ["workload"],
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "breach_counting_window": "5m",
  "breach_counting_window_prometheus_format": "5m",
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

The pattern that stops a latency rule paging on three slow requests at 3am. Both queries
group by `workload`, so that is the join label. `c1` is a duration (nanoseconds, `unit:
"ms"` for display); `c2` is a count and carries **no** unit.

## Two Levels on One Threshold

One query, one direction, two severities — "warn above 300ms, page above 500ms" — is
**not** a composite rule. It is one threshold with a second level:

```json
"severity": "critical",
"threshold_operator": "greater_than",
"threshold_value": 500000000,
"warning_threshold_value": 300000000
```

Crossing `threshold_value` is critical; crossing only `warning_threshold_value` is a
warning; it is one incident whose level moves. Also behind a switch,
`ALERT_DUAL_THRESHOLD_ENABLED` — the capabilities endpoint's `dual_threshold`. The API
refuses it unless:

- `severity` is `critical` (the lower level is always `warning`);
- the operator is ordered (`greater_than*` / `less_than*`), and the warning value is on
  the reachable side — **below** critical for `greater_than*`, **above** it for
  `less_than*`;
- frequency is `at_least_once`, and `condition_type` is `threshold`;
- the rule has no `conditions`.

`warning_threshold_value` is native units, like every threshold. When the switch is off,
fall back to two rules, one per severity.

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

The composite and two-level examples live in their own sections above.

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

Text-search variant. For **one** body match, filter on `body` directly — it is a valid
filter key (never a group-by), and a bare `ILIKE` on it is rewritten to token search:

```json
"filters":     { "body": ["timeout"] },
"raw_filters": { "body": ["timeout"] }
```

For an OR across phrases, or body text mixed with another field, `advanced_query` still
wins — remembering it **replaces** every other filter key:

```json
"filters":     { "advanced_query": ["body SUBSTR_ILIKE \"timeout\" OR body SUBSTR_ILIKE \"connection refused\""] },
"raw_filters": { "advanced_query": ["body SUBSTR_ILIKE \"timeout\" OR body SUBSTR_ILIKE \"connection refused\""] }
```

Either way the rule reads the **raw** logs table every evaluation — no rollup carries
`body` — so say so before attaching one to a long window in a busy tenant.

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
  "query_type": "traces",
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
only the error-rate line. `query_type` is the queries' signal, not `formula` —
`validate-alert-json` refuses a `formula` query_type over traces queries.

## Endpoints

| Purpose | Call |
|---|---|
| Create one rule | `POST /api/alerts/rules` |
| Bulk create | `POST /api/alerts/rules/bulk` — `{dry_run, rules}` |
| List rules | `GET /api/alerts/rules` |
| One rule | `GET /api/alerts/rules/:id` |
| List channels | `GET /api/alerts/notification-channels` |
| Optional features on | `GET /api/alerts/rules/capabilities` → `{composite_conditions, dual_threshold}` |

Prefer the MCP tools (`list-alert-rules`, `list-notification-channels`) over raw HTTP when
the server is connected.
