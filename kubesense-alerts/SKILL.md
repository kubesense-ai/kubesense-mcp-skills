---
name: kubesense-alerts
description: Work with KubeSense alerts — survey what is firing, inspect a rule's breaching condition and history, and create rules either via the create-alert MCP tool or as import JSON over metrics, logs, and traces. Includes validate-alert-json for checking hand-built rule JSON, the alert engine's own field allow-lists, which differ from the query engine's, and translating Datadog monitors. Also covers multi-query formula rules, the Alert. placeholder namespace, manual resolve, and maintenance windows.
metadata:
  version: "2.3.0"
  author: kubesense
  repository: https://github.com/kubesense-ai/kubesense-mcp-skills
  tags: kubesense,alerts,alerting,monitors,thresholds,datadog-migration,promql,notification-channels
---

# KubeSense Alerts

Two distinct jobs, don't confuse them:

- **Reading** alerts — what's firing, what breached, is it chronic. Pure MCP tool calls.
- **Creating** alerts — either the `create-alert` MCP tool (validated, one rule) or
  **import JSON** (reviewable in the UI, supports bulk).

## Routing

| The user is asking… | Do this |
|---|---|
| "what's firing right now?" | `list-active-alerts` |
| "what alerts exist / did I create any?" | `list-alert-rules` (+ `get-current-user` for `created_by`) |
| "this alert fired — what broke?" | `get-alert-details` for the scope, then [kubesense-infra](../kubesense-infra/SKILL.md) for changes and infra failures |
| "is this flapping or new?" | `get-alert-history` |
| "has this been root-caused before?" | `find-investigation-for-alert` |
| "create an alert when…" (one rule, agent applies it) | `create-alert` MCP tool |
| "give me the alert JSON for…" / several rules / migrating | import JSON → [references/import-json.md](./references/import-json.md) |
| "port these Datadog monitors" | [references/datadog-migration.md](./references/datadog-migration.md) |
| "why did this fire but page nobody?" | channel cadence first, then whether a **maintenance window** covers it |
| "put these rules in a list / folder" | UI-only grouping — no MCP surface, say so rather than guessing |
| you hand-built rule JSON and want it checked | `validate-alert-json` before handing it over |

## Reading Alerts

| Tool | Scope |
|---|---|
| `list-active-alerts` | Currently-firing series from the **native** store, joined with rule metadata. Filters: `from_time`/`to_time`, `fingerprint`, `acknowledged`, `assignee`, `include_resolved`. |
| `list-alerts` | The **external Alertmanager** — label-only, no rule config. Different source; use `list-active-alerts` unless you specifically want Alertmanager state or silences. |
| `list-alert-rules` | Rule *definitions*, including disabled and non-firing ones. Newest first. Filters: `enabled`, `state`, `severity`, `query_type`, `search`, `created_by`. |
| `get-alert-details` | One rule's full config (`query_config`, condition, threshold) **plus** its firing instances. Start here when investigating. |
| `get-alert-history` | Triggered/resolved transitions, newest first — tells you chronic vs new. |
| `find-investigation-for-alert` | The most recent *concluded* AI investigation and its root cause. `found=false` is normal, not an error. |
| `list-notification-channels` | Enabled channels only: `id`, `name`, `type`. |

## Checking Hand-Built Rule JSON

Whenever you assemble a rule document yourself — import JSON, a ported Datadog monitor, an
edited export — run it through **`validate-alert-json`** before handing it to the user. It
stores nothing and reports every problem at once:

```
# valid=false findings=2
path                        rule                 message
/query_config/0/queryMode   shape                value must be one of 'builder', 'code'
/metric_query_label         metric_query_label   names query "A", but the rule's queries are labelled "B"
```

Each `path` is a JSON Pointer to the value to fix. Repeat until `valid=true`.

It validates the **wire document** — the export/import shape with `query_config`,
`threshold_operator` and `frequency_type`. It is *not* for `create-alert`'s arguments;
that tool validates its own input and rejects with the same findings.

> [!IMPORTANT]
> **"Which alerts did I create?"** — call `get-current-user` and pass its **`username`** as
> `created_by`. The stored creator is a username; an **email will never match**, and those
> two values are frequently different.

