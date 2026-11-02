# Processor reference

Config for each rule type of `create-log-pipeline` and `update-log-pipeline`. A rule is
`{name, type, config}` (plus `id` when updating an existing rule). Only the config fields
listed for a type are used; any other key is refused by name. Regexes are RE2 and are checked
when you save. Every example below is the `config` object only.

Conventions:

- **`field`** is a log attribute key, written without the `@` that WHERE clauses use. Dotted keys (`http.status`) are flat keys.
- **Empty `field`** means the log `body`, for the types that say so.
- **No match leaves the log as it was**, except where a type notes otherwise.
- Destructive options (`delete_original`, `replace_original`, overwriting) are named in the Dangers section of [SKILL.md](../SKILL.md#dangers). They are flagged here as **destructive**.

| Type | Does | Required config |
|---|---|---|
| `parse` | regex the body into attributes | `pattern` |
| `extract` | regex an attribute into new attributes | `field`, `pattern` |
| `parse-json-field` | parse a JSON string attribute and flatten it | `field` |
| `json-extract` | copy an attribute into the log level | `field`, `new_field: "level"` |
| `extract-timestamp` | set the log timestamp from an attribute | `field`, `pattern` |
| `add-field` | set an attribute to a constant | `new_field`, `data` |
| `edit-metadata` | set cluster, namespace, workload, source or env_type | `new_field`, `data` |
| `remove-fields` | delete attributes | `field` |
| `stringify-fields` | turn a non-string attribute into a JSON string | `field` |
| `replace` | regex replace in an attribute or the body | `pattern` |
| `block` | drop logs | `field` + `pattern` |
| `protect` | encrypt and mask sensitive values | `pattern`, `fields`, `secret_captures` |
| `lookup` | enrich from a reference table | `reference_table_id`, `lookup_key`, `source_field`, `target_fields` |

## parse

Regex-parse the **body**; named groups become attributes.

| Field | Meaning |
|---|---|
| `pattern` | Required. Named groups (`(?P<method>\w+)`) become attributes. |
| `replace_original` | **Destructive.** Also replaces the body with the parsed attributes. |
| `name_as_format` | Record the rule name as the log's `format` instead of `custom`. |

Captured names are merged over attributes that already exist with the same name. A body the
pattern does not match is left unchanged.

```json
{ "pattern": "(?P<method>\\w+) (?P<path>\\S+) (?P<status>\\d{3})" }
```

## extract

Regex an existing attribute into new attributes.

| Field | Meaning |
|---|---|
| `field` | Required. Attribute to read. |
| `pattern` | Required. Named groups become attributes. |
| `delete_original` | **Destructive.** Removes `field` afterwards, even on a log the pattern did not match. |

```json
{ "field": "path", "pattern": "^/api/(?P<api_version>v\\d+)/" }
```

## parse-json-field

Parse a JSON string held in an attribute and flatten the object into the log attributes.

| Field | Meaning |
|---|---|
| `field` | Required. Attribute holding the JSON string. |
| `new_field` | Attribute the parsed object is written to. Always set it. |
| `replace_original` | **Destructive.** Overwrite `new_field` with the parsed object. |
| `delete_original` | **Destructive.** Remove `field` after a successful parse. |

Only a JSON object is applied; a value that is not valid JSON, or not an object, leaves the log unchanged.

```json
{ "field": "payload", "new_field": "payload_parsed" }
```

## json-extract

Copy an attribute into the built-in level column. `level` is the only destination.

| Field | Meaning |
|---|---|
| `field` | Required. Attribute holding the level text. |
| `new_field` | Required in practice: `"level"`. The value is upper-cased. |

```json
{ "field": "severity", "new_field": "level" }
```

## extract-timestamp

Set the log timestamp from an attribute.

| Field | Meaning |
|---|---|
| `field` | Required. Attribute holding the time text. |
| `pattern` | Required. A strptime format, e.g. `%Y-%m-%dT%H:%M:%S%.fZ`. |
| `delete_original` | **Destructive.** Removes `field` even if the time did not parse. |

The timestamp is replaced only when the format parses; otherwise it keeps its value. A
format that parses wrongly stores the log at the wrong time.

```json
{ "field": "ts", "pattern": "%Y-%m-%dT%H:%M:%S%.fZ" }
```

## add-field

Set an attribute to a constant string.

| Field | Meaning |
|---|---|
| `new_field` | Required. Attribute to write. **Overwrites** an existing one. |
| `data` | The value, always stored as a string. |
| `field`, `pattern` | Optional condition: add only when that attribute (empty `field` means the body) matches the regex. |

```json
{ "new_field": "team", "data": "payments", "field": "path", "pattern": "^/checkout" }
```

## edit-metadata

Set a top-level label on the log. Changes where the log appears.

| Field | Meaning |
|---|---|
| `new_field` | Required. One of `workload`, `namespace`, `cluster`, `source`, `env_type`. |
| `data` | The value to set. |
| `field`, `pattern` | Optional condition, as for `add-field`. Without it the rule applies to every log of the pipeline. |

```json
{ "new_field": "env_type", "data": "staging", "field": "", "pattern": "env=staging" }
```

## remove-fields

Delete attributes.

| Field | Meaning |
|---|---|
| `field` | Required. Attribute names, comma-separated: `"password, token"`. |

Acts on attributes only, not on the body or top-level columns.

```json
{ "field": "debug_blob, internal_trace" }
```

## stringify-fields

Turn a non-string attribute (object, array, number) into a JSON string. String values are left alone.

| Field | Meaning |
|---|---|
| `field` | Required. |
| `new_field` | Where to write the string. Defaults to `field`. |
| `replace_original` | **Destructive.** Write back to `field`. |
| `delete_original` | **Destructive.** Remove `field`. With `new_field` empty this removes the value just written. |

```json
{ "field": "labels", "new_field": "labels_json" }
```

## replace

Regex replace.

| Field | Meaning |
|---|---|
| `pattern` | Required. |
| `replacement` | Replacement text. |
| `field` | Attribute to edit. Empty rewrites the **body** in place and ignores the options below. |
| `new_field` | With `field` set, where the result is written. |
| `replace_original` | **Destructive.** Write the result back to `field`. |
| `delete_original` | **Destructive.** Remove `field` afterwards, even on a log the pattern did not match. |

With `field` set, set exactly one of `new_field` or `replace_original`. A rule read back
carries `condition_version`, `conditions` and `raw_conditions`; resend them unchanged. An
update that drops a saved replace rule's conditions is refused, as is a replace rule with no
`field`, `pattern` or `conditions`. To widen on purpose, send `condition_version: 1` with
empty `conditions`.

```json
{ "field": "url", "pattern": "token=[^&]+", "replacement": "token=REDACTED", "new_field": "url_clean" }
```

## block

Drop logs. Dropped logs are not stored.

| Field | Meaning |
|---|---|
| `field` | Attribute to test. Empty tests the body. |
| `pattern` | Regex. Drops logs that match. |
| `block_unmatched` | Drops logs that do **not** match instead. |

A block rule with no `field`, `pattern` or `conditions` would drop **every** log the
pipeline's inputs match, so the server refuses it (also `block_unmatched` with no match, and
`condition_version: 1` with empty `conditions`). A rule read back carries `condition_version`,
`conditions` and `raw_conditions`; resend all three unchanged, or the save is refused.
An over-broad `pattern` is not caught.

