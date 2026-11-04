---
name: kubesense-log-pipelines
description: Use before any write to a KubeSense log pipeline, and when the user wants logs parsed, fields extracted, values masked or redacted, logs dropped, fields removed or renamed, or logs enriched at ingestion — or wants their log pipelines listed, read, created or edited.
metadata:
  version: "1.0.0"
  author: kubesense
  repository: https://github.com/kubesense-ai/kubesense-mcp-skills
  tags: kubesense,log-pipelines,logs,ingestion,processors,parsing,masking,block,mcp
---

# KubeSense Log Pipelines

A log pipeline is an ordered list of processors (rules) that rewrites, enriches, masks or
drops logs **while they are ingested**. These tools read and write that configuration.
Requires the KubeSense MCP server; see **[kubesense-mcp](../kubesense-mcp/SKILL.md)**.
RBAC resolves against the log pipelines module (`log_rule_group`); a permission error names it.

| Tool | Does |
|---|---|
| `list-log-pipelines` | Pipelines in chain order: `id`, `name`, `enabled`, `source`, `index`, `inputs`, `updated_at`, `can_edit`. Filters `source`, `name`. |
| `get-log-pipeline` | One pipeline with its `rules`, each `{id, name, type, config}`, in run order. Returns the `updated_at` that `update-log-pipeline` needs. |
| `create-log-pipeline` | New pipeline: `name`, `source`, `inputs` (at least one domain), `rules` (at least one). Added **enabled**, at the **end** of the chain. |
| `update-log-pipeline` | Rename, replace `inputs`, replace the rule list, or switch the pipeline on or off. |

What these tools cannot do: delete a pipeline or a rule, reorder pipelines, change
`source`, preview a pipeline against sample logs, or list reference tables. Deleting,
reordering and a different `source` are done by a human in the Log Pipelines UI.

## Dangers

> [!CAUTION]
> A saved pipeline acts on **every matching log that arrives from that moment**. Nothing
> a processor drops, removes, masks or overwrites comes back. There is no preview, no
> undo and no delete. Read every item below before the first write.

**1. Changes are applied at ingestion and are permanent for new logs.**
Logs already stored are never rewritten; logs arriving after the save are transformed
before they are stored. What a processor drops, removes, masks or overwrites on those logs
is lost for good. Reverting a rule later fixes only logs that arrive after the revert.
*Guard:* treat every write as irreversible for the logs it touches. Narrow `inputs`
first (one workload), confirm the effect on new logs with `search-logs`, then widen with
`update-log-pipeline`.

**2. Nothing can be deleted through MCP, for anyone, and you must not imitate deletion.**
Neither pipelines nor rules can be removed. An update whose rule list omits an existing
rule id is refused. To stop a pipeline, set `enabled: false`; deletion is a human action
in the Log Pipelines UI.
*Guard:* if the user asks to delete, disable the pipeline (after confirming) and say a
human must delete it in the UI. Never emulate deletion by emptying a rule's config,
repointing `inputs` at a name that matches nothing, or turning a rule into a no-op.
A pipeline reshaped into a stand-in for "deleted" still runs and still confuses the next reader.

**3. `block` drops logs, and an over-broad pattern drops all of them.**
A dropped log is never stored. The server **refuses** a `block` rule that matches every
log: no `field`, `pattern` or `conditions`; `block_unmatched` with no match; `condition_version: 1`
with empty `conditions`. It also refuses `conditions` sent without `condition_version: 1`
(they would be ignored), and a `replace` rule with no `field`, `pattern` or `conditions`.
An over-broad regex is **not** caught: it drops everything it matches.
`block_unmatched: true` inverts the test and drops everything the pattern does *not* match.
A block or replace rule read back from `get-log-pipeline` has an empty `field`/`pattern`
and carries its test in `condition_version`, `conditions` and `raw_conditions`. Re-saving
it without them is refused for a block rule, and for a replace rule whose saved
conditions the update drops (to widen a replace on purpose, send `condition_version: 1`
with empty `conditions`).
*Guard:* never send a `block` rule without a concrete `field`/`pattern`. When re-saving an
existing block or replace rule, copy its config back unchanged, all three condition fields
included. The refusal does not make the rule safe: say aloud which logs it will drop, with
the sampled lines it matches and one it does not.

