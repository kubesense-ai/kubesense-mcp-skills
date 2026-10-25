# Variables and Sub-Grids (Rows)

Read this when the dashboard needs **template variables** (a dropdown the user picks from
that feeds into query filters) or **rows** (collapsible groups of panels). Neither is
required — omit `variables`, `subGrids`, and `subGridLayout` entirely and they default to
`[]`.

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
| `logs` / `traces` | `fieldMeta: {field, type, is_attribute}` — all three; optional `filters`, `filterMode` (`MFD`\|`ADVANCED_QUERY`). With `ADVANCED_QUERY`, the WHERE clause goes in `filters.advanced_query: ["<where>"]` |
| `metrics` | `metric` (non-empty) **and** `fieldMeta`; **no `filterMode`** |

`fieldMeta.type` and `fieldMeta.is_attribute` have no defaults — both must be present.

> [!WARNING]
> **One invalid variable silently deletes every variable** with no import error — the
> `variables` array carries a `.catch([])`. Double-check `description: ""` is present and
> the name matches the regex.

### Referencing a variable

A variable is referenced as `$name` in a query `filters` value:

```json
{ "namespace": ["$service"] }
```

### Field references (`$$name`)

`$$name` stands for the whole condition: the variable's `fieldMeta.field` as the key, its
selection as the values. Prefer it whenever the filter key is the same field the variable
lists — it cannot drift from the variable's field.

```json
{ "$$namespace": ["$$namespace"], "phase": ["Running"] }
```

With variable `namespace` (`fieldMeta.field: "namespace"`) and `kubesense` selected, that
renders `{namespace="kubesense", phase="Running"}`.

- The **key** makes it a field reference; write `["$$name"]` as the value, as the UI does.
  `{"namespace": ["$$namespace"]}` is not one — there the value is read as a literal `$`
  followed by `$namespace`.
- Only `logs`, `traces` and `metrics` variables have a field. A `$$name` naming a `textbox`
  or `custom` variable, or no variable at all, is silently dropped from the query.
- An attribute field (`is_attribute: true`) expands to the `@_@` key for you.
- Nothing selected → the condition is dropped, not matched against an empty set.
- It also works inside `filters.advanced_query` (`"status = error AND $$namespace"` runs as
  `status = error AND namespace IN (…)`) and inside a code-mode PromQL selector
  (`kube_pod_status_phase{$$namespace, phase="Running"}`). Outside `{…}` in PromQL it is not
  expanded.
- Not expanded in SQL or SPL panels.

A metrics query's own `variables` key is **auto-derived** from its filters and promql — do
not set it by hand, anything you supply is overwritten.

### Examples

A `custom` list the user types out:

```json
{
  "name": "env",
  "description": "",
  "meta": { "variableType": "custom", "options": ["prod", "staging"], "value": ["prod"], "selectType": "single" }
}
```

A `logs` variable populated from a real field's values:

```json
{
  "name": "namespace",
  "description": "",
  "meta": {
    "variableType": "logs",
    "fieldMeta": { "field": "namespace", "type": "string", "is_attribute": false },
    "selectType": "multiple"
  }
}
```

A `metrics` variable populated from a label on a metric — note it needs both `metric` and
`fieldMeta`, and must **not** carry `filterMode`:

```json
{
  "name": "pod",
  "description": "",
  "meta": {
    "variableType": "metrics",
    "metric": "container_cpu_usage_seconds_total",
    "fieldMeta": { "field": "pod", "type": "string", "is_attribute": false },
    "selectType": "single"
  }
}
```

## Sub-Grids (Rows)

```json
"subGrids": [ { "id": "row-1", "title": "Payments", "collapsed": false, "panels": [], "gridLayout": [] } ],
"subGridLayout": [ { "i": "sg-row-1", "x": 0, "y": 0, "w": 12, "h": 1 } ]
```

`id` and `title` are required on a sub-grid. In `subGridLayout`, `i` **must** be
`` `sg-${id}` `` — and only `y` is honoured; `x`, `w`, `h` are forced to `0`, `12`, and a
computed value. Row order comes from `y`.

A sub-grid's inner `gridLayout` is optional-chained with fallbacks, so it may be shorter
than its `panels` — unlike the top-level one, which crashes at render if it is short.

Panels inside a sub-grid use the same panel shape as top-level panels, and the sub-grid's
own `gridLayout` uses the same `{i,x,y,w,h}` shape on the same 12-column grid.

> [!WARNING]
> A bad `subGrids` entry drops **all** sub-grids; a bad entry inside one sub-grid's
> `panels` empties **that row's** panels. Both are silent.
