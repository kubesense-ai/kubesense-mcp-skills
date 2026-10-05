# Host map panels

A host map draws every host as a tile, with its pods and containers nested inside, each
coloured (and optionally sized) by a signal. It answers "where is the problem" at a
glance: which hosts are hot, which pods on them are not ready, which containers are
restarting.

The panel holds **no PromQL**. Its one query names what to draw, and the server compiles
that to PromQL for both Kubernetes and legacy (Docker / VM) hosts.

## The panel

```json
{
  "name": "Pod readiness by host",
  "panelType": "hostMap",
  "queries": [{
    "selectedMode": "infrastructure",
    "label": "A",
    "levels": [
      { "entity": "host", "fill": "cpu_utilization" },
      { "entity": "pod",  "fill": "ready", "size": "memory_usage" }
    ],
    "groupByDimensions": ["cluster"],
    "filterMode": "ADVANCED_QUERY",
    "filters": { "advanced_query": ["namespace = payments AND NOT (workload IN (canary))"] }
  }],
  "config": {
    "hostMapColors": {
      "host": { "palette": "solid-red-green", "scale": "linear", "min": 0, "max": 100, "reverse": true },
      "pod":  { "palette": "solid-red-green", "scale": "linear", "min": 0, "max": 1,   "reverse": false }
    }
  }
}
```

Exactly **one** query, and it must be `infrastructure`. An infrastructure query in any other
panel type is refused, because nothing else can draw it.

## `levels`

1 to 3 levels, **outermost first**, in the fixed order **host > pod > container**.

- A level may be skipped: `host > container` is how legacy hosts, which have no pods, are
  drawn. `pod` alone or `pod > container` is fine too.
- A level may never repeat or go back up: `pod > host` is refused.
- Only the **last** level may set `size`. An outer tile is as big as what it holds.

Each level has a `fill` (required, colours the tile) and an optional `size`. Both take a
signal the entity has:

| Entity | Signals |
|---|---|
| `host` | `cpu_utilization`, `memory_utilization`, `cpu_usage`, `memory_usage`, `pod_count`, `ready` |
| `pod` | `cpu_utilization`, `memory_utilization`, `cpu_usage`, `memory_usage`, `restarts`, `ready` |
| `container` | `cpu_utilization`, `memory_utilization`, `cpu_usage`, `memory_usage`, `restarts`, `ready` |

Units: the utilizations are percent of the limit (0-100; a pod or container with no limit
has none), `cpu_usage` is cores, `memory_usage` is bytes, `ready` is 0 or 1, `restarts`
counts restarts over the panel's time range, and `pod_count` counts the pods on a host.

`pod_count` and `restarts` come from Kubernetes only, so legacy hosts show them as no data.

## `groupByDimensions`

Splits the map into one section per value. What it can name depends on the **first**
level, because only the dimensions that level's rows carry can split it:

| First level | May group by |
|---|---|
| `host` | `cluster`, `env_type` |
| `pod` | `cluster`, `env_type`, `host`, `namespace`, `workload` |
| `container` | `cluster`, `env_type`, `host`, `namespace`, `workload`, `pod` |

A level cannot be grouped by its own name (a host map by `host` would draw one tile per
section), and each dimension appears once. `env_type` is `k8s` or `legacy`. Omit it, or
pass `[]`, for one section.

## Filters

A host map filters by **`cluster`, `host`, `namespace`, `workload` and `pod`**. Never
`container`: no metric that places a container also names its host, so it could not narrow
the levels around it.

**Basic** (`"filterMode": "MFD"`, the default) holds a list of values per field. A value
prefixed with `-` is excluded:

```json
"filterMode": "MFD",
"filters": { "cluster": ["prod"], "namespace": ["payments", "-payments-canary"] }
```

**Advanced** (`"filterMode": "ADVANCED_QUERY"`) holds one WHERE-style expression in
`filters.advanced_query`, the same place logs queries keep theirs:

```json
"filterMode": "ADVANCED_QUERY",
"filters": { "advanced_query": ["namespace = payments AND (cluster = prod OR cluster = staging)"] }
```

- Operators: `=`, `!=`, `IN`, joined with `AND`, `OR`, `NOT` and parentheses.
- **`namespace NOT IN (a, b)` is not understood.** Write `NOT (namespace IN (a, b))`.
- No `LIKE`, `>`, `<` or regexes; the filter compiles to exact PromQL label matches.
- Expanded, the expression may have at most 16 OR-alternatives:
  `(a OR b) AND (c OR d) AND (e OR f)` is 8.
- Values may be dashboard variables (`namespace = $namespace`).

Only the active mode's filter applies. `validate-dashboard-json`, `create-dashboard` and
`update-dashboard` parse the Advanced expression and refuse one that will not run (rule
`infrastructure_filter`), naming the JSON Pointer of the expression.

Get real names from `list-clusters`, `list-nodes`, `list-workloads` and `list-pods` before
filtering on them: a filter on a name that does not exist validates and
draws an empty map.

## Colours: `config.hostMapColors`

Optional, keyed by entity. Each is a table column's colour range plus `reverse`. **Write
all five fields**: a field left out of an entry takes the table column's default (`green`,
`logarithmic`), not the host map's.

| Field | Values |
|---|---|
| `palette` | the column range palettes: `green`, `orange`, `red`, `blue`, `red-green`, `red-blue`, `solid-green`, `solid-orange`, `solid-red`, `solid-blue`, `solid-red-green`, `solid-red-blue` |
| `scale` | `linear` \| `logarithmic` |
| `min`, `max` | number, or `null` for the data's own bound |
| `reverse` | `true` flips the palette's direction |

A level with **no entry** gets a neutral ramp (`blue`, `linear`, both bounds `null`) over
its data's range, which is right for an
amount that is neither good nor bad. For a signal with a good and a bad end, set fixed
bounds and pick the direction:

| Signal | Suggested colour |
|---|---|
| utilizations | `solid-red-green`, `min` 0, `max` 100, `reverse: true` (green when low) |
| `ready` | `solid-red-green`, `min` 0, `max` 1 (red when not ready) |
| `restarts` | `solid-red-green`, `logarithmic`, `min` 0, `max` null, `reverse: true` |

An unknown palette is repaired to `green` when the dashboard opens; the save itself is
refused, so check with `validate-dashboard-json`.

## `config.visualFormattingRules`

The top list's value rules work here too, and colour the **outermost level** only, by its
fill value. Once any rule exists, an outermost tile matching none turns neutral; inner
levels keep their palette. Shape and styles are in
[panel-config.md](./panel-config.md#visualformattingrules).

## Who can see it

The panel reads infrastructure metrics, so a viewer needs the **infrastructure** module.
Rows are also cut to the viewer's infrastructure role scope (cluster, namespace, workload):
a namespace-scoped viewer sees the hosts of their cluster but only their own namespace's
pods.
