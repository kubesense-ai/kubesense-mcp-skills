# Log & Trace Field Catalog

The complete, exact field catalog the KubeSense MCP server accepts. Source of truth:
`kubeapi/observability/fieldcatalog/{logs,traces}.go`.

> [!NOTE]
> This page covers logs and traces. RUM has six event types with their own catalogs,
> generated from `kubeapi/observability/fieldcatalog/rum.go`:
> [kubesense-rum/references/field-catalog.md](../../kubesense-rum/references/field-catalog.md).

**Type the "Label" column.** The "Storage column" is what the backend uses internally; it
is **rejected** at every input slot with a message naming the correct label.

Input slots this applies to: `query`, `required_fields`, `group_by_fields`, `fields`,
`sort_by`.

---

## Logs — 17 fields

| Label (type this) | Storage column | Type | Enum values | Notes |
|---|---|---|---|---|
| `type` | `level` | string | `ERROR` `WARN` `INFO` `DEBUG` `TRACE` `FATAL` `PANIC` | **UPPERCASE** |
| `instance` | `pod_name` | string | | pod |
| `container` | `container_name` | string | | |
| `node` | `host` | string | | **not `node_name`** |
| `workload` | `workload` | string | | Kubernetes workload |
| `service` | `service` | string | | application name; same label as on traces |
| `namespace` | `namespace` | string | | |
| `domain` | `cluster` | string | | say "domain" to users |
| `body` | `body` | string | | message text; group by `pattern`, not `body`, for "top errors" |
| `format` | `format` | string | `json` `klog` `nginx` | lowercase |
| `source` | `source` | string | | |
| `region` | `region` | string | | |
| `app_version` | `app_version` | string | | |
| `env_type` | `env_type` | string | | |
| `timestamp` | `timestamp` | string | | hidden from discovery, still accepted |
| `pattern` | derived from `body` | string | | hidden, **group-by only**: the body with timestamps, IDs and numbers masked. Needs a `query`. Rejected in any `query` (search-logs, analyze, create-alert) and in `search-logs` `required_fields`; allowed only in `group_by_fields` of analyze-logs / analyze-telemetry, or as an `execute-sql` column |
| `body_length` | `body_length` | **float** | | hidden; the only numeric log field |

**14 advertised by discovery** (sorted): `app_version`, `body`, `container`, `domain`,
`env_type`, `format`, `instance`, `namespace`, `node`, `region`, `service`, `source`,
`type`, `workload`.

**Hidden but accepted**: `timestamp`, `pattern` (group-by only), `body_length`. Discovery filters them
out, validation does not — a documented asymmetry you can rely on.

**The four renames**: `type`→`level`, `instance`→`pod_name`, `container`→`container_name`,
`node`→`host`. Everything else is identity.

---

## Traces — 35 fields

| Label (type this) | Storage column | Type | Enum values | Notes |
|---|---|---|---|---|
| `service` | `app_service` | string | | **preferred app identity** |
| `workload` | `workload` | string | | K8s topology only |
| `instance` | `pod_name` | string | | pod |
| `container` | `container_name` | string | | |
| `node_name` | `node_name` | string | | **not `node`** |
| `namespace` | `namespace` | string | | |
| `cluster` | `cluster` | string | | |
| `status` | `status` | string | `error` `ok` | **lowercase** |
| `status_code` | `return_code` | **string** | `200` `400` `401` `403` `404` `500` `502` `503` `504` | string — no range comparisons |
| `method` | `subtype` | string | `GET` `POST` `PUT` `DELETE` `PATCH` | HTTP method |
| `resource` | `clustered_resource` | string | | endpoint |
| `role` | `kind` | string | `server` `client` | span role |
| `protocol` | `protocol_type` | string | `HTTP` `gRPC` `TCP` `MongoDB` `Redis` `MySQL` `PostgreSQL` | |
| `source` | `source` | string | `eBPF` `OTel` | |
| `request_type` | `is_external` | **bool** | | no grouping |
| `duration_ms` | `duration` | **float** | | **milliseconds** in `query`, operands, results and rows. Bare `duration` is the legacy nanosecond field. Not for alerts: `create-alert` rejects it as an operand or group-by (use `duration`, nanoseconds); only an alert's `query` takes it |
| `trace_id` | `trace_id` | string | | no grouping; sets free-search |
| `span_id` | `span_id` | string | | no grouping; sets free-search |
| `issue_id` | `issue_id` | string | | no grouping; join key to `trace_issues` |
| `reason` | `issue_reason` | string | | sets free-search |
| `operation_name` | `operation_name` | string | | |
| `server` | `server` | string | | |
| `client` | `client` | string | | |
| `server_namespace` | `server_namespace` | string | | |
| `client_namespace` | `client_namespace` | string | | |
| `partner_cluster` | `partner_cluster` | string | | |
| `region` | `region` | string | | |
| `app_version` | `app_version` | string | | |
| `env_type` | `env_type` | string | | |
| `domain` | `customer_identifier` | string | | tenant / customer |
| `timestamp` | `start_timestamp` | string | | hidden; accepted |
| `primary_namespace` | `perspective_namespace` | string | | hidden; accepted |
| `primary_workload` | `perspective_workload` | string | | hidden; accepted |
| `associate_namespace` | `partner_namespace` | string | | hidden; accepted |
| `associate_workload` | `partner_workload` | string | | hidden; accepted |

**29 advertised by discovery** (sorted): `app_version`, `client`, `client_namespace`,
`cluster`, `container`, `domain`, `env_type`, `instance`, `issue_id`, `method`,
`namespace`, `node_name`, `operation_name`, `partner_cluster`, `protocol`, `reason`,
`region`, `request_type`, `resource`, `role`, `server`, `server_namespace`, `service`,
`source`, `span_id`, `status`, `status_code`, `trace_id`, `workload`.