A **fingerprint** identifies one firing *series* of a rule (one namespace/pod/workload).
Pass it to narrow `get-alert-details` / `get-alert-history` to that instance; omit it for
the whole rule.

### An alert can leave Firing Now without recovering

Two human verbs act on a firing series, and they mean different things:

| | says | stays in Firing Now | notifications |
|---|---|---|---|
| **Acknowledge** | "I am on it" | yes | suppressed by an Alertmanager silence, capped at 7 days |
| **Resolve** | "this is handled" | **no** | suppressed for *this* breach only |

A resolve dismisses the current breach; the engine drops the flag as soon as the series
stops breaching, so a genuine re-breach later notifies normally. It is not a mute.

> [!IMPORTANT]
> Nothing in the MCP output tells the two apart from a real recovery. A manually resolved
> series just gains an `ends_at` and falls out of `list-active-alerts`, exactly like one
> that recovered. So never conclude "it recovered at 14:02" from `include_resolved` alone —
> say the alert *closed*, and if the user is asking why a known-broken thing went green,
> point them at the alert's own page, which does distinguish them.

## Creating Alerts — Which Path?

| | `create-alert` MCP tool | Import JSON |
|---|---|---|
| Rules per call | one | one or many (bulk) |
| Field names | **auto-bridged** — tries the catalog label, then the storage name | you must get them exactly right |
| Validation | up-front, with a precise error to retry against | server-side at import |
| Applied by | the agent (write tool, needs approval) | the user, in the UI |
| Best for | a single rule the user wants created now | reviewable output, several rules, migrations |

**Prefer `create-alert`** for a single rule — it resolves field names against the engine's
own validator, so it can't emit a name the engine rejects. Prefer import JSON when the user
asks for "the JSON", wants to review before anything is created, or is migrating several
monitors.

### create-alert

```json
{
  "signal": "traces",
  "name": "Checkout p95 latency high",
  "description": "p95 above 500ms for 5 minutes",
  "where": "service = checkout",
  "value_operation": "p95",
  "fields": [ { "field": "duration" } ],
  "group_by_fields": [ { "field": "workload" } ],
  "threshold_operator": "greater_than",
  "threshold_value": 500000000,
  "severity": "warning",
  "notification_channels": [1],
  "time_window": "5m",
  "evaluation_interval": "1m"
}
```

- `signal`: `metrics` | `logs` | `traces`.
- **metrics** → supply `promql`. **logs/traces** → `where` (search-logs syntax) +
  `value_operation`, plus `fields` for anything other than `row_count`.
- `value_operation` here is narrower than the query tools: `row_count`, `unique_count`,
  `avg`, `sum`, `min`, `max` — **no percentiles**. For a p95 latency rule use import JSON.
- Required: `name`, `threshold_operator`, `threshold_value`, `notification_channels`.
- Defaults: `severity=warning`, `threshold_frequency=at_least_once`,
  `evaluation_interval=1m`, `time_window=5m`.
- `threshold_operator` also accepts `above`/`below` here (it does **not** in import
  JSON). They are **normalised** before the rule is built — `above` is stored as
  `greater_than`, `below` as `less_than` — so the rule reads back with the canonical
  value, not the one you sent. Prefer the canonical names when you know them.

### Several Queries and a Formula

A ratio — error rate, share of total, one query over another — no longer forces the import
path. Pass `queries` **instead of** the flat single-query fields, and give the last entry
an `expression`:

```json
{
  "signal": "traces",
  "name": "Checkout 5xx rate above 5%",
  "queries": [
    {"label": "A", "where": "return_code LIKE \"5__\"", "value_operation": "row_count",
     "group_by_fields": [{"field": "workload"}]},
    {"label": "B", "where": "", "value_operation": "row_count",
     "group_by_fields": [{"field": "workload"}]},
    {"label": "C", "expression": "A / B * 100"}
  ],
  "threshold_operator": "greater_than",
  "threshold_value": 5,
  "notification_channels": [1]
}
```

- `queries` and the flat fields (`promql`, `where`, `value_operation`, `fields`,
  `group_by_fields`) are **mutually exclusive** — pass `queries` and everything goes in it.
- `label` defaults to `A`, `B`, `C` **by position**, letters only; 26 queries maximum.
- A formula entry carries `expression` and nothing else, and may reference only queries
  listed **before** it.