**4. Destructive processors lose data on the logs they touch.**
- `remove-fields` deletes attributes.
- `replace` with `replace_original` overwrites the value; with an empty `field` it rewrites the body in place.
- `parse` with `replace_original` replaces the raw body with the parsed attributes.
- `extract`, `extract-timestamp` and `replace` with `delete_original` delete the source attribute **even when the pattern did not match**.
- `stringify-fields` with `delete_original` and no `new_field` writes the value back to the same name and then deletes it.
- `add-field` overwrites an existing attribute of the same name, unconditionally.
- `lookup` with `overwrite_existing` overwrites existing attributes (and fallbacks, too).
- `parse` and `extract` merge captured groups over any attribute of the same name.
*Guard:* prefer a new `new_field` over overwriting; leave `delete_original` and `replace_original` off unless the user asked for deletion of that field; check the pattern against several sampled lines first, including lines it should not match.

**5. `edit-metadata` changes a log's identity.**
It sets `cluster`, `namespace`, `workload`, `source` or `env_type` on the log. With no
`pattern` it applies to every log in the pipeline. Logs then appear under the new
workload, and later pipelines match on the new value.
*Guard:* always give it a `field` + `pattern` that selects exactly the intended lines; state the before and after value to the user.

**6. `extract-timestamp` moves logs in time.**
A format that parses but is wrong (day and month swapped, a missing timezone, seconds
read as milliseconds) stores the log at the wrong time, so searches, alerts and
dashboards over the real window do not find it. If the format fails to parse the
timestamp is left alone.
*Guard:* build the strptime format from sampled lines that include the timezone, and check a new log's `timestamp` right after the save.

**7. A rule that errors at runtime drops the log.**
Generated processors run with drop-on-error: a log on which a rule's logic fails is dropped,
not passed through. `protect` is also set to drop on any unexpected error.
*Guard:* keep patterns simple and anchored to sampled lines; verify after the save that the log count for the inputs did not fall (`analyze-logs`, `row_count`, before and after).

**8. `protect` masking is one-way, must be last, and can silently do nothing.**
`protect` replaces the visible value with a mask and stores the original only as
ciphertext. The mask cannot be removed from stored logs, and logs that were stored
unmasked before the rule existed stay unmasked. `protect` rules must be the final rules of
the pipeline; a save with a processor after one is refused. If the aggregator has no
active 32-byte key configured, the rule saves and **does not mask anything**. `mask_prefix`
is 1 to 64 visible characters; `0` or omitted gives the default of 3, not 0.
*Guard:* keep every `protect` rule last, including when inserting a new rule into an existing list; after the save, read new logs with `search-logs` and confirm the value is masked; to show fewer than 3 characters use `mask_prefix: 1`, and tell the user a fully hidden value is not available.

**9. Broad inputs touch every domain.**
`{"name":"*","type":"cluster"}` applies the pipeline to every domain's logs (a domain is
what the API calls a `cluster`). A domain node with no `childs` (or `has_all_childs: true`)
covers every namespace and workload in it. `*` means "all" only as a domain name; a
namespace or workload named `*` matches no log, and the server refuses one you send.
`update-log-pipeline` replaces the whole `inputs` list, so widening or narrowing
is a full rewrite of it.
*Guard:* default to the narrowest matcher that covers the request (domain, namespace and workload); use `*` only when the user said every domain.

**10. A new pipeline goes live immediately, at the end of the chain.**
`create-log-pipeline` saves it enabled and appends it after every existing pipeline, so
it sees logs only after all earlier pipelines have changed or dropped them. Fields it
expects may already be removed, renamed or masked, and logs may already be dropped. The
tools cannot place it elsewhere.
*Guard:* run `list-log-pipelines` first and read each earlier pipeline that overlaps the new `inputs`; if ordering matters, say a human must move it in the UI. Use the same listing to avoid duplicating an existing pipeline.

