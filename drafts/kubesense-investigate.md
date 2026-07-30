---
name: kubesense-investigate
description: End-to-end incident investigation in KubeSense — triage a firing alert, check whether it was already root-caused, correlate deploys and infra failures, follow a distributed trace to the failing hop, and scope logs and metrics to it. Use when an alert fired, a service is degraded, or the user asks "what's wrong".
metadata:
  version: "2.0.0"
  author: kubesense
  repository: https://github.com/kubesense-ai/kubesense-mcp-skills
  tags: kubesense,incident,investigation,rca,root-cause,triage,oncall,alerts,debugging
---

# KubeSense Incident Investigation

> [!NOTE]
> **Draft — not installable.** This file is intentionally not named `SKILL.md`, so the
> installer does not discover it. See [README.md](./README.md) for how to promote it.

A workflow, not a tool reference. It orders the available signals **cheapest and most
diagnostic first**, so most incidents resolve in three or four calls instead of a telemetry
fishing expedition.

Requires the KubeSense MCP server. The per-signal detail lives in
[kubesense-logs](../kubesense-logs/SKILL.md),
[kubesense-traces](../kubesense-traces/SKILL.md),
[kubesense-metrics](../kubesense-metrics/SKILL.md),
[kubesense-infra](../kubesense-infra/SKILL.md), and
[kubesense-alerts](../kubesense-alerts/SKILL.md).

## When to Use

- "This alert fired — what's wrong?"
- "Why is checkout slow / erroring?"
- "Something broke around 14:00"
- On-call triage of a page

## The Order That Matters

```
0. Prior art       find-investigation-for-alert   ← has someone already answered this?
1. Scope           get-alert-details              ← what breached, and for which workload?
2. Pattern         get-alert-history              ← chronic/flapping, or new?
3. Change          get-recent-changes             ← did we just deploy or scale?
4. Platform        get-infra-issues               ← OOM, CrashLoop, probes, scheduling?
5. Request path    get-distributed-trace          ← which hop fails or burns the time?
6. Evidence        search-logs (scoped)           ← the actual error, at the right service
7. Confirm         analyze-metrics                ← quantify the pressure
```

**Steps 0–4 are five cheap calls that resolve a large share of incidents outright.** Do not
start at step 5 or 6. Reaching for raw logs first is the single most common wasted effort —
you get a wall of text with no idea which service to read.

## 0. Check for Prior Art

```
find-investigation-for-alert(alert_rule_id, [fingerprint])
```

Returns the most recent **concluded** AI investigation: root cause, confidence, when it ran,
who started it. Running or failed investigations are not returned — neither has a verdict.

`found=false` is a **normal result**, not an error. Investigate yourself.

If found, the recorded root cause is usually the fastest path to an answer — but confirm it
still holds (check step 3 for a change since).

## 1. Scope the Alert

If you don't have an `alert_rule_id`, survey what's firing:

```
list-active-alerts                    → fingerprint, alert_rule_id, rule_name, severity, value, labels
```

Then:

```
get-alert-details(alert_rule_id, [fingerprint])
```

This is the highest-value first call. It returns the rule's `query_config`, condition, and
threshold — **what** breached — plus every firing series with its labels.

**Extract the scope from the firing series' labels**: `namespace`, `workload`, `pod`,
`cluster`. Every subsequent call gets scoped to these. An investigation that queries the
whole cluster instead of the affected workload will drown.

Pass `fingerprint` to focus one series; omit it to see all series of the rule.

## 2. Chronic or New?

```
get-alert-history(alert_rule_id, [fingerprint])
```

Triggered/resolved transitions, newest first, with each event's value and threshold.

- **Flapping** (many quick transitions) → often a threshold too tight for normal variance, or
  a periodic job. Consider whether the rule is right before hunting a cause.
- **Chronic** (firing for days) → not the cause of a new symptom. Look elsewhere.
- **New** (first firing) → correlate with step 3.

This reframes the whole investigation, so do it before digging.

## 3. What Changed

```
get-recent-changes(namespace, workload, [kind])
```

Image updates (deploys) and replica scaling. `detail` reads like
`kubesense: dev-v1.2.1279 -> dev-v1.2.1280` or `replicas 1 -> 0`.

**Compare the `when` against the alert's `starts_at`.** A deploy minutes before the alert
started is your hypothesis; go verify it rather than continuing down the list.

Widen `from_time` if the default hour doesn't cover when the symptom began.

## 4. Platform-Level Failures

```
get-infra-issues(namespace, workload, [reason])
```

Container crashes with exit codes, OOM kills, restart backoffs, probe failures, scheduling
and mount failures, image-pull errors, node problems.

**Omit `reason` first** to see every failure mode; narrow only once you know what you're
chasing. Reasons: `OOMKilling`, `BackOff`, `Unhealthy`, `FailedScheduling`, `FailedMount`,
`ImagePullBackOff`, `NodeNotReady`.