- Every non-formula query runs against the rule's one `signal` — a rule cannot mix logs
  with metrics.
- **Composed queries must group by the same fields**, or not group at all. The engine
  matches their series by those keys, so a mismatch joins nothing — and an empty result
  reads as *healthy*, not as an error. The rule goes quiet instead of complaining.
- The threshold applies to the formula. With several queries and **no** formula, name the
  one to threshold in `threshold_query`.
- `"where": ""` is accepted inside `queries` — a denominator of "everything" is the point —
  where an unfiltered single-query rule is refused.

Percentiles are still out of reach here: `value_operation` has no `p95`, so a p95 latency
rule remains an import-JSON job.

`labels` attaches extra labels to the rule and to every alert it fires. They route, and
they resolve in `{{placeholders}}` — see below.

> [!WARNING]
> **Call `list-notification-channels` first.** `notification_channels` is required and must
> contain a real channel id. A nonexistent id fails rule creation outright. If no channels
> exist, tell the user one must be created in Settings — do **not** create the rule
> silently, because it would fire and page nobody.

This is a **write tool**. State exactly what you are about to create before calling it.

### When It Refuses

The rule is checked against the wire contract before it is stored, so a refusal names
the exact field:

```
invalid alert: /query_config/0/queryMode: value must be one of 'builder', 'code'
```

Each finding is a JSON Pointer into the rule the tool built plus what is wrong with it.
Fix and call again — that is a cheaper round trip than it looks, and far cheaper than a
rule that stores cleanly and then evaluates nothing.

Two kinds of failure read differently. `invalid alert: …` is yours to correct. `failed to
create alert rule: …` is a server problem — report it rather than retrying.

## Field Names — A Different Vocabulary

> [!IMPORTANT]
> The alert engine accepts a **different field set** from the query tools. The MCP query
> catalog labels (`type`, `instance`, `service`, `node`) are **not** all valid here. There
> are three vocabularies in play:
>
> 1. **Query tools** (`analyze-logs`, `search-traces`) — catalog labels only.
> 2. **Alert group-by / value fields** — a mix of labels and storage names, strictly
>    validated.
> 3. **Alert filter keys** — the group-by set *plus* extra storage-name overlays.

### Logs — group-by and value fields (19, exact)

```
instance  workload  namespace  cluster  pod  container  node
pod_name  container_name  level  format  host  body_length
region  app_version  customer_identifier  source
service  env_type
```

Note both spellings work: `pod` **and** `pod_name`, `container` **and** `container_name`,
`node` **and** `host`, `instance`. Severity is **`level`** here — not the query tools'
`type`.

`service` and `env_type` were accepted only recently (KUBE-2638). The logs catalog had
offered both in the Group By dropdown since it existed while the engine rejected them, so
picking either failed rule creation. If you meet an install that still refuses them, it
predates that fix — group by `workload` instead.

**Logs filter keys** = the 19 above **plus** `env`, `node_name`, and **`body`**.

> [!NOTE]
> **`body` is a filter key, not a dimension.** `raw_filters: {"body": ["timeout"]}` is
> accepted; `body` as a **group-by or value field is still rejected**, deliberately —
> grouping by the message text yields one series per distinct line, and there is nothing to
> aggregate. `body_length` is the numeric field, and a different one.
>
> Two things follow from how it is stored. A body filter **forces the raw table** (no
> rollup has the column), so it costs a full scan per evaluation — worth saying out loud
> before putting one on a 24h window in a busy tenant. And a bare `ILIKE` on `body` is
> rewritten to **token search**, because in SQL it is an exact match and matched no real
> log line. Token search is case-insensitive and splits on non-alphanumerics, so
> `hasAnyTokens` "false positives" are inherent to the index, not a defect — expect them,
> and do not report them as alerting bugs.
>
> `pattern_id` is **not** accepted: it exists only on the rollups, so a rule using it would
> freeze the moment the query fell back to the raw table.

### Traces — group-by and value fields (40, exact)

The 28 catalog labels:

```
status  protocol  source  role  status_code  namespace  method
workload  container  region  app_version  resource  server  client
server_namespace  client_namespace  node  operation_name
partner_cluster  customer_identifier  duration  duration_quantile
duration_avg  pod  instance  cluster  return_code  app_service
```

