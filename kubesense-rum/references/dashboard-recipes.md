# RUM Dashboard Recipes

Panel fragments for the questions RUM dashboards usually ask. Every query is a stored
panel query: `selectedMode: "rum"` plus `rumEventType`, the WHERE clause in
`filters.advanced_query`, `filterMode: "ADVANCED_QUERY"`. See
[RUM query](../../kubesense-dashboards/SKILL.md#rum-query) for the shape and
[field-catalog.md](./field-catalog.md) for the fields; check a field with `get-fields`
before you use it. Test a recipe with `analyze-telemetry` (`selectedMode: "rum_view"`
there) before you save it.

Fragments below show only the fields that matter. Add `label`, `columnFields: []` and
`filterMode: "ADVANCED_QUERY"` to each query; a formula query is
`{"selectedMode": "formula", "label": "C", "expression": "..."}` and comes after the queries
it uses.

## Exact single numbers: calculation `total`

A stat panel reduces a range query's per-bucket values to one number. With `mean`, `sum` or
`last` that overcounts uniques (a user seen in two buckets counts twice) and averages
percentiles (the mean of per-bucket p75s is not the p75). Set
`config.valueOptions.calculation` to **`total`** instead. Each query is then sent with
`aggregator: "total"`, and the server computes the value over the whole range in one
aggregate, alongside the range series that still draws the trend. Formulas on a `total`
stat use those exact scalars.

```json
{
  "panelType": "stat",
  "config": { "valueOptions": { "show": "calculate", "calculation": "total" } },
  "queries": [ { "...": "..." } ]
}
```

Use `total` for anything distinct or percentile: `unique_count`, `p50` to `p99`. For a plain
`row_count` or `sum`, `sum` gives the same number. `total` applies to ClickHouse sources
(RUM, logs, traces, events), not to metrics queries. It also applies to a grouped
`table` or `topList` panel's per-group value; a group the whole-range query ranks outside
its cap shows no value.

> Status: `total` is part of the kubeapi contract (`aggregator: "total"`). The webapp
> `VALUE_CALCULATION_OPTIONS` and the `valueOptions.calculation` zod enum on this branch
> list only the ten values in [panel-config](../../kubesense-dashboards/references/panel-config.md#valueoptions)
> until the webapp change lands; an unknown value falls back to `last`. Check that the
> deployed webapp accepts `total` before you rely on it in saved dashboards.

**Unique users** (`user_id` on `rum_session`, also on every other event type):

```json
{
  "selectedMode": "rum", "rumEventType": "session",
  "filters": { "advanced_query": ["env = production"] },
  "aggregation": { "function": "unique_count",
    "fields": [ { "field": "user_id", "type": "string", "is_attribute": false } ] }
}
```

**p75 LCP** (view, nanoseconds; leave `fieldConfig.unit` unset so it shows as a duration).
Unmeasured views have `lcp = 0` and measures skip zeros, so the p75 is over measured
views only:

```json
{
  "selectedMode": "rum", "rumEventType": "view",
  "aggregation": { "function": "p75",
    "fields": [ { "field": "lcp", "type": "float", "is_attribute": false } ] }
}
```

The same shape gives p75 of `inp`, `fcp`, `first_byte` (TTFB) and `loading_time`. `cls` is
a unitless score, not a duration: p75 of `cls` needs no unit.

## Crash-free users %

Formula `(1 - A/B) * 100` with calculation `total` (stat panel, unit `percentage`):

| Query | Event | WHERE | Aggregation |
|---|---|---|---|
| A | `session` | `crash_count > 0` | `unique_count` of `user_id` |
| B | `session` | none (or the same app filter as A) | `unique_count` of `user_id` |
| C | formula | | `(1 - A/B) * 100` |

Any filter on B (for example `env = production`) must also be on A. Crash-free sessions is
the same with `row_count` on both. To count from errors instead, A is `rumEventType:
"error"` with `severity = crash` (the label for `is_crash`) and `unique_count` of
`user_id`.

## Error rate and crash rate on quiet apps

A formula whose input has no rows in the range no longer fails. A `row_count`, `sum` or
`unique_count` input reads as zero; an `avg`, `min`, `max` or percentile input gives an
empty result (no value) for the formula. So `(B/A)*100` shows no value on an app with no
sessions, and `0` on an app with sessions but no errors. A new app does not need a guard
query.

```json
{ "selectedMode": "formula", "label": "C", "expression": "(B/A)*100" }
```

with A = `session` `row_count`, B = `session` `row_count` where `error_count > 0` (error
rate) or `crash_count > 0` (crash rate).

## Good / needs improvement / poor per Web Vital

A bucket function is not needed: count views by threshold with filters, then divide.
Durations are nanoseconds and `0` means not measured. Use the `_ms` twin in the filter, and
always exclude `0` explicitly or unmeasured views count as good.

% good LCP = `A/B*100`, with A and B both `rumEventType: "view"` and `row_count`:

| Query | WHERE |
|---|---|
| A (good) | `lcp_ms > 0 AND lcp_ms <= 2500` |
| B (all measured) | `lcp_ms > 0` |
| C | formula `A/B*100` |

Needs improvement is A with `lcp_ms > 2500 AND lcp_ms <= 4000`; poor is `lcp_ms > 4000`.
Put the three shares in one panel as three formulas over the same B.

Thresholds are the standard [web.dev](https://web.dev/articles/vitals) ones, measured at the
75th percentile of page loads. Fields are on `rum_view`, browser only:

| Vital | Field in filter | Good | Needs improvement | Poor |
|---|---|---|---|---|
| LCP | `lcp_ms` | `<= 2500` | `<= 4000` | `> 4000` |
| INP | `inp_ms` | `<= 200` | `<= 500` | `> 500` |
| FCP | `fcp_ms` | `<= 1800` | `<= 3000` | `> 3000` |
| TTFB | `first_byte_ms` | `<= 800` | `<= 1800` | `> 1800` |
| CLS | `cls` (unitless) | `<= 0.1` | `<= 0.25` | `> 0.25` |

`cls` has no `_ms` twin and a real CLS of `0` is a valid perfect score, so it cannot be told
from unmeasured. Filter it with `cls >= 0` for the denominator and accept that views that
did not report CLS count as good. Formula expressions take no decimal point, but the
thresholds live in the WHERE clause, so `0.1` is fine there.

## Apdex

Apdex = (satisfied + tolerating / 2) / total, with T the satisfied threshold and 4T the
tolerating limit. T is your choice; this uses T = 1 s on `loading_time` (a nanosecond
view duration, so filter on `loading_time_ms`). All queries are `view` `row_count`:

| Query | WHERE |
|---|---|
| A (satisfied) | `loading_time_ms > 0 AND loading_time_ms <= 1000` |
| B (tolerating) | `loading_time_ms > 1000 AND loading_time_ms <= 4000` |
| C (total) | `loading_time_ms > 0` |
| D | formula `(A+B/2)/C` |

State T in the panel title or description (`Apdex (T = 1 s)`). Add `AND view_name = "..."`
or group by `view_name` for per-page scores.

## Top error messages, issues and URLs

Group a `row_count` panel (`table` or `topList`) by one of these `rum_error` fields, sorted
`DESC`:

| Group by | Label shown | Event types |
|---|---|---|
| `error_message` | first 200 characters | error |
| `issue_id` | the id | error |
| `fingerprint` | the id | error |
| `view_url` | URL path, no query string or fragment | view, action, error, resource, long_task |
| `resource_url` | URL path, no query string or fragment | error, resource |

```json
{
  "selectedMode": "rum", "rumEventType": "error",
  "filters": { "advanced_query": ["severity = crash"] },
  "aggregation": { "function": "row_count" },
  "groupBy": [ { "field": "error_message", "type": "string", "is_attribute": false } ],
  "limit": 10
}
```

Grouping returns the top N groups by the measure, N being the page size (`pagination.page_size`
on a panel query, `limit` in `analyze-telemetry`). These fields are still not LIKE-able.
Because the URL label is a path, filtering on it with `view_url = "/cart"` matches only
URLs that have no query string; a drill-down from a group needs the path to match the
full stored URL, so prefer filtering on `view_name` or `issue_id` for drill-downs. A message
longer than 200 characters is grouped by its first 200; filters still read the full text.

## ANR rate (mobile)

`error_category` is a string field on `rum_error` (`LIKE` is allowed). The ANR value is
`ANR`, as the webapp's Android dashboard filters on `filter_error_category = "ANR"`; the
field catalog lists no enum values, so confirm with a group-by on `error_category` first.
`rum_session` has no `error_category` field.

| Query | Event | WHERE | Aggregation |
|---|---|---|---|
| A | `error` | `error_category = ANR` | `unique_count` of `session_id` |
| B | `session` | none | `row_count` |
| C | formula | | `(A/B)*100` |

ANR-free sessions % is `(1 - A/B) * 100`. Use calculation `total` on the stat. B must carry
the same `env` / `application_id` filter as A.

## Sessions by city, state or service

On `rum_session`, `city`, `state` and `service` are list columns (a session can have
several): filter-only, no group-by. On `rum_view` they are scalar and groupable. Group
views and count the distinct sessions:

```json
{
  "selectedMode": "rum", "rumEventType": "view",
  "aggregation": { "function": "unique_count",
    "fields": [ { "field": "session_id", "type": "string", "is_attribute": false } ] },
  "groupBy": [ { "field": "city", "type": "string", "is_attribute": false } ]
}
```

A session that visits views in two cities counts once in each. With calculation `total` on
a `table` or `topList` panel the per-group value is the exact distinct count.
