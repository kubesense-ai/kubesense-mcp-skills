---
name: kubesense-rum
description: Aggregate real user monitoring (RUM) data via KubeSense MCP — sessions, views, actions, errors, resources and long tasks from browser and mobile apps. Covers the rum_<type> signals, the per-event-type field catalog, which fields accept LIKE or group-by, nanosecond durations and their _ms/_s twins, feature flags and attributes, and the dashboard panel shape. Counts, rates and percentiles only; there is no row search, alerting, SQL or SPL for RUM.
metadata:
  version: "1.0.0"
  author: kubesense
  repository: https://github.com/kubesense-ai/kubesense-mcp-skills
  tags: kubesense,rum,real-user-monitoring,web-vitals,sessions,frontend,errors,observability
---

# KubeSense RUM

Requires the KubeSense MCP server; see **[kubesense-mcp](../kubesense-mcp/SKILL.md)** for
connection, auth, and the shared WHERE-clause reference. RUM queries resolve RBAC against
the **RUM** module (`rbac(rum)`). A key without it fails with
`rbac(rum): this API key does not have access to this resource`; ask for the RUM grant
rather than retrying.

## Signals

RUM has six signals, one per event type. Each reads its own table.

| Signal | One row is | Typical question |
|---|---|---|
| `rum_session` | a user session | how many sessions, how many had errors |
| `rum_view` | a finished page or screen view | LCP, load time, views per page |
| `rum_action` | a click, tap or scroll | which actions are slow or frustrating |
| `rum_error` | a captured error or crash | which errors, how many crashes |
| `rum_resource` | an HTTP or asset request | slow or failing requests, by host |
| `rum_long_task` | a main-thread long task | what blocks the UI |

`rum_view` counts only ended views of non-system sessions. Every row is placed in time by
its own `start_timestamp`, so a long session is counted in the window where it started.

## Tools

| Tool | Use when | Notes |
|---|---|---|
| `get-fields` (`signal: "rum_view"`, …) | Always, first | Field catalog for that event type |
| `analyze-telemetry` | Every RUM question | One sub-query per signal, set with `selectedMode` |

There is no `analyze-rum` and no `search-rum`. `analyze-logs` and `analyze-traces`
do not take RUM signals. To compare RUM with logs or traces, or to compute a rate, put
several sub-queries in one `analyze-telemetry` call and add a formula; see
[multi-query](../kubesense-mcp/references/multi-query.md).

## Discover First

Call `get-fields` with the signal you will query. The field set differs per event type:
`lcp` exists only on `rum_view`, `error_type` only on `rum_error`, and `view_name` allows
LIKE on `rum_view` but not elsewhere. The full catalog for every event type is in
**[references/field-catalog.md](./references/field-catalog.md)**; use it to check a name
before the call, and `get-fields` as the authority for the deployment you are talking to.

`get-fields` for RUM returns the static catalog only, in the usual TSV:

- The header line is `# signal=rum_view total_count=<N> truncated=<bool> note=RUM has no
  attribute-key scan; ...`. There is no `attribute_scan_error`. The note says to type a
  custom attribute as `@key` (no LIKE on attributes) and a feature flag as
  `feature_flag.<key>`.
- Operators come as sets (`# ops.o1=EQ|NEQ|IN|NIN|LT|GT|LTE|GTE`). A field that allows
  LIKE has a set that includes `LIKE` / `ILIKE`; an exact field such as `user_email` does
  not. Trust the set over any assumption about the field.
- A trailing `notes` column appears when some field has a note, for example
  `measure-only: aggregate or filter it, never group by it (milliseconds); platform: browser`
  on `lcp_ms` and `filter-only: not groupable; platform: browser` on `lcp_target_selector`.
- `enum_values` carries `severity`'s `crash` and `error`.
- Pass `search` to narrow the list (`search=lcp` returns `lcp`, `lcp_ms`, `lcp_s` and
  `lcp_target_selector`).

There is no attribute-key discovery. When the user needs a custom attribute, ask for the
key or infer it from their instrumentation, and type it with the `@` prefix. A wrong key
matches nothing and returns an empty result, not an error.

## WHERE Syntax