An `exit_code` of 137 is a SIGKILL — almost always the OOM killer; cross-check memory in
step 7. Exit 1 or 2 is usually the application failing on its own terms → go to logs.

For per-container detail (restart reason, last terminated state):

```
get-pod-detail(name, namespace, cluster)
```

## 5. Follow the Request Path

If the symptom is latency or request errors, get a `trace_id` — from `search-traces` scoped
to the workload, or from `list-issues`:

```
search-traces  where: "workload = checkout AND status = error"   → trace_id
get-distributed-trace(trace_id, from_time, to_time)
```

The window must **contain** the trace's start; use ~10 minutes either side. Traces are
time-partitioned, so a window that misses it finds nothing.

**Read `## services` before the span rows** — it is ordered worst-first by errors, then self
time. That row is your suspect.

Two rules that decide where to look next:

- **A span errored but every child succeeded** → the fault is *in* that service. Go to its
  logs.
- **Large `duration_us`, small `self_time_us`** → the service was **waiting**, not working.
  Investigate what it called (its children), not the service itself.
- **No error span at all** → still valid. The top `## services` row is the hop that burned
  the time.

Copy the failing span's `workload`, `namespace`, `start_time`, and `end_time` — they are the
exact filter for step 6.

## 6. Scoped Logs

Now — and only now — read logs, with the scope you earned:

```
search-logs
  where: "workload = checkout AND type = ERROR"
  from_time / to_time: the failing span's window, widened a few seconds
  required_fields: [instance, body]
```

Remember the [logs field names](../kubesense-logs/SKILL.md): `type` (not `level`),
`instance` (not `pod_name`), and severity values are **UPPERCASE**. There is no `service`
field on logs — use `workload`.

For the shape of the failure rather than individual lines:

```
analyze-logs  where: "type = ERROR"  group_by_fields: [workload]  value_operation: row_count
```

Group by `pattern_id` to cluster similar messages instead of reading each one.

## 7. Confirm Quantitatively

```
analyze-metrics  promql: "..."  query_type: "range"
```

Use metrics to **test the hypothesis**, not to discover it. Typical confirmations:

| Hypothesis | Query |
|---|---|
| OOM — was it near the limit? | `container_memory_working_set_bytes{container!=''} / kube_pod_container_resource_limits{resource="memory"} * 100` |
| CPU throttling | `rate(container_cpu_usage_seconds_total{container!=''}[5m])` vs `kube_pod_container_resource_limits{resource="cpu"}` |
| Restart storm | `increase(kube_pod_container_status_restarts_total[1h])` |
| Replicas unavailable | `kube_deployment_status_replicas - kube_deployment_status_replicas_ready` |

The cluster label is **`clusterId`**, and `container!=''` is mandatory on `container_*`
metrics. See [kubesense-metrics](../kubesense-metrics/SKILL.md).

## Shortcuts by Symptom

| Symptom | Start at |
|---|---|
| Pod restarting / CrashLoopBackOff | 4 (`get-infra-issues`) → `get-pod-detail` for the exit code → 6 |
| OOMKilled | 4 → 7 (memory vs limit) → 3 (did a deploy raise usage?) |
| Latency regression, no errors | 5 (`self_time_us` ranking) → 3 |
| 5xx spike | 5 → 6 → 3 |
| "Nothing works after the deploy" | 3 → 4 → 5 |
| Pending pods / won't schedule | 4 (`reason: FailedScheduling`) → `list-nodes` for pressure |
| Alert firing but service looks fine | 2 (flapping?) → `get-alert-details` to check the rule is sane |

## Reporting

State, in this order:

1. **What broke** — the user-visible symptom and its blast radius (which workloads,
   namespaces, how many series firing).
2. **Root cause** — with the specific evidence: the deploy and its timestamp, the exit code,
   the failing hop's name.
3. **Why you believe it** — the correlation you actually observed, e.g. "deploy at 14:02,
   alert started 14:04, `self_time_us` on checkout jumped 8×".
4. **What you ruled out** — the cheap checks that came back clean. This is what makes the
   conclusion trustworthy.
5. **Confidence, honestly.** If the correlation is circumstantial, say so.

If you could not determine a cause, say that plainly and list what you checked. Do not
present the most suspicious thing you found as a root cause.

## Rules

1. Follow the order. `find-investigation-for-alert` and `get-alert-details` before anything
   else; **never open with raw logs**.
2. Extract `namespace`/`workload`/`pod` from the alert labels and scope every subsequent call
   to them.
3. `get-alert-history` early — chronic and flapping alerts change what the investigation even
   is.
4. `get-recent-changes` is the cheapest hypothesis you will ever test. Always run it.
5. Prefer the platform's own detection (`list-issues`, `get-infra-issues`) over re-deriving
   problems from telemetry.
6. Use `analyze-*` to characterise, `search-*` only to read specific records.
7. Widen the time window before concluding "no data" — every tool defaults to one hour, and
   an empty result is not evidence of absence.
8. Metrics confirm hypotheses; they rarely generate them.
9. Report what you ruled out, and state confidence honestly.
