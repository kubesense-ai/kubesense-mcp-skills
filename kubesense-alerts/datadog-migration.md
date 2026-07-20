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
| `http.status_code:40*` / `http.status_class:4xx` (status-code class or wildcard) | a structured `LIKE` filter, NOT an enumerated list: a `unified_filter` `common_filter` entry `{ "field": "return_code", "operation": "LIKE", "values": ["4__"] }` (`_`=one char: `40*`→`"40_"`, `4xx`→`"4__"`, `5xx`→`"5__"`). See rule 14 and the body-filter note in [SKILL.md](./SKILL.md) — the reliable path is to build it in the UI's advanced-query editor and Export. |

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
| `notify_no_data: true` | `no_data_state: "firing"` **only when metric absence is itself the incident** (a gauge/liveness/heartbeat monitor — "the exporter/host stopped reporting"). For **count / rate / change monitors** — restarts, error counts, event rates — map to `"normal"` instead and **warn the user**. See the caveat below. |
| `notify_no_data: false` | `no_data_state: "normal"` |
| `no_data_timeframe` | informational — KubeSense uses `time_window` for the no-data decision (note any mismatch) |

> **⚠️ `notify_no_data` on count/rate/change monitors — do NOT map to `firing`.**
> A count/rate query over a metric with no matching series returns an **empty
> result, not 0**, so a *healthy* window (e.g. zero pod restarts) reads as **no
> data**. With `no_data_state: "firing"` that healthy state fires continuously at
> value 0 (the alert detail shows "No Data" with a firing badge). Datadog's own
> no-data evaluation differs (it fills/interpolates per the rollup), so
> `notify_no_data: true` there does **not** misfire the way a literal port does
> here. Rule of thumb: only use `firing` when the *presence* of the metric is the
> health signal (a gauge that should always report). For anything that counts
> occurrences, use `no_data_state: "normal"` and note the change in the migration
> summary. This bit a real migration (Datadog monitor `17127396`, "Pod restarting
> > 2 times").
| `evaluation_delay`, `new_host_delay` | no equivalent — ignore, mention it |
| `renotify_interval` | handled by Alertmanager `repeat_interval`, not the rule — mention it |
| `require_full_window` | ≈ `frequency_type: "always"` |
| `@channel` mentions in `message`/`escalation_message` | map to KubeSense channel ids — see **Notification channels** below |
| `tags` | copy to `labels` (as `{ "team": "infra" }`) where useful |

## Notification channels

Datadog routes via `@`-handles in the monitor's `message` and `escalation_message`
(e.g. `@slack-flight-alerts`, `@webhook-zenduty-shop`, `@ayush@corp.com`). KubeSense
routes via `notification_channel_ids` — an array of **ids of channels that already
exist in KubeSense**. Datadog handles do NOT auto-create channels, and the KubeSense
MCP has no channel tool, so the assistant can't fetch them — it needs the list.

**Workflow:**

1. **Extract** every `@`-handle from the monitor's `message` AND `escalation_message`.
   Classify by type: `@slack-*` → slack · `@webhook-*` / `@pagerduty-*` → webhook/pagerduty
   · `@name@domain` → email.
2. **Get the KubeSense channel list** — if a channel-listing MCP tool is available
   (e.g. `list-notification-channels`), **call it** to fetch the channels automatically;
   otherwise ask the user to paste the output of `GET /api/alerts/notification-channels`
   (or copy Settings → Notification Channels). Either way it yields `[{ id, name, type }, …]`.
3. **Match** each handle to a channel by **type + name** (the handle's meaningful part
   vs the channel `name`, case/separator-insensitive: `@slack-flight-alerts` ≈ a slack
   channel named "flight-alerts"/"Flight Alerts"). Put matched `id`s in
   `notification_channel_ids`.
4. **Report unmatched** handles explicitly: leave them out and tell the user to create
   that channel (Settings → Notification Channels) and add it on the import-review
   screen (which has a channel picker). NEVER invent ids — a wrong id fails creation.

If the user hasn't created KubeSense channels yet, leave `notification_channel_ids: []`
and they pick channels during import review — migration still works, just unrouted.

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

`no_data_state: "firing"` is correct in **this** example because
`system.cpu.user` is a **gauge** — a host that stops reporting CPU is itself the
incident. Had the source monitor been a count/rate (e.g. pod restarts), the same
`notify_no_data: true` would map to `"normal"` instead (see the caveat in the
`options` mapping) — otherwise every healthy window fires at value 0.

## What to always tell the user after migrating

- Which Datadog options had **no equivalent** (evaluation_delay, anomaly type, renotify) and how it differs.
- That warning+critical became **two rules** (or a single critical).
- That `@mentions` need real KubeSense channel ids.
- That the metric/field names were re-discovered, not copied verbatim.
- **Any `notify_no_data: true` on a count/rate/change monitor that was set to `no_data_state: "normal"`** (not `firing`) to avoid the healthy-window-fires-at-0 trap — and that they can flip it back to `firing` if metric absence really is their incident.
