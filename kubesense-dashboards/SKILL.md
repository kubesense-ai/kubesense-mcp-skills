---
name: kubesense-dashboards
description: Create KubeSense dashboards over metrics, logs, and traces — either directly with the create-dashboard MCP tool or as preset JSON the user imports — with the exact schema, the fields that hard-fail import, and the fields that silently discard your data instead of erroring. Includes validate-dashboard-json for checking a preset before you commit to it.
metadata:
  version: "2.1.0"
  author: kubesense
  repository: https://github.com/kubesense-ai/kubesense-mcp-skills
  tags: kubesense,dashboards,panels,json,import,preset,visualization
---

# KubeSense Dashboards

Build a dashboard preset — the same shape the **Export** button produces, so an exported
dashboard can be edited and re-imported.

Two ways to deliver it:

| | `create-dashboard` MCP tool | Preset JSON |
|---|---|---|
| Applied by | the agent (write tool, needs approval) | the user, via Dashboards → Import |
| Use when | the user asked you to *create* one | they asked for the JSON, or want to review first |
| Shape to emit | the preset object itself | the import envelope, with `preset` **stringified** |

Both go through the same server-side schema check, so a preset that passes
`validate-dashboard-json` is one that both paths accept.

## When to Use

- "Create a dashboard for…" / "Build a dashboard with panels for…" → `create-dashboard`
- "Give me the dashboard JSON for…" → preset JSON
- "Generate a dashboard preset" → preset JSON

## Always Validate Before You Finish

Call **`validate-dashboard-json`** on the preset before creating it or handing it over.
It stores nothing, so call it as often as you need.

```
# valid=false findings=2
path                              rule   message
/panels/0/queries/0/selectedMode  shape  value must be one of 'logs', 'metrics', 'traces', 'formula'
/gridLayout/0                     shape  must have required property 'h'
```

Each `path` is a JSON Pointer to the exact value to fix. Repeat until `valid=true`.

Pass the **preset object** as `document` — not the import envelope with the stringified
`preset` field. Same for `create-dashboard`'s `preset` argument.

Validation checks *shape*, not whether the data exists. A query against a metric nobody
collects is well-formed and will render empty, so discover names first.

## Discover Fields First

If the KubeSense MCP server is connected, discover real names before writing queries —
never guess a metric, group-by, or filter field.

| To find | Tool |
|---|---|
| Metric names | `get-available-metrics` |
| Metric labels (for `by`) | `get-metric-labels` |
| Log/trace fields | `get-trace-or-log-fields` |

Dashboard queries use **storage-level field names**, not the MCP catalog labels — the
webapp posts these directly. Take field names from the discovery output's storage column
where they differ, and tell the user to confirm on the panel preview. See
[kubesense-mcp](../kubesense-mcp/SKILL.md) for the label/storage distinction.

Without MCP, fall back to user-provided names and say they need verifying.

## Output Format

```json
{
  "name": "<dashboard name>",
  "description": "",
  "preset": "<stringified JSON of the preset object>"
}
```

> [!IMPORTANT]
> **In this envelope, `preset` is a JSON *string*, not a nested object.** The validator
> declares `preset: z.string()` and only runs the preset schema after `JSON.parse(preset)`.
> Emitting an object fails with *"Preset must be a valid JSON string that matches the
> dashboard preset schema"*.
>
> This applies to the **import envelope only**. `create-dashboard` and
> `validate-dashboard-json` take the preset object itself — passing a stringified blob to
> them works too, but do not wrap it in this envelope.

`name` is required and non-empty. `description` is optional.

The object you stringify:

```json
{
  "gridLayout": [],
  "panels": [],
  "variables": [],
  "subGrids": [],
  "subGridLayout": []
}
```

Only `gridLayout` and `panels` are required; the rest default to `[]`. A sixth optional
key, `publicDashboardPath` (string), also validates.

## Minimal Valid Dashboard

Verified against the live validator:

```json
{
  "name": "Minimal",
  "description": "",
  "preset": "{\"gridLayout\":[{\"i\":\"0\",\"x\":0,\"y\":0,\"w\":12,\"h\":4}],\"panels\":[{\"name\":\"Up\",\"panelType\":\"timeSeries\",\"queries\":[{\"selectedMode\":\"metrics\",\"label\":\"A\",\"selectedMetric\":\"up\",\"functions\":[]}],\"config\":{}}],\"variables\":[],\"subGrids\":[],\"subGridLayout\":[]}"
}
```

## What Hard-Fails Import

Get these wrong and import is rejected with an error:

1. `preset` not a string.
2. Missing or empty top-level `name`.
3. Missing `gridLayout` or `panels`.
4. A `gridLayout` item missing any of `i`, `x`, `y`, `w`, `h`, or with a wrong type
   (`"6"` instead of `6`).
5. A panel missing `name`, or `name: ""`.
6. A panel missing the `queries` array (it may be `[]`, but the key must exist).
7. A query whose `selectedMode` is not `metrics` | `logs` | `traces` | `formula`.
8. **A logs/traces query missing `columnFields`** — the single hard-required field on
   those queries.
9. A `columnFields[]` entry with `field: ""`.
10. A formula missing `expression`, or one containing lowercase letters or a decimal point.
11. A formula referencing an undefined label, referencing itself, placed *before* the
    queries it references, or with a multi-character label.

## What Silently Destroys Your Data

More dangerous than hard failures — these validate cleanly and then discard what you sent.
Almost every field carries a `.catch()`, so **a single bad value resets its whole array or
object to the default**.

| Field | On a bad value |
|---|---|
| `functions` (metrics query) | **The entire array is wiped to `[]`** — one malformed entry loses every function |
| `variables` | **All variables deleted** — one invalid variable empties the array |
| `subGrids` | All sub-grids dropped |
| `subGrids[].panels` | That row's panels emptied |
| `aggregation` | Resets to `{"function": "row_count"}` |
| `panelType` | Resets to `"timeSeries"` |
| `chart_type` | Resets to `"table"` |
| `yAxisLabelFormatter` | Resets to `"auto"` |
| `colorScheme` | Resets to `{"type":"palette","palette":"default"}` |
| `step` | Non-integer (e.g. `60.5`) resets to `"auto"` |
| `pagination` | `page_size > 500` resets the whole object to `{page:1,page_size:50}` |

Because of this, **prefer omitting an optional field over guessing its value** — an
omitted field takes the default; a wrong one can take out its siblings.

> [!WARNING]
> **`gridLayout` must have at least as many entries as `panels`.** Panels and layout are
> matched **positionally by array index**, not by the `i` value. A short `gridLayout`
> passes validation and then throws a TypeError when the dashboard renders. The `i` string
> is only used to identify sub-grid rows (via a `sg-` prefix); real exports set it to the
> index (`"0"`, `"1"`, …).

## Panel

```json
{
  "name": "CPU by namespace",
  "description": "",
  "panelType": "timeSeries",
  "queries": [],
  "config": {}
}
```

`panelType` — 9 values: `timeSeries`, `stat`, `table`, `list`, `bar`, `pie`, `topList`,
`spl`, `sql`. Note camelCase `timeSeries`.

`config` can never fail import (the whole object catches), so `{}` is always safe and
inherits every default. For the full field list, defaults, and the `colorScheme` /
`thresholds` / `alignColumns` shapes, read
**[references/panel-config.md](./references/panel-config.md)**.

Three config fields the old format got wrong:

- **`thresholdDisplayMode`**, not `enableThresholds`. Values: `off` (default), `lines`,
  `lines_dashed`, `filled_regions`, `filled_regions_and_lines`,
  `filled_regions_and_lines_dashed`.
- **`colorScheme`**, not `colorPalette`. A 5-variant union; the palette variant is
  `{"type":"palette","palette":"default"}` and the only palette keys are `default`,
  `success`, `warning`, `error`.
- **`mergeTables`** is `z.literal(true)` and lives in the defaults — it is **always
  `true`** and cannot be disabled. Sending `false` silently becomes `true`. Just omit it.