…**plus 12 storage names**, which is what the webapp actually persists for a trace
group-by:

```
container_name  pod_name  node_name  kind  subtype  protocol_type
clustered_resource  perspective_namespace  perspective_workload
env_type  app_db  issue_reason
```

Group-by used to accept only the first list, so 12 of the 27 groupable trace fields the UI
offered were rejected on save — KUBE-2638 again, and the reason `issue_reason` is now
accepted where older notes say it is not.

**Trace filter keys** = the 40 above **plus** `is_external`, `app_name`,
`partner_namespace`, `partner_workload`.

So for traces, **both** the catalog name and the storage name work, as a filter key *and*
as a group-by (`status_code` and `return_code`, `resource` and `clustered_resource`,
`method` and `subtype`).

> [!WARNING]
> **`service` is NOT accepted for traces — use `app_service`.** The query tools' preferred
> label does not exist in the trace side of the alert engine, and the rejection message
> says so. (Logs are the opposite: `service` *is* accepted there.) For logs, `node_name` is
> filter-only — as a dimension the column is called `host`.

Fields marked `is_attribute: true` skip validation entirely, as do filter keys that are
empty, `advanced_query`, or `@`-prefixed.

### What happens on a bad field name

**At import**, the rule is rejected with a 400 and a per-field message:

```
query A (traces): group-by field "issue_reason" is not accepted by the alert engine
and would freeze the rule — not supported by the alert engine
```

That guard exists because of the **evaluation-time** behaviour it prevents: a name the
engine can't resolve errors on *every* evaluation, and the engine then **holds the rule's
current state**. A new rule silently never fires; a rule already firing **freezes — it
never resolves, and editing its threshold has no effect**, because the query errors before
the threshold is checked.

The import-time allow-lists are a hand-maintained mirror of the engine's, with no automated
drift check — so treat a rule that validates but never fires as possibly hitting this, and
verify on the condition chart.

## Traps That Silently Change Your Rule

| Trap | Consequence |
|---|---|
| A `groupBy` entry missing `field`, `type`, or `is_attribute` | **The entire `groupBy` is emptied** — the rule fires as one global series instead of per-label |
| `value_operation` numeric (e.g. `p95`) with missing/bad `fields` | Silently degrades to **`row_count`** — a latency rule becomes a count rule |
| `fields[].type` not literally `"float"` for numeric ops | Same degradation |
| `unit: "ns"` / `"percent"` / `"short"` | Not valid values — silently becomes `auto`. Use `nanoseconds`, `percentage`, `number` |
| `frequency_type: "always"` alone | Silently downgrades to `at_least_once` — you must also send `threshold_frequency: "always"` |
| `notification_channel_ids: []` on a single-rule import | The editor requires ≥ 1 channel; the user **cannot click Create** |
| A hand-written `unified_filter` block | **Never read on import** — silently discarded |
| `advanced_query` alongside other `raw_filters` keys | `advanced_query` is **exclusive**; every other filter key is dropped |
| A `label` key on a `query_config` entry | Ignored — labels bind **positionally** (index 0 → `A`, 1 → `B`) |

Always tell the user to confirm the values on the import editor's **condition chart** before
clicking Create.

## Trace latency thresholds are in nanoseconds

The alert engine reads trace `duration` in **nanoseconds**, including the rollup
percentiles.

| User says | `threshold_value` |
|---|---|
| 100ms | `100000000` |
| 250ms | `250000000` |
| 500ms | `500000000` |
| 1s | `1000000000` |

`ns = ms × 1_000_000`. Set `"unit": "nanoseconds"`.

> [!NOTE]
> This differs from the **query** tools, where a `duration` WHERE filter is expressed in
> **milliseconds**. Alerts: nanoseconds. Queries: milliseconds. See
> [kubesense-traces](../kubesense-traces/SKILL.md).
>
> The product's own `type-tracing` starter template uses `threshold: 500` with a description
> saying "ms" — that is 500 *nanoseconds*. Don't copy it.

## Text and Pattern Filters

For a single body match, filter on **`body` directly** — `raw_filters: {"body": ["timeout"]}`
— and read the note under the logs field list for what that costs and how it matches.

