# Datadog SLO → KubeSense SLO

Translate a Datadog service level objective into a KubeSense one. See
[api-payloads.md](./api-payloads.md) for the target schema and [SKILL.md](../SKILL.md)
for the semantics.

Monitors are a different job — that is
[kubesense-alerts/references/datadog-migration.md](../../kubesense-alerts/references/datadog-migration.md).
**Migrate the monitors first**: a Datadog *monitor-based* SLO is worthless until the
monitors it names exist in KubeSense.

Always **rediscover real metric and field names** (`get-available-metrics`,
`get-metric-labels`, `get-trace-or-log-fields`) before emitting anything. Datadog
metric names almost never map one-to-one.

## Input shape

Datadog's v1 SLO object (the Terraform `datadog_service_level_objective` resource
carries the same fields):

```json
{
  "name": "Checkout availability",
  "description": "…",
  "type": "metric",
  "query": {
    "numerator":   "sum:trace.http.request.hits{service:checkout,!http.status_class:5xx}.as_count()",
    "denominator": "sum:trace.http.request.hits{service:checkout}.as_count()"
  },
  "monitor_ids": [],
  "groups": [],
  "thresholds": [
    {"timeframe": "7d",  "target": 99.9, "warning": 99.95},
    {"timeframe": "30d", "target": 99.5, "warning": 99.7}
  ],
  "tags": ["team:payments", "env:prod"]
}
```

A `time_slice` SLO instead carries:

```json
{
  "type": "time_slice",
  "sli_specification": {
    "time_slice": {
      "query": { "formulas": [{"formula": "query1"}], "queries": [{ "…": "…" }] },
      "comparator": "<=",
      "threshold": 500,
      "query_interval_seconds": 60
    }
  }
}
```

## Type mapping

| Datadog `type` | KubeSense `slo_type` | Carries over as |
|---|---|---|
| `metric` | `by_count` | `query.numerator` → `good_events_filter`, `query.denominator` → `total_events_filter` |
| `monitor` | `alert` | `monitor_ids` → `total_events_filter.alert_ids`, **after** mapping each monitor to its migrated KubeSense alert rule uuid |
| `time_slice` | `time_slice` | `sli_specification.time_slice` → the single `total_events_filter` + `operation` + `threshold_value` |

## Field mapping

| Datadog | KubeSense | Notes |
|---|---|---|
| `name`, `description` | `name`, `description` | Append "Migrated from Datadog" to the description. |
| `thresholds[].target` | `slo_target_percentage` | |
| `thresholds[].warning` | `warning_target_percentage` | Must be **above** the target — Datadog's own rule, same here. Omit if absent. |
| `thresholds[].timeframe` | `evaluation_window_days` | `7d` → 7, `30d` → 30, `90d` → 90. `custom` → read `thresholds[].timeframe`'s day count. |
| **several `thresholds`** | **several SLOs** | KubeSense stores **one** window per SLO. Emit one SLO per timeframe, named `"<name> (7d)"`, `"<name> (30d)"`, and say so. |
| `groups` (monitor SLOs) | **no equivalent — do not map to `groupBy`** | These *select* which monitor groups count toward compliance. KubeSense has no such selection: an alert SLO takes the union of its rules' firing history, and its grouped path keys on alert **fingerprint**, not on a tag value. See "Monitor SLOs" below. |
| `by {tag}` inside a metric SLO query | `groupBy` on both filters + `by (…)` in the PromQL | A grouping dimension, unlike `groups` above. Verify the KubeSense field name first. |
| `tags` | *(no equivalent)* | An SLO has **no** labels/tags field. Fold what matters into `description`, or into the `workload`/`namespace`/`cluster` metadata columns, which the list page filters on. |
| `sli_specification.time_slice.comparator` | `operation` | `<=` → `LTE`, `<` → `LT`, `>=` → `GTE`, `>` → `GT`, `==` → `EQ`. **Uppercase only.** `!=` has **no working equivalent** — `NEQ` is rejected at create; invert the query instead, or flag it to the user. |
| `sli_specification.time_slice.threshold` | `threshold_value` | Integer, in the unit your query returns. |
| `query_interval_seconds` | `evaluation_time_interval_seconds` | Datadog offers 60 and 300; so does KubeSense. Pass it straight through. |
| `monitor_ids` | `total_events_filter.alert_ids` | **Uuids of the migrated KubeSense rules**, not Datadog's integer ids. |
| SLO burn-rate / error-budget monitors | `alert_types` on the SLO | See below. |
| SLO corrections | *(no equivalent)* | Maintenance/excluded periods do not port. Flag it. |
| `timeframe` / `target_threshold` / `warning_threshold` (flat legacy form) | same as `thresholds[0]` | Older payloads use the flat fields; read whichever is present. |