### Y-axis units

`yAxisLabelFormatter` accepts **199 values** (the same enum as `fieldConfig.unit`).

> [!WARNING]
> `percent`, `percent_unit`, `short`, `ops`, `bps`, `celsius`, `fahrenheit`, and `none`
> **do not exist** and silently become `auto`. Use `percentage`, `CPU` / `mCPU`,
> `bytes/sec`, `number` instead.

Common ones: `auto`, `number`, `percentage`, `bytes`, `bytes/sec`, `nanoseconds`,
`microseconds`, `milliseconds`, `seconds`, `mCPU`, `CPU`, `dollars`. Use `nanoseconds` for
any panel aggregating trace `duration` — the formatter auto-scales ns → µs/ms/s. Full list
in [references/panel-config.md](./references/panel-config.md).

## Queries

Discriminated on `selectedMode`: `metrics` | `logs` | `traces` | `formula`. Note `spl` is
**not** a valid `selectedMode` — use `panelType: "spl"` with a logs/traces query and
`filterMode: "SPL"`.

### Metrics query

```json
{
  "selectedMode": "metrics",
  "label": "A",
  "selectedMetric": "container_cpu_usage_seconds_total",
  "functions": [],
  "filters": {},
  "queryMode": "builder",
  "promql": "",
  "visible": true,
  "labelOptions": { "type": "auto" },
  "pagination": { "page": 1, "page_size": 50 },
  "fieldConfig": {}
}
```

Every field is optional. `queryMode` is `builder` or `code` — use `code` with `promql`
set, `builder` with `selectedMetric` + `functions`.

`variables` is **auto-derived** from filters and promql (`$name` references) — anything you
supply is overwritten. Don't bother setting it.

### Logs / traces query

```json
{
  "selectedMode": "logs",
  "label": "A",
  "columnFields": [],
  "filters": {},
  "queryMode": "builder",
  "filterMode": "MFD",
  "aggregation": { "function": "row_count" },
  "groupBy": [],
  "chart_type": "table",
  "visible": true,
  "sorting": {
    "sortBy": { "field": "", "type": "string", "is_attribute": false },
    "sortOrder": "ASC"
  },
  "query": "",
  "pagination": { "page": 1, "page_size": 50 },
  "fieldConfig": {}
}
```

> [!IMPORTANT]
> **`columnFields` is required** — include it on every logs/traces query, even as `[]`.
> Omitting it is a hard import failure. Entry shape:
> `{"field": "namespace", "type": "string", "is_attribute": false}` with optional `alias`
> and `label`. `field` must be non-empty.

- `chart_type` — 7 values: `table`, `stat`, `bar`, `pie`, `topList`, `timeseries`, `list`.
  **Lowercase `timeseries`** — `timeSeries` silently becomes `table`. This is a query-level
  field, separate from the panel-level `panelType`.
- `filterMode` — `MFD`, `ADVANCED_QUERY`, `SPL`, `SQL`. Use `ADVANCED_QUERY` with a `query`
  string for anything MFD's equality-only filters can't express (e.g. a latency threshold).
- `groupBy` entries use the same shape as `columnFields`.
- `list` (array) and `value` (string) are the SPL/SQL column fields. There is no
  `topListLabel`/`topListValue`.

**`aggregation` is strict about `type`:**

```json
{ "function": "p99", "fields": [ { "field": "duration", "type": "float", "is_attribute": false } ] }
```

- `row_count` — no `fields`.
- `unique_count` — `fields` required, `type` is `"float"` or `"string"`.
- `avg`, `sum`, `max`, `min`, `p99`, `p95`, `p90`, `p75`, `p50` — `fields` required and
  `type` must be **literally `"float"`**.

Get any of that wrong — missing `fields`, `type: "string"` on a numeric aggregation, or
`function: "count"` (not a valid name) — and the whole aggregation silently resets to
`row_count`, giving you a row count where you asked for a percentile.

### Formula query

```json
{ "selectedMode": "formula", "label": "C", "expression": "A/B", "visible": true, "fieldConfig": {} }
```

