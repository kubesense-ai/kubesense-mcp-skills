# Datadog Monitor → KubeSense Alert

Translate a Datadog monitor into an equivalent KubeSense alert rule in the import JSON
shape. See [import-json.md](./import-json.md) for the schema and [SKILL.md](../SKILL.md)
for the field allow-lists.

Always **discover the real KubeSense metric and field names** before emitting anything —
`get-available-metrics`, `get-metric-labels`, `get-trace-or-log-fields`. Datadog metric
names rarely map one-to-one.

## Input Shape

```json
{
  "name": "High CPU on prod hosts",
  "type": "query alert",
  "query": "avg(last_5m):avg:system.cpu.user{env:prod} by {host} > 80",
  "message": "CPU high {{host.name}} @slack-ops @pagerduty",
  "tags": ["team:infra"],
  "options": {
    "thresholds": { "critical": 80, "warning": 70 },
    "notify_no_data": true,
    "no_data_timeframe": 10,
    "evaluation_delay": 60,
    "renotify_interval": 0
  }
}
```

## Parsing the Datadog `query`

```
avg(last_5m) : avg:system.cpu.user{env:prod} by {host} > 80
└──┬──┘ └─┬─┘   └┬┘ └──────┬───────┘└───┬───┘   └─┬─┘ └┬┘ └┬┘
 time-agg window space-agg  metric     scope    group   op thr
```

| Datadog part | Maps to |
|---|---|
| `last_5m` | `time_window: "5m"` |
| `avg(...)` time aggregation | the metric query's rollup (`avg_over_time`/`max_over_time`) or the logs/traces `value_operation` |
| `avg:` / `sum:` / `min:` / `max:` space aggregation | PromQL `avg`/`sum`/`min`/`max by (...)` |
| `system.cpu.user` | **discover** the KubeSense equivalent |
| `{env:prod}` scope | PromQL label matcher `{env="prod"}`, or `raw_filters` for logs/traces |
| `by {host}` | PromQL `by (host)`, or `groupBy` — verify the KubeSense label (often `node` or `host`; the cluster label is `clusterId`) |
| `> 80` | `threshold_operator: "greater_than"`, `threshold_value: 80` |

**Operators:** `>` → `greater_than`, `>=` → `greater_than_or_equal`, `<` → `less_than`,
`<=` → `less_than_or_equal`, `==` → `equals`, `!=` → `not_equals`.

**Status-code classes and wildcards** (`http.status_code:40*`, `http.status_class:4xx`) —
use an `advanced_query` filter with `LIKE`, where `_` matches one character:

```json
"raw_filters": { "advanced_query": ["return_code LIKE \"4__\""] }
```

`40*` → `"40_"`, `4xx` → `"4__"`, `5xx` → `"5__"`. Do **not** hand-write a
`unified_filter` block — it is silently discarded on import. And remember `advanced_query`
displaces every other `raw_filters` key, so fold all conditions into the one string.

## Monitor Type → `selectedMode`

| Datadog `type` | KubeSense |
|---|---|
| `metric alert`, `query alert` | `metrics` — build PromQL |
| `log alert` | `logs` — `value_operation: "row_count"` + `raw_filters` + `groupBy` |
| `trace-analytics alert`, `apm` | `traces` — `row_count`, or `p95`/`p99` over `duration`. See the latency note below. |
| `anomaly`, `forecast`, `outlier` | No direct equivalent. Closest is `condition_type: "change_percent"` or a static threshold — **flag the gap to the user.** |

### Trace latency conversion

Datadog expresses latency in **seconds or milliseconds**; the KubeSense alert engine reads
trace `duration` in **nanoseconds**.

| Datadog | KubeSense `threshold_value` |
|---|---|
| `> 0.5` (seconds) | `500000000` |
| `> 500ms` | `500000000` |
| `> 1s` | `1000000000` |

Set `"unit": "nanoseconds"` — not `"ns"`, which is not a valid value and silently becomes
`auto`.

**Grouping "by service":** use `workload`. The engine also accepts `app_service`, but it has
historically resolved to a rollup column populated only for SDK-instrumented services, which
yields empty or single-blank-series alerts. `workload` is populated on essentially every
span. (Note `service` itself is **rejected** by the alert engine, even though it is the
preferred label in the query tools.)

## `options` Mapping

| Datadog option | KubeSense |
|---|---|
| `thresholds.critical` | `threshold_value` + `severity: "critical"` |
| `thresholds.warning` | KubeSense has **one** threshold per rule. Generate **two rules** (a `warning` and a `critical`) and tell the user — or use critical only if they prefer. |
| `notify_no_data: true` | `no_data_state: "firing"` **only when metric absence is itself the incident** — see the caveat below |
| `notify_no_data: false` | `no_data_state: "normal"` |
| `no_data_timeframe` | Informational — KubeSense uses `time_window` for the no-data decision. Note any mismatch. |
| `require_full_window` | ≈ `frequency_type: "always"` — and you must also send `threshold_frequency: "always"`, or it downgrades to `at_least_once` |
| `evaluation_delay`, `new_host_delay` | No equivalent — ignore and mention it |
| `renotify_interval` | Handled by Alertmanager `repeat_interval`, not the rule — mention it |
| `@channel` mentions in `message` / `escalation_message` | Map to channel ids — see below |
| `tags` | Copy into `labels`, e.g. `{"team": "infra"}` |

