# Datadog Monitor → KubeSense Alert

Translate a Datadog monitor into an equivalent KubeSense alert rule in the
import/export JSON shape — see [SKILL.md](./SKILL.md) for the schema and how
the user imports it (Alerts → Import JSON → review → Create).

Always **discover the real KubeSense metric/field names** (MCP `get-available-metrics`,
`get-trace-or-log-fields`) before emitting the payload — Datadog metric names rarely
match KubeSense's one-to-one.

## Input shape

A Datadog monitor (from the API or the UI export) looks like:

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

## Parse the Datadog `query`

```
avg(last_5m) : avg:system.cpu.user{env:prod} by {host} > 80
└──┬──┘ └─┬─┘   └┬┘ └──────┬───────┘└───┬───┘   └─┬─┘ └┬┘ └┬┘
 time-agg window space-agg  metric     scope    group   op thr
```

| Datadog part | Extract |
|---|---|
| `last_5m` | rolling window → `time_window: "5m"` |
| `avg(...)` (time aggregation) | how to reduce over the window — maps to the metric query's rollup (`avg_over_time`/`max_over_time`/…) or the logs/traces `value_operation` |
| `avg:` / `sum:` / `min:` / `max:` (space aggregation) | the cross-series aggregation → PromQL `avg/sum/min/max by (...)` |
| `system.cpu.user` | **discover the KubeSense equivalent metric** |
| `{env:prod}` (scope) | filters → PromQL label matcher `{env="prod"}` or `raw_filters`/`filters` |
| `by {host}` | `groupBy` → PromQL `by (host)` (verify the KubeSense label name, often `node`/`host`) |
| `> 80` | `threshold_operator: "greater_than"`, `threshold_value: 80` |
| `http.status_code:40*` / `http.status_class:4xx` (status-code class or wildcard) | an **advanced-query** filter, NOT an enumerated list: `40*` → `return_code LIKE "40_"`; `4xx`/`status_class:4xx` → `return_code LIKE "4__"`; `5xx` → `"5__"`. See "Advanced-query filters" in [SKILL.md](./SKILL.md). |

### Operators

`>` → `greater_than`, `>=` → `greater_than_or_equal`, `<` → `less_than`,
`<=` → `less_than_or_equal`, `==` → `equals`, `!=` → `not_equals`.

## Monitor type → KubeSense `selectedMode`

| Datadog `type` | KubeSense |
|---|---|
| `metric alert`, `query alert` | `metrics` (build PromQL) |
| `log alert` | `logs` (`value_operation: row_count` + `raw_filters`/`groupBy`) |
| `trace-analytics alert`, `apm` | `traces` (`value_operation` count, or `p95`/`p99` over `duration`). ⚠️ Datadog latency is in **seconds/ms**; KubeSense trace `duration` is **nanoseconds** — convert the threshold (`> 0.5` → `500000000`, `> 500ms` → `500000000`) and set `unit: "ns"`. Group "by service" via `workload` (NOT `app_service`). See the trace-latency notes in [SKILL.md](./SKILL.md). |
| `anomaly`, `forecast`, `outlier` | No direct equivalent — closest is `change_percent` (anomaly) or a static threshold; flag the gap to the user |

## `options` mapping

| Datadog option | KubeSense |
|---|---|
| `thresholds.critical` | `threshold_value` + `severity: "critical"` |
| `thresholds.warning` | KubeSense has **one** threshold per rule. Either (a) generate TWO rules — a `warning` and a `critical` — or (b) use critical only. Default to **two rules** and tell the user. |
| `notify_no_data: true` | `no_data_state: "firing"` |
| `notify_no_data: false` | `no_data_state: "normal"` |
| `no_data_timeframe` | informational — KubeSense uses `time_window` for the no-data decision (note any mismatch) |
| `evaluation_delay`, `new_host_delay` | no equivalent — ignore, mention it |
| `renotify_interval` | handled by Alertmanager `repeat_interval`, not the rule — mention it |
| `require_full_window` | ≈ `frequency_type: "always"` |
| `@channel` mentions in `message` | map each to a KubeSense notification channel id (look up via the channels endpoint; if absent, leave `notification_channel_ids: []` and tell the user to create/add the channel) |
| `tags` | copy to `labels` (as `{ "team": "infra" }`) where useful |

## Evaluation cadence

Datadog re-evaluates continuously; KubeSense uses a fixed
`evaluation_interval`. Default to `"1m"` unless the user
specifies otherwise.

## Worked example

Datadog:
```
avg(last_5m):avg:system.cpu.user{env:prod} by {host} > 80   (warning 70)
notify_no_data: true
```

→ KubeSense (critical rule; generate a second identical rule with value 70 /
severity `warning`):
```json
{
  "name": "High CPU on prod hosts {{host}}",
  "description": "Migrated from Datadog monitor",
  "severity": "critical",
  "enabled": true,
  "query_type": "metrics",
  "query_config": [{ "label": "A", "selectedMode": "metrics", "visible": true, "queryMode": "code",
    "promql": "avg by (host)(rate(<kubesense_cpu_metric>{env=\"prod\"}[5m]))" }],
  "metric_query_label": "A",
  "threshold_operator": "greater_than",
  "threshold_value": 80,
  "condition_type": "",
  "evaluation_interval": "1m",
  "time_window": "5m",
  "frequency_type": "at_least_once",
  "no_data_state": "firing",
  "notification_channel_ids": [],
  "route_by_labels": false,
  "labels": { "team": "infra", "source": "datadog" }
}
```

Import it via **Alerts → Import JSON** and review before creating (see SKILL.md).

Replace `<kubesense_cpu_metric>` with the metric `get-available-metrics`
returns for CPU, and confirm `host` is the correct group-by label
(`get-metric-labels`).

## What to always tell the user after migrating

- Which Datadog options had **no equivalent** (evaluation_delay, anomaly type, renotify) and how it differs.
- That warning+critical became **two rules** (or a single critical).
- That `@mentions` need real KubeSense channel ids.
- That the metric/field names were re-discovered, not copied verbatim.