**11. `source` is fixed at creation.**
`parsed` runs on logs that already have structured attributes; `unparsed` runs on logs
before any parsing. `update-log-pipeline` cannot change `source`; a wrong choice is
repaired only by a human recreating the pipeline in the UI, after logs have already gone through it wrongly.
*Guard:* take `source` from a comparable existing pipeline (`list-log-pipelines`, `get-log-pipeline`) or from the sampled logs. Doubt means ask the user before creating.

**12. Each save rewrites the shared Vector config for every pipeline.**
The service regenerates the whole aggregator pipeline config under one process lock and
publishes it; a config the validator rejects is refused (`invalid pipeline: the pipeline produced a
Vector config the validator rejected: <reason>`) and the old one is kept. A config that is valid
but wrong goes live on the next log. Disabling a pipeline also changes what the pipeline after it receives.
*Guard:* validity is not correctness; the checks in the workflow below are what protect production. After the write, re-read with `get-log-pipeline`.

**13. Optimistic lock: stale `updated_at` is refused. Re-read, never retry blind.**
`update-log-pipeline` needs the `updated_at` from `get-log-pipeline` whenever `name`,
`inputs` or `rules` change. The server checks it first, before it judges any rule; if the
pipeline changed since, the edit is refused with
`stale: pipeline changed since you read it; call get-log-pipeline again`.
*Guard:* on `stale:`, call `get-log-pipeline` again, re-apply your edit to the new version, and show the user the diff again. Never rebuild a rule list from memory or from an earlier turn. `enabled` toggles also change `updated_at`, so re-read after any toggle.

**14. Per-pipeline access and audit.**
A restricted pipeline can be changed only by its owner, its editors and Log Pipeline
Admins (`can_edit` in the listing tells you). An admin override on a pipeline you do not own is recorded as an override. Every create and update
you make is written to the audit log with "(via AI agent)". Restricting a pipeline
does not protect the chain after it, and reference tables are shared, so editing one
changes every pipeline that looks it up.
*Guard:* check `can_edit` before drafting an edit; if it is false, stop and tell the user who can change it. Do not look for another route.

**15. Confirm before every write.**
Both write tools are annotated destructive, so an MCP client may ask the user to approve
each call. That prompt does not replace this confirmation; it shows no pipeline contents.
*Guard:* before `create-log-pipeline` or `update-log-pipeline` (an `enabled`-only call included), show the user the exact pipeline: name, source, `inputs` as a tree, and
every rule in order with its full config; for an edit, the before and after. Name the Dangers above that apply. Call the tool only after an explicit yes to *that* content. A changed draft needs a new yes.

## Workflow

Each step ends when its condition is true.

1. **Survey.** `list-log-pipelines` (add `name` or `source` to narrow). Done when you know which pipelines overlap the requested logs, their chain `index`, and whether `can_edit` is true for the one to change. Check for an existing pipeline that already does the job.
2. **Template.** `get-log-pipeline` on the closest existing pipeline, and on the overlapping earlier ones. Done when you have read the `config` shape of each rule type you plan to use, and know which fields earlier pipelines add, remove or rename.
3. **Sample.** Use [kubesense-logs](../kubesense-logs/SKILL.md): `get-fields` with `signal: "logs"`, then `search-logs` on the target `workload`/`namespace` with `body` and the attributes you plan to touch. Done when you hold at least 10 real lines per distinct format, one that the pattern must not match, and the attribute names verbatim. A processor's `field` is the attribute key without the `@` that WHERE uses. Sampled attributes are the *stored* ones, after existing pipelines ran; an `unparsed` pipeline runs earlier, so work from `body`.
4. **Draft.** Write `name`, `source`, `inputs` and `rules`. Rule names must be unique across **all** pipelines and pipeline names unique across pipelines, so use a distinct prefix. Done when each regex is checked by hand against every sampled line (RE2 syntax; the server refuses an invalid regex, not a wrong one) and the Dangers that apply are named.
5. **Confirm.** Danger 15. Done on an explicit yes.
6. **Write.** One call. For `update-log-pipeline` pass `id`, `updated_at` and the full list (see below).
7. **Verify.** `get-log-pipeline` for the saved shape and new `updated_at`; then `search-logs` on a window after the save for the effect, and `analyze-logs` `row_count` for the inputs to confirm volume did not collapse. Done when the sampled new logs show the intended result. If they do not, disable the pipeline (`enabled: false`) and tell the user, rather than layering more rules.

