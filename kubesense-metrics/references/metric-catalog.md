# KubeSense Metric Catalog

The metric families KubeSense collects and queries internally. Source of truth:
`kubeapi/observability/common/constants.go`.

**This is what to expect, not a guarantee.** Which families are present depends on the
collectors a cluster ships (kube-state-metrics vs OTel, node-exporter vs hostmetrics).
Application metrics are entirely deployment-specific and are not listed here. Always
confirm with `get-available-metrics`.

Standard labels: `clusterId` (camelCase), `namespace`, `pod`, `container`, `node`.

---

## Containers & Pods (cAdvisor + kube-state-metrics)

| Metric | Meaning |
|---|---|
| `container_cpu_usage_seconds_total` | Counter, CPU seconds. `rate()` → cores; ×1000 → millicores |
| `container_memory_working_set_bytes` | Gauge, working-set memory |
| `kube_pod_container_resource_limits` | Limits. Needs `resource="cpu"` or `resource="memory"` |
| `kube_pod_container_resource_requests` | Requests. Same `resource` label |
| `kube_pod_status_phase` | 1/0 per `phase` label (`Running`, `Pending`, `Failed`, `Unknown`, `Succeeded`) |
| `kube_pod_status_qos_class` | 1/0 per QoS class label |
| `kube_pod_container_status_restarts_total` | Restart counter |
| `kube_pod_init_container_status_restarts_total` | Init-container restart counter |
| `kube_pod_container_status_ready` | 1/0 readiness |
| `kube_pod_container_status_running` | 1/0 running |
| `kube_pod_container_status_terminated` | 1/0 terminated |
| `kube_pod_container_status_terminated_reason` | 1/0 per `reason` label (`OOMKilled`, `Error`, …) |
| `kube_pod_container_status_waiting` | 1/0 waiting |
| `kube_pod_container_status_waiting_reason` | 1/0 per `reason` label (`CrashLoopBackOff`, `ImagePullBackOff`, …) |
| `kube_pod_init_container_status_*` | Init-container equivalents of the four above |
| `kube_pod_info` | Metadata series (node, host IP, …) |
| `kube_pod_container_info` / `kube_pod_init_container_info` | Container image metadata |
| `kube_pod_created` | Creation timestamp (unix seconds) |
| `kube_pod_ips` | Pod IP metadata |
| `kube_pod_service_account` | Service-account metadata |
| `kube_pod_tolerations` | Toleration metadata |

**Cause-of-death queries.** OOM kills and crash loops are label-encoded on the
`*_reason` metrics:

```promql
kube_pod_container_status_terminated_reason{reason="OOMKilled"} > 0
kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} > 0
```

For a narrative (exit codes, event messages, counts) prefer `get-infra-issues` from
[kubesense-infra](../../kubesense-infra/SKILL.md) — it reads cluster events directly.

## Nodes

| Metric | Meaning |
|---|---|
| `k8s_node_cpu_time_seconds_total` | Node CPU counter (KubeSense collector) |
| `node_cpu_usage_seconds_total` | Node CPU counter (alternate) |
| `k8s_node_memory_working_set_bytes` | Node working-set memory |
| `k8s_node_filesystem_usage_bytes` | Node filesystem used bytes |
| `kube_node_status_allocatable` | Allocatable capacity; `resource` label discriminates cpu/memory/pods |
| `kube_node_status_capacity` | Total capacity; same `resource` label |
| `kube_node_status_condition` | 1/0 per (`condition`, `status`) pair — `condition="Ready",status="true"` |
| `kube_node_status_addresses` | Address metadata |
| `kube_node_spec_taint` | Taint metadata |
| `kube_node_info` | Kubelet/runtime/OS metadata |
| `kube_node_created` | Creation timestamp |

Derived gauges KubeSense computes rather than scrapes: `node_allocatable_cpu`,
`node_available_mem_bytes`, `node_disk_space_used_percent`.

## Hosts — node-exporter family

| Metric | Meaning |
|---|---|
| `node_cpu_seconds_total` | Per-mode CPU counter (`mode` label) |
| `node_memory_MemTotal_bytes` | Total memory |
| `node_memory_MemAvailable_bytes` | Available memory |
| `node_filesystem_size_bytes` | Filesystem size |
| `node_filesystem_free_bytes` | Filesystem free |
| `node_uname_info` | OS/kernel metadata |
| `node_boot_time_seconds` | Boot timestamp |

CPU utilisation is the standard idle-subtraction:

```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## Hosts — OpenTelemetry hostmetrics family

Present instead of the node-exporter family when a cluster ships via the OTel collector.
Labels differ: `kubesense_cluster`, `host_name`, `kubesense_env_type`.

| Metric |
|---|
| `system_cpu_time_seconds_total` |
| `system_memory_usage_bytes` |
| `system_filesystem_usage_bytes` |
| `system_processes_count` |
| `process_cpu_time_seconds_total` |
| `process_memory_usage_bytes` |

## Processes — process-exporter family

| Metric | Meaning |
|---|---|
| `namedprocess_namegroup_cpu_seconds_total` | Per-group CPU counter |
| `namedprocess_namegroup_memory_bytes` | Per-group memory |
| `namedprocess_namegroup_oldest_start_time_seconds` | Group's oldest process start (unix seconds) |

The `groupname` label is formatted `{pid}-{command}`, so each group holds exactly one
process. The OTel equivalent splits this into `process_pid` / `process_command_line` /
`process_executable_name`.

## Workload Controllers

| Kind | Metrics |
|---|---|
| Deployment | `kube_deployment_status_replicas`, `_replicas_available`, `_replicas_ready`, `kube_deployment_status_condition`, `kube_deployment_created` |
| StatefulSet | `kube_statefulset_status_replicas`, `_replicas_available`, `_replicas_ready`, `kube_statefulset_created` |
| DaemonSet | `kube_daemonset_status_current_number_scheduled`, `_desired_number_scheduled`, `_number_available`, `_number_ready`, `kube_daemonset_created` |
| ReplicaSet | `kube_replicaset_status_replicas`, `_ready_replicas`, `_fully_labeled_replicas`, `kube_replicaset_owner`, `kube_replicaset_created` |
| Job | `kube_job_status_succeeded`, `_start_time`, `_completion_time`, `kube_job_owner`, `kube_job_created` |
| CronJob | `kube_cronjob_status_active`, `_last_schedule_time`, `kube_cronjob_info`, `kube_cronjob_created` |
| HPA | `kube_horizontalpodautoscaler_status_current_replicas`, `_status_desired_replicas`, `_spec_min_replicas`, `_spec_max_replicas`, `kube_horizontalpodautoscaler_created` |
| ConfigMap | `kube_configmap_created` |

The grouping label is the kind's own name — `deployment`, `daemonset`, `statefulset`,
`horizontalpodautoscaler` — not a generic `workload`.

Unavailable replicas is a subtraction across two metrics of the same family:

```promql
kube_deployment_status_replicas - kube_deployment_status_replicas_ready > 0
```

## Storage — PV / PVC

| Metric | Meaning |
|---|---|
| `kubelet_volume_stats_capacity_bytes` | PVC capacity |
| `kubelet_volume_stats_used_bytes` | PVC used |
| `kubelet_volume_stats_available_bytes` | PVC available |
| `kube_persistentvolume_capacity_bytes` | PV capacity |
| `kube_persistentvolume_status_phase` | 1/0 per PV phase label |
| `kube_persistentvolume_info` / `_claim_ref` / `_created` | PV metadata |
| `kube_persistentvolumeclaim_status_phase` | 1/0 per PVC phase label |
| `kube_persistentvolumeclaim_resource_requests_storage_bytes` | PVC requested storage |
| `kube_persistentvolumeclaim_access_mode` / `_info` / `_created` | PVC metadata |

KubeSense-derived: `pvc_usage_percent`, `pvc_usage_bytes`, `pvc_read_bytes_total`,
`pvc_write_bytes_total`, `pvc_reads_total`, `pvc_writes_total`,
`pvc_read_latency_summary`, `pvc_write_latency_summary`.

## Network

| Metric |
|---|
| `network_rx_bytes_total` |
| `network_connections_opened_total` |
| `network_connections_closed_total` |

## GPU (NVIDIA DCGM)

| Metric | Meaning |
|---|---|
| `DCGM_FI_DEV_GPU_UTIL` | GPU utilisation % |
| `DCGM_FI_DEV_GPU_TEMP` | GPU temperature |
| `DCGM_FI_DEV_FB_USED` | Framebuffer memory used |
| `DCGM_FI_DEV_SM_CLOCK` | SM clock |
| `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` | Tensor-pipe activity |

Names are case-sensitive and uppercase.

## JVM

| Metric | Meaning |
|---|---|
| `jvm_heap_memory`, `_init`, `_max`, `_committed` | Heap memory |
| `jvm_non_heap_memory`, `_init`, `_max`, `_committed` | Non-heap memory |
| `jvm_loaded_classes` | Loaded class count |
| `jvm_thread_count` | Thread count |
| `jvm_gc.major_collection_time` / `.minor_collection_time` | GC time |
| `jvm_gc.major_collection_count` / `.minor_collection_count` | GC count |
| `jvm_gc.major_collection_rate` / `.minor_collection_rate` | GC rate |
| `jvm_gc.old_gen_size`, `.eden_size`, `.survivor_size`, `.metaspace_size` | Generation sizes |

> [!NOTE]
> JVM GC and generation metrics contain **dots** in the metric name
> (`jvm_gc.major_collection_time`). A bare dotted name is not a valid PromQL identifier —
> select it with the `__name__` matcher:
> ```promql
> {__name__="jvm_gc.major_collection_time"}
> ```

## Docker

| Metric | Meaning |
|---|---|
| `container_spec_cpu_quota` | Container CPU quota |
| `container_spec_memory_limit_bytes` | Container memory limit |