`expression` must match `^[A-Z0-9+/*()-]+$` after whitespace is stripped. Consequences:

- **Uppercase only** — `a+b` fails.
- **No decimal point** — `A*1.5` fails. Use `A*3/2`.
- Labels are **single letters A–Z**; a two-character label breaks the dependency check.
- The formula must appear **after** the queries it references in the `queries` array.
- It cannot reference itself, or a label that doesn't exist.

### Filters

`filters` is `Record<string, string[]>`:

```json
{ "namespace": ["production"], "level": ["ERROR", "FATAL"] }
```

- Attribute keys are prefixed `@_@`, e.g. `"@_@user.id": ["abc"]`.
- Exclusion is a `-` prefix on the **value**: `{"namespace": ["-kube-system"]}`.
- A `$name` value is a dashboard-variable reference.

## Metrics Query Functions

`functions` is an ordered pipeline. **One malformed entry wipes the entire array**, and
argument counts are exact tuples — so build these carefully.

| type | names | arguments |
|---|---|---|
| `range` | `rate`, `increase`, `resets` | `[{arg_name:"over", arg_value:"5m"}]` — any string |
| `aggregations` | `sum`, `avg`, `max`, `min`, `count`, `No_Aggregations` | `[{arg_name:"by", arg_value:["namespace"]}]` — must be an **array** |
| `top_bottom` | `top`, `bottom` | `[{arg_name:"k",arg_value:5},{arg_name:"by",arg_value:"max"}]` — `by` ∈ `max\|min\|avg\|median\|last` |
| `rollup` | `avg_over_time`, `sum_over_time`, `max_over_time`, `min_over_time`, `count_over_time`, `last_over_time`, `absent_over_time`, `present_over_time`, `increases_over_time`, `range_over_time`, `quantile_over_time` | `[{arg_name:"over", arg_value:"5m"}]` — **restricted to `30s\|1m\|5m\|30m\|1h\|1d`** |
| `comparison` | `greater`, `lesser`, `greater_than_or_equal`, `less_than_or_equal`, `equal`, `not_equal` | `[{arg_name:"than"\|"to", arg_value:100}]` |
| `transform` | `abs`, `clamp`, `clamp_max`, `clamp_min`, `round`, `histogram_quantile`, `sort`, `sort_desc` | variable length, but the `arguments` key is **still required** — use `[]` for zero-arg |

`transform` argument names: `clamp` → `min`+`max`, `clamp_max` → `max`, `clamp_min` →
`min`, `round` → `to_nearest`, `histogram_quantile` → `quantile`; `abs`/`sort`/`sort_desc`
take none (but still need `"arguments": []`).

> [!WARNING]
> `range.over` accepts any string, but **`rollup.over` only accepts
> `30s`, `1m`, `5m`, `30m`, `1h`, `1d`**. A `rollup` with `over: "7m"` silently deletes
> every function on that query.

Typical time-series pipeline: `rate` then `aggregations`.

```json
"functions": [
  { "type": "range", "name": "rate", "arguments": [ { "arg_name": "over", "arg_value": "5m" } ] },
  { "type": "aggregations", "name": "sum", "arguments": [ { "arg_name": "by", "arg_value": ["namespace"] } ] }
]
```

## Grid Layout

```json
{ "i": "0", "x": 0, "y": 0, "w": 6, "h": 4 }
```

All five keys required. 12-column grid, `rowHeight` 100px, panel `minH` 2. No bounds are
validated — `w: 99` is accepted and renders broken.

- `x`: 0–11. Side by side: `0, 6` for two columns; `0, 4, 8` for three.
- `y`: increment by the previous row's height.
- `i`: the array index as a string. **Matching is positional**, so keep `gridLayout` in the
  same order as `panels`, and at least as long.

## Variables

```json
{
  "name": "service",
  "description": "",
  "meta": { "variableType": "custom", "options": ["api", "web"], "value": [], "selectType": "multiple" }
}
```

