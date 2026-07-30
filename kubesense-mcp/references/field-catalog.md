# Log & Trace Field Catalog

The complete, exact field catalog the KubeSense MCP server accepts. Source of truth:
`kubeapi/observability/fieldcatalog/{logs,traces}.go`.

**Type the "Label" column.** The "Storage column" is what the backend uses internally; it
is **rejected** at every input slot with a message naming the correct label.

Input slots this applies to: `where`, `required_fields`, `group_by_fields`, `fields`,
`sort_by`.

---

## Logs — 16 fields

| Label (type this) | Storage column | Type | Enum values | Notes |
|---|---|---|---|---|
| `type` | `level` | string | `ERROR` `WARN` `INFO` `DEBUG` `TRACE` `FATAL` `PANIC` | **UPPERCASE** |
| `instance` | `pod_name` | string | | pod |
| `container` | `container_name` | string | | |
| `node` | `host` | string | | **not `node_name`** |
| `workload` | `workload` | string | | app name — logs have no `service` |
| `namespace` | `namespace` | string | | |
| `cluster` | `cluster` | string | | |
| `body` | `body` | string | | message text — **cannot be a group-by** |
| `format` | `format` | string | `json` `klog` `nginx` | lowercase |
| `source` | `source` | string | | |
| `region` | `region` | string | | |
| `app_version` | `app_version` | string | | |
| `env_type` | `env_type` | string | | |
| `timestamp` | `timestamp` | string | | hidden from discovery, still accepted |
| `pattern_id` | `pattern_id` | string | | hidden; group by this to cluster similar messages |
| `body_length` | `body_length` | **float** | | hidden; the only numeric log field |

**13 advertised by discovery** (sorted): `app_version`, `body`, `cluster`, `container`,
`env_type`, `format`, `instance`, `namespace`, `node`, `region`, `source`, `type`,
`workload`.

**Hidden but accepted**: `timestamp`, `pattern_id`, `body_length`. Discovery filters them
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
| `duration` | `duration` | **float** | | hidden from discovery, accepted. **ms in, ns out** |
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

**Hidden but accepted**: `timestamp`, `duration`, `primary_*`, `associate_*`.

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
| service identity | *does not exist* | `service` | **Traces only** |
| message text | `body` | *does not exist* | **Logs only** |
| latency | *does not exist* | `duration` | **Traces only** |
| pod | `instance` | `instance` | Yes |
| container | `container` | `container` | Yes |
| namespace / workload / cluster | same | same | Yes |
| region / app_version / env_type | same | same | Yes |
| timestamp | `timestamp` (→ `timestamp`) | `timestamp` (→ `start_timestamp`) | Label yes, column no |
| source | `source`, no enums | `source` = `eBPF`/`OTel` | Label yes, enums traces-only |

Confirmed failures from carrying names across signals:

```
service = checkout   on logs    → unknown field "service" for signal=logs
node = node-1        on traces  → unknown field "node" for signal=traces
pod = my-pod         on either  → unknown field "pod"      (it is "instance")
observation_point = x on traces → unknown field "observation_point"
duration_ms > 500    on traces  → unknown field "duration_ms"
```

`observation_point` is worth calling out: the `search-traces` tool description suggests
pinning it for exhaustive pagination, but it is not in the catalog and is rejected.

---

## Error Messages

**Storage name supplied:**

```
field "pod_name" is a storage column; use the catalog label "instance" instead
  (call get-trace-or-log-fields to see all labels)
```

Act on the suggestion — do not retry the same name.

**Unknown field:**

```
unknown field "service" for signal=logs; call get-trace-or-log-fields to discover
  valid fields (attributes carry an @ prefix)
```

Errors are prefixed by the slot that failed: `where clause: …`,
`required_fields[0]: …`, `group_by_fields[0]: …`, `fields[0]: …`, `sort_by: …`.

---

## Attributes

Dynamic attributes are **not in the catalog** — they are discovered per-window by scanning
storage, so they differ between deployments and windows. Neither signal's catalog contains
a single attribute entry.

| Where | Syntax | Works? |
|---|---|---|
| `where`, logs | `@user.id = abc-123` | ✅ |
| `where`, traces | `@db.system = postgresql` | ❌ **rejected** as unknown field |
| `group_by_fields` / `fields` / `required_fields` / `sort_by`, both signals | `{"field": "db.system", "is_attribute": true}` | ✅ |

Discovery reports the key **bare** in the `field` column with `is_attribute=true`; the `@`
appears only in the `example` cell.

**Log attribute operators**: `=` `!=` `IN` `<` `>` `<=` `>=` `LIKE` `ILIKE`. Unquoted
numerics are coerced, so `@latency > 100` compares numerically.

**Trace attributes** are stored as parallel `attribute_names[]`/`attribute_values[]` arrays
and are always string-typed. The parser is supposed to remap `=`/`IN`/`LIKE` to
`ARRAY_MAP*` operators, but it clears the attribute marker in the process, so the field
then fails column validation — hence the WHERE rejection above. Group-by is unaffected.

`exist(@field)` is broken on both signals: it emits an `EXIST` operator carrying a value,
which the validator rejects (`operator "EXIST" takes no values (got 1)`). `NOT_EXIST` has
no syntax at all. There is no working existence check.

---

## Free-Search Routing

Touching any of these fields routes the query to the **raw table** instead of the
pre-aggregated rollups — slower, but the only way to see message text or per-span detail:

- logs: `body`, `trace_id`, `span_id`, any attribute
- traces: `duration`, `trace_id`, `span_id`, `reason`, any attribute

It is computed automatically and reported as `is_free_search` in the output header.
Column-only filters stay on the fast rollup path. This is also why `duration` filters make
a trace query noticeably slower.

---

## Operator Availability vs Advertised

Discovery's `operators` column reflects an internal catalog that is **broader than the
WHERE parser**.

**Parseable in a WHERE string:** `=` `!=` `<` `>` `<=` `>=` `LIKE` `ILIKE` `SUBSTR_ILIKE`
`IN`

**Advertised but with no WHERE syntax** — these fail to parse: `HAS_TOKEN`, `HAS_ALL`,
`HAS_ANY`, `NOT_HAS_ANY`, `LIKE_AND`, `ILIKE_AND`, `ILIKE_LOG`, `ILIKE_LOG_AND`,
`SUBSTR_ILIKE_AND`, `IS_IP_ADDRESS`, `NOT_IS_IP_ADDRESS`, `EXIST`, `NOT_EXIST`, and the
whole `ARRAY_MAP*` family.

Other parser constraints:

- Bare values allow only `[A-Za-z0-9_.-]`. Anything with `/`, `:`, `%`, or a space must be
  **double-quoted**: `resource = "/api/v1"`, `timestamp > "2026-07-30T10:00:00Z"`.
- `NOT IN` is not a leaf operator — write `NOT (field IN (...))`.
- Trace `IN` values stay strings: `status_code IN (500, 502)` → `"500"`, `"502"`.
- `duration` is the only trace field whose value is coerced to a number (and scaled ×1e6
  from ms to ns). Every other trace value stays a string.