## Translating the queries

### Metric SLOs

Datadog's `sum:metric{scope}.as_count()` is a counter sum over the bucket. The
KubeSense equivalent depends on where the data actually lives in your cluster:

| Datadog numerator/denominator | KubeSense |
|---|---|
| `trace.*.hits`, `trace.*.errors` | almost always **traces** — `selectedMode: "traces"`, `value_operation: "row_count"`, filters instead of a metric name |
| a real Prometheus counter | `selectedMode: "metrics"` with `sum(increase(<metric>{…}[1m]))` on both sides |
| `logs` count queries | `selectedMode: "logs"`, `value_operation: "row_count"` |

Scope translation for the traces path — note these are the **alert engine's** field
names, not the query tools' catalog labels:

| Datadog scope | KubeSense filter |
|---|---|
| `service:checkout` | `{"field": "app_service", "operation": "IN", "values": ["checkout"]}` |
| `!http.status_class:5xx` | `{"field": "return_code", "operation": "NOT_LIKE", "values": ["5__"]}` (`_` = one char) |
| `http.status_code:200` | `{"field": "return_code", "operation": "IN", "values": ["200"]}` |
| `env:prod` | whichever field your deployment carries it on — **discover it**, often `env_type` or a cluster/namespace |
| `resource_name:POST_/checkout` | `{"field": "resource", "operation": "IN", "values": ["post_/checkout"]}` |
| `by {service}` | `groupBy: [{"field": "workload", …}]` — see the grouping note below |

Datadog's convention "good = total − errors" becomes a good-side filter of
`status = ok`, or a `return_code NOT_LIKE "5__"`. Do not express the numerator as a
subtraction; there is no formula mode on an SLI query.

**Latency thresholds are nanoseconds** on trace `duration`, exactly as for alerts:
Datadog's `0.5` seconds or `500ms` → `500000000`.

### Time-slice SLOs

Datadog's time-slice SLI is a formula over one or more queries, compared against a
threshold. Port the formula to a single PromQL expression in
`total_events_filter.promql` and keep the comparator and threshold.

Prefer `selectedMode: "metrics"` here. The metrics executor reports "no series"
honestly, and missing data counts as **uptime** in both products — so the semantics
match. A traces/logs time slice has to infer missing data from a zero count, which is
a coarser signal.

### Monitor SLOs

1. Migrate each monitor with [kubesense-alerts](../../kubesense-alerts/SKILL.md).
2. Collect the created rules' uuids (`create-alert` returns one; `list-alert-rules`
   finds them afterwards).
3. Put those uuids in `total_events_filter.alert_ids`.

> [!WARNING]
> **Set `evaluate_from` to the moment the migrated rules started existing.** This is
> the biggest hazard in the whole migration, and it fails in the flattering direction.
>
> Uptime is computed as `bucket_seconds - downtime`, where downtime comes from rows in
> `alert_events`. A backfilled bucket from before the rules existed has no rows, so it
> scores as **fully healthy** — not as "no data". Backdate `evaluate_from` to match
> Datadog's history and you manufacture a stretch of perfect uptime, which then feeds
> the error budget and every burn-rate alert derived from it.
>
> There is no import path for Datadog's monitor state history. Say plainly that
> compliance starts at migration, and that the first full window is the first
> trustworthy number.

The other gap is **group selection**. Datadog's `groups` field restricts a monitor SLO
to named monitor groups. KubeSense cannot express that: `evaluateAlert` takes the union
of the firing history of every rule in `alert_ids`, so outages in groups the original
SLO excluded *will* count against you. Two honest options:

1. **Scope it in the rules.** Migrate the monitor into a rule whose filters already
   restrict it to the groups the SLO named, and point the SLO at that rule.
2. **Flag it as unsupported** and port the SLO without the restriction, saying so.

Do not silently translate `groups` into a `groupBy` entry — that is a different
operation, and for an alert SLO `groupBy` splits compliance by alert **fingerprint**
(`groupLabels: {"fingerprint": …}`), which is not the tag grouping Datadog showed.

## Burn-rate and error-budget monitors

In Datadog these are separate monitors (`burn_rate("slo_id").over("1h")…`,
`error_budget("slo_id")…`). In KubeSense they are **not** monitors you write — they
are `alert_types` on the SLO, and the API generates the rules:

| Datadog monitor | `alert_types` value |
|---|---|
| fast burn rate, 1h window | `burn_rate_fast` |
| slow burn rate, 6h window | `burn_rate_slow` |
| error budget remaining < 5% | `error_budget_critical` |
| error budget remaining < 10% | `error_budget_low` |

The thresholds are derived from `evaluation_window_days` (a 30-day window yields the
usual 14.4× / 6×), so a hand-tuned Datadog multiplier does **not** carry over. If the
user needs a different multiplier, they get a hand-written alert rule on
`kubesense_slo_burn_rate{slo_id="…"}` — and it must be a *separate* rule, because
`PUT /api/slo` rebuilds every generated rule from `alert_types`.

`@`-handles in the monitor message map to `notification_channels` ids exactly as for
alerts: `list-notification-channels` first, never invent an id, report unmatched
handles.

## Grouping note

Datadog groups an SLO by a tag. KubeSense groups by a query field, and the group cap
is **100** — past it the evaluator skips every bucket and the SLO goes silent. Datadog
itself caps at 20. If the Datadog SLO is grouped by something unbounded (`pod`,
`container_id`), do not port the grouping; say why.

Grouping by "service": use `workload`. The engine accepts `app_service` as a filter
and a group-by, but it is populated only for SDK-instrumented services, so grouping by
it yields blank or single-series groups. `workload` is populated on essentially every
span.

## Worked example

Datadog:

```json
{
  "name": "Checkout availability",
  "type": "metric",
  "query": {
    "numerator":   "sum:trace.http.request.hits{service:checkout,!http.status_class:5xx}.as_count()",
    "denominator": "sum:trace.http.request.hits{service:checkout}.as_count()"
  },
  "thresholds": [{"timeframe": "30d", "target": 99.9, "warning": 99.95}],
  "tags": ["team:payments"]
}
```

KubeSense — preview it, then create it:

```json
{
  "name": "Checkout availability (30d)",
  "description": "Migrated from Datadog SLO. team:payments.",
  "slo_type": "by_count",
  "metric": "requests",
  "slo_target_percentage": 99.9,
  "warning_target_percentage": 99.95,
  "evaluation_window_days": 30,
  "evaluation_time_interval_seconds": 60,
  "evaluate_from": "2026-09-01T00:00:00Z",
  "evaluation_start_time": "2026-09-01T00:00:00Z",
  "status": "active",
  "operation": "", "threshold_value": 0, "value": 0,
  "workload": "", "namespace": "", "cluster": "", "customer_identifier": "",
  "good_events_filter": {
    "label": "A", "selectedMode": "traces", "value_operation": "row_count", "groupBy": [],
    "unified_filter": {
      "type": "common",
      "common_filter": [
        {"field": "app_service",  "operation": "IN",       "values": ["checkout"]},
        {"field": "role",         "operation": "IN",       "values": ["server"]},
        {"field": "return_code",  "operation": "NOT_LIKE", "values": ["5__"]}
      ],
      "adv_filters": {}
    }
  },
  "total_events_filter": {
    "label": "B", "selectedMode": "traces", "value_operation": "row_count", "groupBy": [],
    "unified_filter": {
      "type": "common",
      "common_filter": [
        {"field": "app_service", "operation": "IN", "values": ["checkout"]},
        {"field": "role",        "operation": "IN", "values": ["server"]}
      ],
      "adv_filters": {}
    }
  },
  "alert_types": ["burn_rate_fast", "burn_rate_slow"],
  "notification_channels": [1]
}
```

`role = server` is not in the Datadog query. It is there because
`trace.http.request.hits` counts inbound requests to the service, and without it the
client spans of everything calling checkout are counted too. Add it, and say you did.

## Always tell the user

- That each Datadog **timeframe became its own SLO**, and what they are named.
- That `tags` had nowhere to go, and where you put them instead.
- That metric and field names were **rediscovered**, not copied — and which ones you
  could not resolve.
- For monitor SLOs: that compliance **starts at migration**, that `evaluate_from` was
  set accordingly, and that backdating it would have invented perfect uptime rather
  than leaving a gap.
- For monitor SLOs with `groups`: that the group **restriction** could not be carried
  over, and which of the two options above you took.
- That `!=` time-slice comparators have no working equivalent, if one appeared.
- That burn-rate monitors became `alert_types`, that the multipliers are derived from
  the window rather than ported, and that editing a generated rule is reverted on the
  next SLO update.
- That SLO **corrections** (excluded maintenance windows) do not port.
- Any grouping you dropped for cardinality, and why.
- The preview numbers — run `POST /api/slo/preview` on every converted SLO and show
  the compliance it returns. A converted SLO that previews `no_data` is a wrong field
  name, not a healthy service.