- `name`: required, non-empty, **max 20 chars**, must match `^[a-zA-Z_][a-zA-Z0-9_]*$`.
- `description`: **required** — use `""`. It is not optional.
- `meta`: discriminated union on `variableType`. There is no `id`, `label`, or
  `multiSelect`.
- `selectType`: `"single"` or `"multiple"`.

| variableType | required in `meta` |
|---|---|
| `textbox` | — (`defaultValue`, `value` default to `""`) |
| `custom` | `options: string[]` with ≥ 1 entry |
| `logs` / `traces` | `fieldMeta: {field, type, is_attribute}` — all three; optional `filters`, `filterMode` (`MFD`\|`ADVANCED_QUERY`) |
| `metrics` | `metric` (non-empty) **and** `fieldMeta`; **no `filterMode`** |

`fieldMeta.type` and `fieldMeta.is_attribute` have no defaults — both must be present.

> [!WARNING]
> **One invalid variable silently deletes every variable** with no import error. Double-check
> `description: ""` is present and the name matches the regex.

## Sub-Grids (Rows)

```json
"subGrids": [ { "id": "row-1", "title": "Payments", "collapsed": false, "panels": [], "gridLayout": [] } ],
"subGridLayout": [ { "i": "sg-row-1", "x": 0, "y": 0, "w": 12, "h": 1 } ]
```

`id` and `title` are required on a sub-grid. In `subGridLayout`, `i` **must** be
`` `sg-${id}` `` — and only `y` is honoured; `x`, `w`, `h` are forced to `0`, `12`, and a
computed value. Row order comes from `y`.

A sub-grid's inner `gridLayout` is optional-chained with fallbacks, so it may be shorter
than its `panels` — unlike the top-level one.

## Delivering It

### Creating it directly

```
validate-dashboard-json  →  valid=true  →  create-dashboard
```

`create-dashboard` takes `name`, `preset` (the object, or a JSON string containing it) and
an optional `description`. It returns the dashboard id and its UI path — quote that path so
the user can open it.

It is a **write tool**: only call it when the user has clearly asked for a dashboard to be
created, and say what you are about to create before calling. If it refuses, the response
names the JSON Pointer for every problem; fix them and retry rather than falling back to
handing over JSON.

### Handing over JSON to import

1. Copy the JSON to a `.json` file (the import UI requires `application/json`).
2. KubeSense → **Dashboards → Import**.
3. Upload and review, then save.

On this path never claim the dashboard was created — the user imports and confirms it.

## Rules

1. Validate with `validate-dashboard-json` before creating or handing over. Everything
   below is a rule this check enforces for you.
2. `preset` **must** be a stringified JSON string in the import envelope — but the plain
   object when passed to `create-dashboard` or `validate-dashboard-json`.
3. `gridLayout` must be at least as long as `panels`, in the same order — matching is
   positional and a short layout crashes at render.
4. Every logs/traces query needs `columnFields`, even if `[]`.
5. Panel `name` and top-level `name` must be non-empty.
6. Numeric aggregations need `fields[].type: "float"` exactly, or they silently become
   `row_count`.
7. `chart_type` is lowercase `timeseries`; `panelType` is camelCase `timeSeries`.
8. Formula expressions: uppercase, no decimals, single-letter labels, placed **after** the
   queries they reference.
9. `rollup.over` only accepts `30s`/`1m`/`5m`/`30m`/`1h`/`1d`; a bad value wipes all
   `functions`.
10. Variables need `description` (use `""`) and a regex-valid `name` ≤ 20 chars — one bad
    variable deletes them all.
11. Prefer omitting optional fields to guessing them: an omitted field takes its default, a
    wrong one can reset its siblings.
12. Don't emit `enableThresholds`, `colorPalette`, `mergeTables: false`, `topListLabel`, or
    `topListValue` — none exist in the current schema.
13. Use real y-axis units (`percentage`, `mCPU`, `bytes/sec`) — `percent`, `short`, `none`
    silently become `auto`.
14. Discover metric/field names with MCP before writing queries; tell the user to verify on
    the panel preview.
