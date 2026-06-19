# KubeSense Filtering Reference

How to express filters on logs, traces, and metrics across every KubeSense
surface. Each surface (MCP tools, dashboard presets, alert rules) takes a
**different concrete shape**, but they all compile down to the same backend
model. Read the section for the surface you are generating.

> [!IMPORTANT]
> **Always discover field names first.** Never guess fields used for filtering.
> With the KubeSense MCP server available, use `get-trace-or-log-fields` (logs/
> traces) and `get-metric-labels` (metrics). Use the discovered names verbatim
> and note whether each is an **attribute** (see [Attributes](#attributes-is_attribute--type-attribute)).

## Pick your surface

| You are generating…                       | Filter format                                  | Section |
| ----------------------------------------- | ---------------------------------------------- | ------- |
| MCP tool calls (`analyze-*`, `search-*`)  | SQL-like **WHERE-clause string**               | [§1](#1-mcp-tools--where-clause-string) |
| Dashboard preset JSON                      | **`Record<string, string[]>`** map + `filterMode` | [§2](#2-dashboard-presets--filters-map--filtermode) |
| Alert rule JSON                            | `raw_filters` + `filters` maps                 | [§3](#3-alert-rules--raw_filters--filters) |

All three are translations of the backend [`UnifiedFilter`](#the-backend-model-unifiedfilter)
model. Understanding that model explains why MFD is equality/membership-based and
why latency thresholds need the advanced form.

---

## 1. MCP tools — WHERE-clause string

The `analyze-logs`, `analyze-traces`, `search-logs`, and `search-traces` tools
take a single `filters` **string**: a SQL-like WHERE clause.

```json
{ "filters": "level = 'ERROR' AND namespace = 'production'" }
```

> [!IMPORTANT]
> **The MCP tools have no `filterMode`.** The `filters` string *is* the
> [ADVANCED](#advanced_query-mode-filtermode-advanced_query) form — and ADVANCED
> is a strict **superset** of [MFD](#mfd-mode-filtermode-mfd). There is nothing
> MFD can express that this string cannot, so on MCP you never need the MFD
> value-map; just write the clause. (MFD only exists because dashboard/alert
> presets persist filters for later editing in the dropdown UI — see §2/§3.)
>
> If you are thinking in MFD terms, translate to the string directly:
>
> | MFD value-map intent              | WHERE-string equivalent          |
> | --------------------------------- | -------------------------------- |
> | `{ "severity": ["ERROR"] }`       | `severity = 'ERROR'`             |
> | `{ "namespace": ["a", "b"] }`     | `namespace IN ('a', 'b')`        |
> | `{ "service_name": ["-proxy"] }`  | `service_name != 'proxy'`        |
> | `{ "@_@http_status": [">300"] }`  | `@http_status > 300`             |
> | latency threshold                 | `duration_ms > 500`              |

### Operators

| Operator              | Example                                   | Notes |
| --------------------- | ----------------------------------------- | ----- |
| `=` `!=`              | `level = 'ERROR'`, `status != 'ok'`       | Equality. Strings single-quoted. |
| `>` `<` `>=` `<=`     | `duration_ms > 500`                       | Numeric. Numbers **unquoted**. |
| `IN`                  | `namespace IN ('default', 'kube-system')` | Membership. Parenthesised, comma-separated. |
| `LIKE` / `ILIKE`      | `body ILIKE '%timeout%'`                  | Pattern match (`ILIKE` = case-insensitive). |
| `SUBSTR_ILIKE`        | `body SUBSTR_ILIKE 'timeout'`             | Substring, case-insensitive. |
| `AND` / `OR`          | `a = 1 AND b = 2`                          | Combine conditions. |
| `NOT ( … )`           | `NOT ( namespace IN ('kube-system') )`    | Negation wraps a group. `NOT IN` must be written this way. |
| `exist(@attr)`        | `exist(@http.url)`                         | Attribute presence. |

### Values

- **Strings** — single-quoted: `level = 'ERROR'`.
- **Numbers** — unquoted: `duration_ms > 500`.
- **Attributes** — prefix the field with `@`: `@http_status > 300`. See
  [Attributes](#attributes-is_attribute--type-attribute).

### Latency (traces)

Filter latency with **`duration_ms`** (milliseconds), never the raw `duration`
field (nanoseconds, meant for aggregation). `duration_ms` is **not** returned by
`get-trace-or-log-fields` — use it verbatim:

```
duration_ms > 500     # spans slower than 500ms
duration_ms >= 1000   # slower than 1s
```

### Metrics

Metrics have no WHERE clause — filter via **PromQL label matchers** inside the
query string: `metric{label="value"}` (exact) or `metric{label=~"regex.*"}`
(regex). Discover labels with `get-metric-labels` first.

---

## 2. Dashboard presets — `filters` map + `filterMode`

Dashboard panel and variable queries store filters as the webapp UI shape: a
**flat map** of field → array of value tokens, paired with a `filterMode`.

```json
{
  "filters": { "namespace": ["default", "kube-system"], "severity": ["ERROR"] },
  "filterMode": "MFD"
}
```

- `filters` — `Record<string, string[]>`. Keys are field names; values are
  string tokens. **`{}` is valid** (no filtering). Default `filterMode` is `MFD`.
- An empty map plus `"filterMode": "MFD"` is the no-filter default — only
  populate when the user specifies filters.

### MFD mode (`"filterMode": "MFD"`)

Equality- and membership-based. The **operator is encoded as a prefix on the
value token** — there is no separate operator field:

| Token form     | Meaning            | Example                                |
| -------------- | ------------------ | -------------------------------------- |
| `"value"`      | include (equals/in) | `{ "severity": ["ERROR"] }`           |
| `"-value"`     | exclude (not in)   | `{ "service_name": ["-internal-proxy"] }` |
| `">value"`     | greater than       | `{ "http_status": [">300"] }`          |
| `"<value"`     | less than          | `{ "http_status": ["<500"] }`          |
| `">=value"`    | greater or equal   | `{ "duration_ms": [">=1000"] }`        |
| `"<=value"`    | less or equal      | `{ "duration_ms": ["<=500"] }`         |

Multiple values under one key are OR'd (membership): `{ "namespace":
["default", "kube-system"] }` matches either. Multiple keys are AND'd.

**Attributes** in MFD: prefix the **key** with `@_@`, e.g.
`{ "@_@http_status": [">300"] }`. See [Attributes](#attributes-is_attribute--type-attribute).

> [!NOTE]
> MFD is fundamentally equality/membership. The `>`/`<` prefixes work for
> numeric fields, but for anything beyond simple comparisons (mixed AND/OR,
> negated groups, latency thresholds combined with other conditions), use
> ADVANCED_QUERY instead.

### ADVANCED_QUERY mode (`"filterMode": "ADVANCED_QUERY"`)

The full WHERE-clause string (same syntax as [§1](#1-mcp-tools--where-clause-string))
stored under the single reserved key `advanced_query`:

```json
{
  "filters": { "advanced_query": ["severity = 'ERROR' AND duration_ms > 500"] },
  "filterMode": "ADVANCED_QUERY"
}
```

Use this whenever a filter cannot be expressed as plain equality/membership —
e.g. latency thresholds, `OR` across fields, or `NOT ( … )` groups.

### Latency in dashboards

Same rule as everywhere: filter on **`duration_ms`** (ms), never the ns
`duration`. Because MFD numeric prefixes are limited, the cleanest way to
express a latency threshold is ADVANCED_QUERY with `duration_ms > 500`. Use
`duration` (ns) only in `aggregation`/`groupBy`, with
`config.yAxisLabelFormatter: "nanoseconds"`.

### Dashboard variables

Logs/traces variables carry the **same** `filters` map + `filterMode` (only
`MFD` / `ADVANCED_QUERY`), plus a `fieldMeta: { field, type, is_attribute }`.
Metrics variables have **no** `filters`/`filterMode`. A variable's selected
value is referenced inside another query's filters as a `$variableName` token.

---

## 3. Alert rules — `raw_filters` + `filters`

Alert rule queries over logs/traces provide filters as **two parallel maps**,
both `{ field: [values] }`, and you must supply **both** with the same content:

```json
{
  "selectedMode": "logs",
  "raw_filters": { "level": ["ERROR"] },
  "filters": { "level": ["ERROR"] }
}
```

- `raw_filters` — the raw user selection.
- `filters` — the resolved/applied filter.
- Keep them identical unless the alert skill says otherwise.
- Logs use field names like `level` / `pod_name` / `container_name`; traces use
  `status` / `pod` / `container`. Discover exact names with
  `get-trace-or-log-fields`.

This is the same equality/membership map as dashboard MFD — values are matched
by membership (multiple values under a key are OR'd).

---

## Attributes (`is_attribute` / `type: "attribute"`)

Fields fall into two classes:

- **Columns** — first-class indexed fields (`namespace`, `level`, `status`,
  `duration_ms`, …).
- **Attributes** — dynamic key/value pairs stored in attribute maps (log
  `string_attributes`/`float_attributes`; trace `attribute_names`/
  `attribute_values`). They must be flagged so the backend looks them up in the
  attribute maps instead of expecting a column.

How "attribute" is signalled per surface:

| Surface          | How to mark an attribute                                        |
| ---------------- | -------------------------------------------------------------- |
| MCP WHERE string | prefix the field with `@` — `@http_status > 300`               |
| Dashboard MFD    | prefix the **key** with `@_@` — `{ "@_@http_status": [">300"] }` |
| Dashboard ADV    | prefix the field with `@` inside the query string              |
| Field descriptors (`sortBy`, `groupBy`, `fieldMeta`, columns) | set `"is_attribute": true` and `type` (`"string"`/`"float"`) |

`get-trace-or-log-fields` reports whether a field is an attribute — honour it.
When unsure and the field is a standard column, `is_attribute: false`.

---

## The backend model (`UnifiedFilter`)

All three surfaces compile to one backend shape. You will not author this
directly, but it explains the rules above:

```json
{
  "type": "common | advanced",
  "common_filter": [ { "field": "...", "operation": "IN", "values": ["..."], "type": "..." } ],
  "adv_filters": { "operation": "AND", "children": [ /* recursive */ ] }
}
```

- **`type: "common"`** ← MFD. `common_filter` is a flat list of conditions, each
  `{ field, operation, values, type }`. `operation` is one of `IN`, `NIN`, `EQ`,
  `NEQ`, `LT`, `GT`, `LTE`, `GTE`, `LIKE`, `ILIKE`, `SUBSTR_ILIKE`, `HAS`, …
  Conditions are AND'd; `values` within a condition are OR'd (membership). This
  is why MFD is equality/membership-based.
- **`type: "advanced"`** ← ADVANCED_QUERY / WHERE string. `adv_filters` is a
  recursive tree of `AND` / `OR` / `NOT` group nodes and leaf condition nodes —
  which is why arbitrary boolean logic and comparisons are only fully expressible
  in the advanced form.
- A condition's `type: "attribute"` routes it to the attribute-map lookup —
  the backend equivalent of the `@` / `@_@` prefixes above.
- Trace `duration_ms` values are scaled to nanoseconds on the backend, so you
  always write the threshold in **milliseconds**.

---

## Quick reference

- Discover fields first (`get-trace-or-log-fields`, `get-metric-labels`).
- **MCP** → WHERE string: `"level = 'ERROR' AND duration_ms > 500"`.
- **Dashboard** → map + `filterMode`. Simple equality/membership → `MFD`
  (`{ "level": ["ERROR"] }`); anything richer → `ADVANCED_QUERY`
  (`{ "advanced_query": ["..."] }`).
- **Alerts** → both `raw_filters` and `filters` as `{ field: [values] }`.
- **Latency** → always `duration_ms` (ms), never `duration` (ns).
- **Attributes** → `@field` (WHERE / ADV), `@_@key` (MFD), `is_attribute: true`
  (field descriptors).
- MFD = equality/membership; ADVANCED = full boolean + comparisons.