```json
{ "field": "path", "pattern": "^/healthz$" }
```

## protect

Encrypt and mask sensitive values; one-way. Must be the last rule(s) of the pipeline.

| Field | Meaning |
|---|---|
| `pattern` | Required. Regex with capture groups. It must not contain a single quote. |
| `fields` | Required, 1 to 16 entries: `"body"` or attribute names. |
| `secret_captures` | Required, 1 to 8 entries: capture group names or numbers to encrypt. Selected captures must not overlap. |
| `mask_prefix` | Visible leading characters, 1 to 64. Default 3; `0` also gives 3. |

Masking happens only where the aggregator has an active encryption key. Without one the
rule saves and passes logs through unmasked, so check a new log after saving.

```json
{ "pattern": "card=(?P<pan>\\d{13,16})", "fields": ["body"], "secret_captures": ["pan"], "mask_prefix": 4 }
```

## lookup

Enrich a log from a reference table.

| Field | Meaning |
|---|---|
| `reference_table_id` | Required. An existing, enabled reference table. |
| `lookup_key` | Required. Must equal that table's primary key column. |
| `source_field` | Required. Attribute holding the key. |
| `target_fields` | Required. Table columns to copy into the log. Each must exist in the table. |
| `overwrite_existing` | **Destructive.** Overwrite attributes that already exist. Off: only empty ones are filled. |
| `fallback` | Object of target field to default value, used when the key is not found. |

No tool lists reference tables. Take the id from an existing lookup rule in
`get-log-pipeline`, or ask the user. Reference tables are shared: editing one changes every
pipeline that looks it up.

```json
{ "reference_table_id": "team-owners", "lookup_key": "workload", "source_field": "workload",
  "target_fields": ["owner", "oncall"], "fallback": { "owner": "unknown" } }
```