### Inputs: the matcher tree

`inputs` is a list of matchers; a log matches the pipeline if it matches **any** top-level
matcher. A node is `{"name","type"}` with `type` `cluster`, `namespace` or `workload`. A
`cluster` node is a **domain**: say "domain" to the user, and send `cluster` as the type.

- Nest a namespace under a domain and a workload under a namespace, with `childs`.
- A workload whose logs have no namespace (legacy, non-Kubernetes services) goes directly
  under its domain. Never invent a namespace for it.
- A workload directly under a domain matches that workload name in every namespace of the domain.
- A node with no `childs`, or with `has_all_childs: true`, matches everything below it.
  `get-log-pipeline` returns `has_all_childs` on every node; copy it back as it is.
- `*` means all only as a domain name. A namespace or workload named `*` matches no log and is refused.
- There is no service node: use the workload name the logs carry.
- Names are exact and case-sensitive. Take them from `list-clusters` / `list-workloads`, or,
  for domains with no Kubernetes inventory, from the `cluster`, `namespace` and `workload`
  values on logs from `search-logs`.

```json
[
  { "name": "prod-us", "type": "cluster", "childs": [
      { "name": "payments", "type": "namespace", "childs": [
          { "name": "checkout", "type": "workload" } ] } ] },
  { "name": "legacy-dc", "type": "cluster", "childs": [
      { "name": "billing-batch", "type": "workload" } ] },
  { "name": "prod-eu", "type": "cluster" }
]
```

This matches `checkout` in `payments` on `prod-us`, `billing-batch` in any namespace (or none)
on `legacy-dc`, plus everything on `prod-eu`.

Refusals, each prefixed `invalid pipeline: ` and followed by a path such as `inputs[0]` or
`inputs[0].childs[1]`:
- `a top-level input must be a domain (type "cluster"), not a namespace. Nest a namespace or workload under a domain, and a workload under a namespace` (likewise `not a workload`)
- `a domain (type "cluster") can only hold namespace or workload nodes, not cluster`
- `a namespace can only hold workload nodes, not namespace` (likewise `not cluster`)
- `a workload cannot have childs`
- `a namespace named "*" matches no log. "*" means all only on a domain. To match one workload that has no namespace, put the workload directly under its domain` (likewise `a workload named "*"`). Only inputs you send are checked, so a saved pipeline that already has one can still be renamed or have its rules edited.
- `type "<x>" is not one of cluster, namespace, workload`
- `name is required`

### Create

```json
{
  "name": "checkout-nginx-parse",
  "source": "parsed",
  "inputs": [{ "name": "prod-us", "type": "cluster", "childs": [
    { "name": "payments", "type": "namespace", "childs": [
      { "name": "checkout", "type": "workload" } ] } ] }],
  "rules": [
    { "name": "checkout-nginx-parse-access", "type": "parse",
      "config": { "pattern": "(?P<method>\\w+) (?P<path>\\S+) (?P<status>\\d{3})" } }
  ]
}
```

The result carries `id`, `name`, `updated_at` and a `url` (`/log-pipelines?pipeline=<id>`).
Refer to the pipeline by name when you speak to the user.

### Update

Read first, then send the **complete** result you want:

```json
{
  "id": "<pipeline id>",
  "updated_at": "<exactly as get-log-pipeline returned it>",
  "rules": [
    { "id": "<existing rule id>", "name": "checkout-nginx-parse-access", "type": "parse",
      "config": { "pattern": "(?P<method>\\w+) (?P<path>\\S+) (?P<status>\\d{3})" } },
    { "name": "checkout-drop-health", "type": "block",
      "config": { "field": "path", "pattern": "^/healthz$" } }
  ]
}
```