**Hidden but accepted**: `timestamp`, `primary_*`, `associate_*`.

**The renames**: `service`→`app_service`, `instance`→`pod_name`,
`container`→`container_name`, `method`→`subtype`, `status_code`→`return_code`,
`resource`→`clustered_resource`, `role`→`kind`, `protocol`→`protocol_type`,
`request_type`→`is_external`, `domain`→`customer_identifier`, `reason`→`issue_reason`,
`timestamp`→`start_timestamp`, `primary_*`→`perspective_*`, `associate_*`→`partner_*`.

---

## Cross-Signal Comparison

The traps, side by side:

| Concept | Logs | Traces | Same? |
|---|---|---|---|
| severity / outcome | `type` = `ERROR` | `status` = `error` | **No — name and casing** |
| node | `node` (→ `host`) | `node_name` | **No — label and column** |
| service identity | `service` | `service` | Yes |
| message text | `body` | *does not exist* | **Logs only** |
| latency | *does not exist* | `duration_ms` | **Traces only** |
| pod | `instance` | `instance` | Yes |
| container | `container` | `container` | Yes |
| namespace / workload / cluster | same | same | Yes |
| region / app_version / env_type | same | same | Yes |
| timestamp | `timestamp` (→ `timestamp`) | `timestamp` (→ `start_timestamp`) | Label yes, column no |
| source | `source`, no enums | `source` = `eBPF`/`OTel` | Label yes, enums traces-only |

Confirmed failures from carrying names across signals:

```
cluster = prod       on logs    → "cluster" is a storage column; use the catalog label "domain"
node = node-1        on traces  → unknown field "node" for signal=traces
pod = my-pod         on either  → unknown field "pod"      (it is "instance")
observation_point = x on traces → unknown field "observation_point"
```

`observation_point` is worth calling out: the `search-traces` tool description suggests
pinning it for exhaustive pagination, but it is not in the catalog and is rejected.

---

## Error Messages

**Storage name supplied:**

```
field "pod_name" is a storage column; use the catalog label "instance" instead
  (call get-fields with signal=logs to see all labels)
```

Act on the suggestion — do not retry the same name.

**Unknown field:**

```
unknown field "svc" for signal=logs; call get-fields with signal=logs to
  discover valid fields (attributes carry an @ prefix)
```

Errors are prefixed by the slot that failed: `query: …` (a KQL error carries its code and position, `query: unknown_field: unknown field svc for logs (at 0-3)`),
`required_fields[0]: …`, `group_by_fields[0]: …`, `fields[0]: …`, `sort_by: …`.

---

## Attributes

Dynamic attributes are **not in the catalog** — they are discovered per-window by scanning
storage, so they differ between deployments and windows. Neither signal's catalog contains
a single attribute entry.

| Where | Syntax | Works? |
|---|---|---|
| `query`, logs | `@user.id:abc-123` | ✅ |
| `query`, traces | `@db.system:postgresql` | ✅ |
| `group_by_fields` / `fields` / `required_fields` / `sort_by`, both signals | `{"field": "db.system", "is_attribute": true}` | ✅ |

Discovery reports the key **bare** in the `field` column with `is_attribute=true`; the `@`
appears only in the `example` cell.

**Attribute forms** (both signals): `@k:value`, `@k:(a OR b)`, `@k:val*`, `@k:~val*`,
`@k>n`, `@k>=n`, `@k<n`, `@k<=n`, `-@k:value`, `@k:*` (the attribute is set). A key that holds
numbers, text or both takes every operator: `@latency>200` reads a number or text such as
`"250"`, and `@latency:*20*` matches the number 20 as text. A value that is not a number
matches neither a comparison nor its negation. On logs and events, `-@k:v` and negated
patterns and comparisons need the key to exist.

Trace attributes are stored as parallel `attribute_names[]`/`attribute_values[]` arrays and
are string-typed; the server maps the forms above onto them. Group-by is unaffected.

There is an existence check: `@field:*`. Its negation is `-@field:*`.

---

## Free-Search Routing

Touching any of these fields routes the query to the **raw table** instead of the
pre-aggregated rollups — slower, but the only way to see message text or per-span detail:

- logs: `body`, `trace_id`, `span_id`, any attribute
- traces: `duration_ms`, `trace_id`, `span_id`, `reason`, any attribute

It is computed automatically and reported as `is_free_search` in the output header.
Column-only filters stay on the fast rollup path. This is also why `duration_ms` filters make
a trace query noticeably slower.

---

## Forms Advertised vs Accepted

`get-fields` lists the KQL **forms** each field takes in its `forms` column (a token that
points at a `# forms.<token>=...` legend line, with `<f>` for the field name). Those are
the forms the compiler accepts for that field, no more and no fewer, so a form that is not
listed is an error with the field and the position: for example a range on a text field, or
a wildcard on a RUM field that cannot take one.

Rules the grammar adds:

- Quote a value that has a space or a colon: `resource:"/api/v1"`, `@msg:"a b"`.
- Negate a list with `-field:(a OR b)`; there is no `NOT IN`.
- `duration_ms` takes numbers in milliseconds (`duration_ms>250`, decimals allowed); every
  other trace column is text or an enum.
- `body` on logs is a word match: `body:timeout`; `body:*timeout*` is a substring. Both
  ignore case.
- `AND` binds tighter than `OR`, and a space is `AND`: `type:ERROR OR namespace:a service:b`
  reads as `type:ERROR OR (namespace:a AND service:b)`. Add parentheses when you mean otherwise.