For anything the simple prefix operators cannot express — an OR across two phrases, a mix
of body text and another field, a status-code class — `unified_filter` does not work
through import, and the only working route is the reserved `advanced_query` key holding a
WHERE string:

```json
"raw_filters": {
  "advanced_query": ["body SUBSTR_ILIKE \"timeout\" OR body SUBSTR_ILIKE \"connection refused\""]
}
```

Same for a status-code class — `return_code LIKE "5__"` (`_` = one character: `4__` = 4xx,
`40_` = 40x). Remember `advanced_query` **replaces** all other filter keys, so fold every
condition into the one string.

`raw_filters` values also support prefix operators for simple cases:

| Prefix | Operation | Example |
|---|---|---|
| none | IN | `{"level": ["ERROR"]}` |
| `-` | NOT IN | `{"return_code": ["-200"]}` |
| `>` `<` `>=` `<=` | comparison | `{"duration": [">500000000"]}` |

Because these filter shapes are fiddly and a filter that fails to bind is **silent** (the
rule then matches *everything*, not nothing), the reliable path is: build the condition in
the Explorer's advanced-query editor, attach it in the alert editor, verify on the condition
chart, then Export.

## Placeholders in a Name or Description

`{{...}}` in a rule's name or description is expanded **per firing series**, so one rule
produces one differently-titled alert per group. There are two namespaces.

**The rule's own labels** — its group-by keys and any `labels` it carries. Resolution runs
in this order, per placeholder:

1. **The label key itself.** An exact match always wins.
2. **The UI-label alias**, and only when that column is in *this* alert's labels. 16 fields
   are shown in the Group By dropdown under one name and stored under another:

   ```
   service→app_service   domain→cluster        resource→clustered_resource
   container→container_name  node→host         instance→pod_name
   type→level            status_code→return_code  method→subtype
   protocol→protocol_type  role→kind           reason→issue_reason
   primary_workload→perspective_workload   primary_namespace→perspective_namespace
   associate_workload→partner_workload     associate_namespace→partner_namespace
   ```

   Rule 1 is what keeps this unambiguous: `service` is the UI label for both logs' own
   `service` and traces' `app_service`, and each rule resolves against its own column.
   An alias never *invents* a value — group by neither and `{{domain}}` stays literal, so a
   typo stays visible instead of silently rendering empty.
3. **The same name as an attribute.** Group by the attribute `topic` and `{{topic}}`
   resolves it; the stored key is `@topic`, and `@` cannot be typed inside `{{ }}`.

**The alert's own facts**, under a reserved `Alert.` prefix:

```
{{Alert.status}}  {{Alert.value}}  {{Alert.threshold}}  {{Alert.thresholdOperator}}
{{Alert.severity}}  {{Alert.timeWindow}}  {{Alert.frequency}}
{{Alert.startedAt}}  {{Alert.startsAt}}  {{Alert.endsAt}}
{{Alert.evaluatedFrom}}  {{Alert.evaluatedTo}}
```

- The prefix is **not** optional and is not decoration. Bare `{{status}}` resolves the
  rule's *label* `status` first, so on a rule grouped by an attribute called `status` it
  printed "firing" instead of the value. The namespace removes the collision — no group-by
  can produce a key beginning `Alert.`.
- `{{Alert.status}}` renders `firing`, `resolved` or `no_data` — lowercase tokens, not
  display text.
- **`startedAt`/`endsAt` bound the episode; `evaluatedFrom`/`evaluatedTo` bound the query
  window.** A rule firing for three hours on a 5m window has a three-hour episode and a
  five-minute window, so a "show me what fired this" link built from the episode shows
  three hours of data to explain five minutes of it. Build links from `evaluated*`.
- An unknown fact stays **literal** rather than rendering a zero — `{{Alert.value}}` for a
  series with no reading must not read `0.00`, because `0.00` is also a real measurement.

## Maintenance Windows

Scheduled downtime, Datadog-style: a window mutes alert **notifications** for a scope over
a period. Nothing else changes — telemetry still arrives, rules still evaluate, alerts
still fire and resolve, history still records, SLO budgets still burn.