> [!WARNING]
> **`notify_no_data: true` on a count/rate/change monitor must NOT become `firing`.**
>
> A count or rate query over a metric with no matching series returns an **empty result, not
> 0** — so a *healthy* window (zero pod restarts) reads as "no data". With
> `no_data_state: "firing"`, that healthy state fires continuously at value 0. Datadog's own
> no-data evaluation fills/interpolates per the rollup, so `notify_no_data: true` there does
> not misfire the way a literal port does here.
>
> Only use `firing` when the **presence** of the metric is the health signal — a gauge,
> liveness, or heartbeat that should always report. For anything that counts occurrences, use
> `"normal"` and say so in the migration summary.

## Notification Channels

Datadog routes via `@`-handles in `message` and `escalation_message`. KubeSense routes via
`notification_channel_ids` — integer ids of channels that **already exist**. Datadog handles
do not auto-create channels.

1. **Extract** every `@`-handle from both `message` and `escalation_message`. Classify:
   `@slack-*` → slack; `@webhook-*` / `@pagerduty-*` → webhook/pagerduty;
   `@name@domain` → email.
2. **Fetch the KubeSense channels** — call **`list-notification-channels`** (it returns
   `id`, `name`, `type` for enabled channels; optional `search`). Without MCP, ask the user
   for `GET /api/alerts/notification-channels`.
3. **Match** by type + name, case- and separator-insensitive: `@slack-flight-alerts` ≈ a
   slack channel named "flight-alerts" or "Flight Alerts". Put matched ids in
   `notification_channel_ids`.
4. **Report unmatched handles explicitly.** Leave them out and tell the user to create the
   channel (Settings → Notification Channels) and add it on the import-review screen.
   **Never invent an id** — a wrong id fails rule creation outright.

> [!IMPORTANT]
> `notification_channel_ids: []` **blocks a single-rule import** — the editor requires at
> least one channel and the user cannot click Create. For a bulk array it passes validation
> but the rules page nobody. Either supply a real id, or tell the user plainly that they must
> pick a channel on the review screen.

## Evaluation Cadence

Datadog re-evaluates continuously; KubeSense uses a fixed `evaluation_interval`. Default to
`"1m"` unless the user says otherwise.

## Worked Example

Datadog:

```
avg(last_5m):avg:system.cpu.user{env:prod} by {host} > 80   (warning 70)
notify_no_data: true
```

→ KubeSense critical rule (generate a second identical rule with value 70 and severity
`warning`):

```json
{
  "name": "High CPU on prod hosts {{host}}",
  "description": "Migrated from Datadog monitor",
  "enabled": true,
  "query_type": "metrics",
  "query_config": [
    { "variables": [], "visible": true, "filters": {}, "raw_filters": {},
      "selectedMeasurement": "avg", "selectedMode": "metrics", "queryMode": "code",
      "promql": "avg by (host)(rate(<kubesense_cpu_metric>{env=\"prod\"}[5m]))",
      "labelOptions": { "label": "A" } }
  ],
  "metric_query_label": "A",
  "raw_query": "",
  "threshold_operator": "greater_than",
  "threshold_value": 80,
  "condition_type": "threshold",
  "compared_to": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "severity": "critical",
  "labels": { "team": "infra", "source": "datadog" },
  "notification_channel_ids": [1],
  "route_by_labels": false,
  "no_data_state": "firing",
  "include_samples": false,
  "sample_limit": 5,
  "unit": "percentage"
}
```

Replace `<kubesense_cpu_metric>` with what `get-available-metrics` actually returns for CPU,
and confirm `host` is the right group-by label with `get-metric-labels`.

`no_data_state: "firing"` is correct **here** because `system.cpu.user` is a gauge — a host
that stops reporting CPU *is* the incident. Had the source been a count/rate (pod restarts,
error counts), the same `notify_no_data: true` would map to `"normal"`.

Since this produces two rules (critical + warning), emit them as **one JSON array** so they
bulk-import in a single pass.

## Always Tell the User

- Which Datadog options had **no equivalent** (`evaluation_delay`, anomaly/forecast types,
  `renotify_interval`) and how the behaviour differs.
- That warning + critical became **two rules** (or that you used critical only).
- That `@mentions` were resolved to real channel ids — and which ones **could not** be
  matched.
- That metric and field names were **re-discovered**, not copied from Datadog.
- Any `notify_no_data: true` on a count/rate/change monitor that you set to `"normal"`
  instead of `"firing"`, and that they can flip it back if metric absence really is their
  incident.
- That trace latency thresholds were converted to **nanoseconds**.
- To review each rule on the import editor's **condition chart** before creating.