- `rules`, when present, is the **full ordered** list: an entry with `id` updates that rule (send its complete `name`, `type`, `config`), an entry without `id` creates one. List order is run order. **Every existing rule id must appear** or the update is refused. Omit `rules` to keep them.
- `name` and `inputs` are optional; omitted ones keep their saved value. `inputs` replaces the whole list.
- `enabled` is optional and saved in the same write as any other change, so switching a pipeline on while editing a rule is one call. `updated_at` is required whenever `name`, `inputs` or `rules` change and is not needed for an `enabled`-only call.
- An edit does not move the pipeline in the chain and does not change its `source`.
- A disabled pipeline's edits are saved but not live until it is enabled. Setting `enabled: true` on it publishes the saved rules.
- Config keys a rule type does not have are refused by name, so a misspelt key never saves silently.

Common failures. Each is returned as a tool error; `invalid pipeline:` messages name the rule and the reason: fix and re-confirm.
- `stale: pipeline changed since you read it; call get-log-pipeline again` (Danger 13). Also `stale: nothing was changed: who may edit this pipeline changed while you were acting on it. Re-read it with get-log-pipeline and try again`.
- `invalid pipeline: updated_at is required to change a pipeline's name, inputs or rules: pass the value get-log-pipeline returned`.
- `invalid pipeline: the pipeline produced a Vector config the validator rejected: <reason>` (Danger 12).
- `invalid pipeline: rules[<i>] (block, "<name>"): a block rule with no field, pattern or conditions drops EVERY log of the pipeline. ...` (Danger 3). The replace form reads `a replace rule with no field, pattern or conditions would rewrite every log`.
- `invalid pipeline: rules[<i>] (<type>, "<name>"): conditions are ignored unless condition_version is 1. Send condition_version, conditions and raw_conditions together, as get-log-pipeline shows them`.
- `invalid pipeline: rules[<i>] (replace, "<name>"): the saved rule only applies to logs that match its conditions, and this update leaves them out, so it would apply to every log. ...`.
- `invalid pipeline: rules cannot be deleted through this tool. The list must include every existing rule; missing: <id> ("<name>"). To stop the pipeline from running, set enabled to false instead`. Your list left a saved rule out; re-read and include it.
- `invalid pipeline: rules[<i>]: id "<id>" is not a rule of this pipeline` and `rule id "<id>" is listed twice`.
- `invalid pipeline: inputs[...]`: see the nesting refusals above.
- `not allowed: ` (access, Danger 14; includes `you have read-only access to log pipelines`).
- `unavailable: ` (access control cannot be evaluated; nothing was changed).
- `log pipeline not found: it does not exist or you cannot see it. Use list-log-pipelines for the ids you can use`.

## Processors

Thirteen rule types: `parse`, `extract`, `parse-json-field`, `json-extract`,
`extract-timestamp`, `add-field`, `edit-metadata`, `remove-fields`, `stringify-fields`,
`replace`, `block`, `protect`, `lookup`.

Per-type config fields, minimal examples and the quirks of each are in
**[references/processors.md](./references/processors.md)**. Read the entry for every type
you use before drafting. `field` always names a log attribute (a key under the log
attributes, not a top-level column); an empty `field` means the log `body` for the types
that allow it.

`get-log-pipeline` omits config settings that are at their zero value. A `block` or
`replace` rule read back also carries `condition_version`, `conditions` and
`raw_conditions`: send all three back unchanged when re-saving that rule (a block rule
without them, or a replace rule that drops saved conditions, is refused), and author new
rules with `field` and `pattern` only.

## Rules

1. Survey, template, sample before drafting; never invent a field, domain, workload or reference table id.
2. Confirm the exact pipeline with the user before `create-log-pipeline` or `update-log-pipeline`.
3. Always `get-log-pipeline` immediately before `update-log-pipeline`, and pass `updated_at` unchanged.
4. `rules` in an update is the full ordered list with every existing id.
5. Narrow `inputs` first; `block` always with a concrete pattern; `protect` always last.
6. Prefer `new_field` over overwriting; leave `delete_original` and `replace_original` off by default.
7. Deletion belongs to a human in the UI. Disable with `enabled: false`; never emulate deletion.
8. Verify new logs after every write; on a bad result, disable and report.