The shared syntax from [kubesense-mcp](../kubesense-mcp/SKILL.md#where-syntax) applies,
with the field names from the RUM catalog.

```
env = production AND browser_name = Chrome
severity = crash AND country IN (US, DE)
view_name ILIKE "%checkout%"                    (rum_view only)
lcp_ms > 2500 AND browser_name = Chrome         (rum_view)
status_code >= 500 AND resource_host = api.example.com   (rum_resource)
error_count > 0                                 (rum_session)
feature_flag.new_checkout = true                (any event type)
@checkout.step = payment                        (attribute)
```

Quote values that contain `/`, `:`, `%` or a space. Write `NOT (x IN (...))`, not
`x NOT IN (...)`.

## Rules

1. **LIKE and ILIKE only on fields whose `LIKE` column says `yes`** in the catalog.
   Those are the low-cardinality columns (`env`, `country`, `error_type`, `action_name`,
   `view_name` on `rum_view`). Everything else (`user_id`, `view_url`, `resource_url`,
   `error_message`, `view_name` on the other event types) takes `=` and `IN`. A LIKE on
   them is refused with `LIKE is not supported on <field>; use = or IN`.
2. **No LIKE on `@attribute` fields.** Attributes take `=`, `!=`, `IN`, `<`, `>`, `<=`
   and `>=`. Comparisons need a number. `@plan LIKE ...` is refused with
   `operator "LIKE" not allowed for rum_view attribute field "plan"`.
3. **Array fields filter only.** `service`, `state`, `city`, `network_connectivity` and
   `ip` on `rum_session`, `ip` on `rum_view`, and `action_id` on `rum_error`,
   `rum_resource` and `rum_long_task` hold lists. `=` and `IN` test membership. They
   cannot be grouped or measured.
4. **Durations are nanoseconds.** Raw columns (`lcp`, `duration`, `loading_time`,
   `time_spent`, …) are stored and returned in nanoseconds, and cannot be a group-by.
   Each has an `_ms` and an `_s` twin (`lcp_ms`, `duration_s`) that you can filter on and
   measure in the unit you read. Prefer the twin everywhere: `lcp_ms > 2500` filters at
   2.5 seconds. The twins are measure and filter only, never a group-by.
5. **Group-by is `no` for free-search ids and text** (`session_id`, `view_id`,
   `view_url`, `error_message`, `trace_id`, …). Group by a low-cardinality field instead.
6. **`feature_flag.<key>`** filters on every event type. It groups or measures only on
   `rum_view` and `rum_error`, where the flag value is stored on the row. On the other
   four it is stored per session, so a group-by there is refused. Keys are
   case-sensitive and values are text (`true`, `dark`, `5`). A group-by on a flag key
   (`feature_flag.new-checkout`) is confirmed on `rum_view`. The `where` form follows the
   engine source and has not been run against a live server.
7. **Attributes need `@`** in `where` (`@checkout.step`) and `is_attribute: true`
   without `@` in `group_by_fields` / `fields`. There is no discovery for the key.
8. **`severity`** on `rum_error` is `crash` or `error`, lowercase. It is the label for
   `is_crash`; type `severity`, not `is_crash` as a string.
9. **Boolean fields** (`session_is_active`, `slow_rendered`) take `true` or `false`.
10. **Platform-specific fields are not enforced.** `lcp` is browser-only and
    `battery_level` is mobile-only. Filtering on one for the wrong application type matches
    nothing and raises no error.
11. **`value_operation`** is `row_count`, `unique_count`, `avg`, `sum`, `min`, `max`,
    `p50`, `p75`, `p90`, `p95` or `p99`. `row_count` takes no field. Everything else takes
    exactly one `fields` entry. The numeric operations need a number field or an
    attribute; `unique_count` takes any non-list field.
12. **`alert_mode`, `group_by_present_only` and `lookback_seconds` are refused** for RUM.

## analyze-telemetry

Set `selectedMode` to the signal. Omitting it makes the sub-query a metrics query.

**p90 LCP per page, Chrome only, in milliseconds**

```json
{
  "from_time": "2026-10-20T10:00:00Z",
  "to_time": "2026-10-20T11:00:00Z",
  "query_type": "instant",
  "queries": {
    "A": {
      "selectedMode": "rum_view",
      "where": "browser_name = Chrome",
      "group_by_fields": [ { "field": "view_name", "is_attribute": false } ],
      "value_operation": "p90",
      "fields": [ { "field": "lcp_ms", "is_attribute": false } ],
      "sort_direction": "DESC",
      "limit": 10
    }
  }
}
```

**Crashes per hour by error type**

```json
{
  "from_time": "2026-10-20T00:00:00Z",
  "to_time": "2026-10-21T00:00:00Z",
  "query_type": "range",
  "queries": {
    "A": {
      "selectedMode": "rum_error",
      "where": "severity = crash AND env = production",
      "group_by_fields": [ { "field": "error_type", "is_attribute": false } ],
      "value_operation": "row_count"
    }
  }
}
```

**Share of sessions that hit an error** — two queries and a formula, both ungrouped:

```json
{
  "from_time": "2026-10-20T10:00:00Z",
  "to_time": "2026-10-20T11:00:00Z",
  "query_type": "instant",
  "queries": {
    "A": { "selectedMode": "rum_session", "value_operation": "row_count" },
    "B": { "selectedMode": "rum_session", "where": "error_count > 0", "value_operation": "row_count" },
    "C": { "query_type": "formula", "expression": "(B/A)*100" }
  }
}
```

**Slowest hosts by p95 request time, failed requests only**
`selectedMode: rum_resource`, `where: "status_code >= 500"`,
`group_by_fields: [{"field":"resource_host"}]`, `value_operation: p95`,
`fields: [{"field":"duration_ms"}]`

**Errors by feature flag value**
`selectedMode: rum_error`, `group_by_fields: [{"field":"feature_flag.new_checkout"}]`,
`value_operation: row_count`

**Sessions by a custom attribute**
`selectedMode: rum_session`, `group_by_fields: [{"field":"checkout.step","is_attribute":true}]`,
`where: "@checkout.step IN (cart, payment)"`

## Dashboard Panels

A stored panel query and the analyze call name the event type differently:

| | Field | Value |
|---|---|---|
| analyze-telemetry sub-query | `selectedMode` | `rum_view` |
| dashboard panel query | `selectedMode` + `rumEventType` | `"rum"` + `"view"` |

A panel with `selectedMode: "rum_view"` fails validation, and `"rum"` without
`rumEventType` is refused on save. The panel shape, with a `_ms` measure and its unit, is
in **[kubesense-dashboards](../kubesense-dashboards/SKILL.md#rum-query)**. Test the query
with `analyze-telemetry` first, then translate it.

## Limits

- **Retention.** Raw RUM rows are kept 7 days for `rum_action`, `rum_error`,
  `rum_resource` and `rum_long_task`, and 30 days for `rum_session` and `rum_view`, by
  default. A longer window returns only what is still stored; deployments can change the
  retention.
- **No row search.** There is no tool that lists individual sessions, errors or
  resources. Answer with aggregates, and group by the narrowest low-cardinality field.
- **No alerts, SQL or SPL.** RUM is not a datasource for alert rules, `execute-sql` or
  `execute-spl`. Say so rather than approximating with logs.
- **No attribute-key discovery.** See Discover First.

## Failure Messages

Seen from a live server:

| Message | Cause |
|---|---|
| `unknown field "services" for signal=rum_session ...` | A storage name; type the catalog name (`service`) |
| `analysis failed: cannot group by lcp_ms` | Rule 4: `_ms` / `_s` twins are measure and filter only |
| `analysis failed: LIKE is not supported on user_email; use = or IN` | Rule 1 |
| `operator "LIKE" not allowed for rum_view attribute field "plan" — use one of: EQ, NEQ, ...` | Rule 2 |
| `rbac(rum): this API key does not have access to this resource` | The key lacks the RUM module |

Worded from the kubeapi source, not seen live:

| Message | Cause |
|---|---|
| `<field> is not a filterable field for <type>` | The field belongs to another event type, or is hidden |
| `<field> holds a list and cannot be grouped or measured; filter on it instead` | Rule 3 |
| `cannot group by <field>; it is a duration in nanoseconds` | Rule 4, on a raw column such as `lcp` |
| `cannot group by <field>` | Rule 5 |
| `feature flags are stored per session for <type>; filter on them instead` | Rule 6 |
| `<op> needs a numeric field; <field> is not numeric` | Measure on a string or boolean |
| `rum is not configured` | The deployment has no RUM database |