That matters when reading: a muted alert looks completely normal in `list-active-alerts`
and `get-alert-history`. If the user asks why a firing alert paged nobody, a window is a
candidate answer, and **no MCP tool exposes one** — say that and point at Alerts →
Maintenance Windows rather than guessing from the alert's own data.

- Scope is rule ids and/or **label matchers**, with Alertmanager's semantics: anchored
  regex, and an absent label reading as empty.
- An empty scope mutes **nothing** unless `scope_all` is set explicitly — a blank form
  cannot black out the estate.
- Schedules are one-off, daily or weekly, stored as a wall-clock time plus an IANA zone, so
  "01:00 nightly" stays 01:00 across a DST change.
- Suppression is an Alertmanager **silence**, not the engine going quiet. Going quiet would
  trip `resolve_timeout` and page a false all-clear.

## Import JSON

For the complete top-level schema, `query_config` shapes, every enum, bulk import, and
verified working examples for metrics/logs/traces/formula rules, read
**[references/import-json.md](./references/import-json.md)**.

The essentials:

- Flat fields (`threshold_operator`, `threshold_value`) and **plain duration strings**
  (`"5m"`, not `*_prometheus_format`) — except `breach_counting_window`, which import reads
  as `breach_counting_window_prometheus_format`.
- One rule → a single JSON **object**. Multiple rules → **one JSON array**, which
  bulk-imports with a dry-run review. Never emit separate per-rule snippets.
- `enabled` and `query_type` are **ignored** on import — the server hardcodes enabled and
  derives the type from the first query's `selectedMode`.
- Applied via **Alerts → Alert Rules → Import JSON** → review → Create. Nothing is written
  until the user confirms.

Never claim an alert was created via the import path — the user imports and confirms it.

## Discovery First

Never invent a metric name, field, or channel id.

| You need | Call |
|---|---|
| A metric name | `get-available-metrics` → `get-metric-labels` |
| Log/trace field names and values | `get-trace-or-log-fields` |
| Channel ids | `list-notification-channels` |
| Your own username | `get-current-user` |

For an unfamiliar rule shape, ask the user to **Export a similar existing rule** and modify
it — that guarantees the `query_config` shape is valid.

Without MCP you may still generate logs/traces rules from the allow-lists above (they are
canonical, not guesses), but you may **not** invent PromQL metric names — those are
cluster-specific. Ask the user, or have them export a reference rule.

## Rules

1. Discover every metric, field, and channel id before emitting a rule.
2. Use the **alert engine's** field lists, not the query tools' catalog labels. `level` not
   `type`; `app_service` not `service` **for traces**. `body` filters, but never groups.
3. `list-notification-channels` first. Never invent an id; `[]` blocks a single-rule import.
4. Trace latency thresholds in **nanoseconds**, `unit: "nanoseconds"`.
5. Emit all three keys on every `groupBy` entry, or grouping is silently dropped.
6. Numeric `value_operation` needs `fields` with `type: "float"`, or it degrades to
   `row_count`.
7. `unit` must be a real formatter value — `nanoseconds`, `milliseconds`, `percentage`,
   `bytes`, `CPU`, `number`, `raw`.
8. Text/class filters go in `raw_filters.advanced_query`, never `unified_filter` — and
   `advanced_query` displaces all other filter keys.
9. Query labels are **positional**; `metric_query_label` names the thresholded query
   (single → `A`; formula → the formula's label).
10. One rule → object; multiple → **one array**. One code block either way.
11. `no_data_state: "firing"` only when a metric *disappearing* is the incident (a
    gauge/heartbeat). Never for a count/rate/change rule — a healthy window returns an empty
    result, not 0, so `firing` misfires at value 0. Use `normal`.
12. `more_than_once` needs `breaches_count` (≥ 2); `always` needs `threshold_frequency` set
    too.
13. `{{field}}` placeholders in `name` resolve per firing series against a group-by key or
    a rule label, e.g. group by `workload` → `"High latency {{workload}}"`. One that
    matches nothing stays **literal**, which is how you spot a typo. The alert's own facts
    need the `Alert.` prefix — `{{Alert.value}}`, not `{{value}}`.
14. Tell the user to review the condition chart before creating, and never claim a rule was
    created unless `create-alert` actually returned an id.
