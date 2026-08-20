# KubeSense Cloud Resource Metric Catalog

Metrics KubeSense pulls from cloud providers' own monitoring APIs — AWS CloudWatch,
Google Cloud Monitoring, Azure Monitor, the MongoDB Atlas Administration API, the
Confluent Cloud Metrics API, and Kong. They land in the same VictoriaMetrics instance
as the Kubernetes metrics, but under a **completely different naming and label
convention**, so nothing in the main catalog transfers.

Source of truth: `kubecol/controller/db/victoriametrics/vm_writer.go` (the label set)
and `kubecol/controller/cloud/*` (the metric definitions).

---

## One metric name for every cloud datapoint

> [!IMPORTANT]
> Every cloud metric — all providers, all resource types — is written as a single
> Prometheus series name:
>
> ```
> kubesense_cloud_resource_metric
> ```
>
> The provider's own metric name is a **label value** (`metric_name`), not part of the
> series name. There is no `aws_ec2_cpuutilization` and no
> `azure_vm_percentage_cpu` — searching for one returns nothing.

```promql
kubesense_cloud_resource_metric{provider="aws",resource_type="Ec2Instance",metric_name="CPUUtilization"}
```

## The label contract

Six labels are emitted on every row, followed by any collector dimensions.

| Label | Meaning | Example |
|---|---|---|
| `provider` | Which integration produced it | `aws`, `gcp`, `azure`, `mongodbatlas`, `confluent`, `kong` |
| `account_id` | The registered account/subscription/org | AWS account id, Azure subscription id, GCP project, Atlas org id |
| `resource_id` | KubeSense's id for the resource — joins to the entity | `i-0abc…`, an ARN-derived id, `lkc-1234/orders` |
| `resource_type` | Resource kind (the table below) | `Ec2Instance`, `AzureVm`, `AtlasCluster` |
| `metric_name` | The provider-side metric name | `CPUUtilization`, `Percentage CPU`, `cpu_utilization` |
| `unit` | Unit string from the metric definition | `Percent`, `Bytes`, `Count`, `Seconds`, `ms` |

Extra labels are the collector's dimensions. `region` is present on AWS, GCP and Azure
rows; the rest vary by provider (see the provider sections). A dimension whose key
collides with one of the six reserved names above is **dropped** to keep the line
valid — so `resource_type` always carries the KubeSense kind, never a provider's own
type string.

There is no `clusterId`, no `namespace`, no `pod`. Cloud metrics live outside the
Kubernetes label namespace entirely; a selector copied from a kube-state-metrics query
matches nothing here.

## Discovery

`get-available-metrics` and `get-metric-labels` are the wrong tools for cloud metrics:
the first returns one name (`kubesense_cloud_resource_metric`) no matter how many
thousand cloud series exist, and the second returns label *names* only. Everything
useful is in the label **values**, which you read with `analyze-metrics` and
`query_type: "instant"`.

```promql
# What providers are connected?
count by (provider) (kubesense_cloud_resource_metric)

# What resource types does one provider emit?
count by (resource_type) (kubesense_cloud_resource_metric{provider="aws"})

# What metrics exist for one resource type?  <- the key discovery step
count by (metric_name, unit) (kubesense_cloud_resource_metric{resource_type="RdsInstance"})

# Which resources of that type are reporting?
count by (resource_id) (kubesense_cloud_resource_metric{resource_type="RdsInstance"})

# What dimensions does this family carry?
count by (region) (kubesense_cloud_resource_metric{provider="aws",resource_type="S3Bucket"})
```

Run the `count by (metric_name, ...)` query before writing a real query. The tables
below say what KubeSense *asks* each provider for; what a given account actually
publishes depends on its resources and on optional features (Container Insights,
RDS Enhanced Monitoring / Performance Insights, Atlas Search, the Kong Prometheus
plugin). A metric that is defined but unpublished is simply absent.

## Query rules

**1. These are gauges. Never `rate()` them.**
The provider's aggregation is already applied at collection time — CloudWatch's
`Sum`/`Average` statistic over the period, Cloud Monitoring's aligner, Azure Monitor's
aggregation. A `Sum` metric such as `RequestCount` is *already* the count for its
5-minute bucket, so `rate(kubesense_cloud_resource_metric{...}[5m])` divides a
pre-summed value by the window and yields a meaningless number. Use the raw value, or
`sum_over_time` / `avg_over_time` / `max_over_time` to roll up across buckets.

**2. Always pair `metric_name` with `resource_type`.**
Metric names collide hard across services: `CPUUtilization` exists on `Ec2Instance`,
`RdsInstance`, `EcsCluster`, `EcsService`, `ElastiCacheCluster`, `DocumentDbCluster`,
`NeptuneCluster`, `OpenSearchDomain` and `RedshiftCluster`. Selecting on
`metric_name` alone silently mixes nine services into one aggregate.

```promql
avg by (resource_id) (kubesense_cloud_resource_metric{
  provider="aws", resource_type="Ec2Instance", metric_name="CPUUtilization"})
```

**3. Azure metric names contain spaces and slashes.**
`Percentage CPU`, `Network In Total`, `OS Disk Read Bytes/sec`. They are legal label
values, but must be matched exactly and quoted; a regex match needs the metavalues
escaped. AWS names are PascalCase with occasional dots (`GetRecords.IteratorAgeMilliseconds`,
`ClusterStatus.red`); GCP and most Azure PaaS names are snake_case; Atlas is
SCREAMING_SNAKE; Confluent is a slashed path; Kong is dotted.

**4. Do not filter on `unit`.**
It is descriptive, not normalised — `Count` vs `count`, `Milliseconds` vs `ms` — and it
is part of the series identity, so if a definition's unit is ever corrected the series
forks. Read it off the result to label a chart; never put it in a selector.

**5. Freshness: a 5-minute tick with a bounded forward-fill.**
Cloud APIs stamp datapoints with the provider's own bucket time and publish minutes
late, so the newest real sample is typically 5–10 minutes old on arrival. The collector
appends a now-stamped copy of each series' newest sample when it is between 1 and 15
minutes stale, which is what makes instant queries work. Past 15 minutes the copy stops,
so a deleted or stopped resource goes absent rather than flatlining forever.
Consequences:

- An instant query is reliable; it is reading the forward-filled copy.
- A resource silent for >15 min disappears from instant queries. That is real signal,
  not a gap — check the resource exists before reporting it as down.
- Genuinely daily series (`BucketSizeBytes`, `NumberOfObjects` on S3, fetched on a 48h
  lookback) are left alone by the forward-fill. Query them over a multi-day range.
- Keep `rate`/`_over_time` windows at or above 10m; the native resolution is 5m and the
  auto-computed step on a short window will produce gaps.

**6. Scope every query.**
`kubesense_cloud_resource_metric` with no matchers selects every cloud series in the
deployment. Always pin at least `provider` + `resource_type`, and `account_id` when more
than one account is enrolled.

---

## AWS

`provider="aws"`. Collected from CloudWatch (`GetMetricData`) at a 300s period, plus RDS
Performance Insights. Dimensions: `region` always; plus readable grouping keys on some
types (`target_group`, `storage_type` and `filter_id` on S3, `operation` on DynamoDB).
`account_id` is the AWS account id.

> [!WARNING]
> Several CloudWatch definition sets **roll up onto a parent resource type** — the
> metrics exist, but not under the name you would guess:
>
> | These metrics… | are emitted with `resource_type` |
> |---|---|
> | HTTP API + WebSocket API Gateway | `ApiGatewayApi` |
> | Network LB, Classic LB | `LoadBalancer` |
> | NLB target-group health | `LoadBalancerTargetGroup` |
> | MSK per-broker | `MskCluster` |
> | DynamoDB per-operation | `DynamoDbTable` |
> | EBS Nitro-only latency/IOPS | `EbsVolume` |
> | Redshift query latency | `RedshiftCluster` |
> | RDS Performance Insights (`db.*`, `os.*`) | `RdsInstance` |
>
> There is no `resource_type="PerformanceInsights"`, no `"NetworkLoadBalancer"`, and no
> `"MskBroker"` in VictoriaMetrics.

| `resource_type` | Core metrics (Expanded tier adds more) |
|---|---|
| `Ec2Instance` | `CPUUtilization`, `NetworkIn`, `NetworkOut`, `DiskReadBytes`, `DiskWriteBytes` |
| `EbsVolume` | `VolumeReadBytes`, `VolumeWriteBytes`, `VolumeReadOps`, `VolumeWriteOps`; Nitro adds `VolumeAvgReadLatency`, `VolumeAvgWriteLatency`, `VolumeAvgIOPS`, `VolumeAvgThroughput`, `VolumeIOPSExceededCheck`, `VolumeThroughputExceededCheck`, `VolumeStalledIOCheck` |
| `AutoScalingGroup` | `GroupMinSize`, `GroupMaxSize`, `GroupDesiredCapacity`, `GroupInServiceInstances`, `GroupPendingInstances`, `GroupStandbyInstances`, `GroupTerminatingInstances`, `GroupTotalInstances` |
| `LoadBalancer` | ALB: `RequestCount`, `TargetResponseTime`, `HTTPCode_Target_4XX_Count`, `HTTPCode_Target_5XX_Count`. NLB: `ActiveFlowCount`, `NewFlowCount`, `ProcessedBytes`, `TCP_ELB_Reset_Count`, `TCP_Target_Reset_Count`. Classic: `RequestCount`, `Latency`, `HTTPCode_ELB_5XX`, `HTTPCode_Backend_5XX`, `HealthyHostCount`, `UnHealthyHostCount` |
| `LoadBalancerTargetGroup` | `HealthyHostCount`, `UnHealthyHostCount`, `RequestCountPerTarget` |
| `RdsInstance` | `CPUUtilization`, `FreeStorageSpace`, `DatabaseConnections`, `FreeableMemory`; plus Performance Insights `db.Transactions.*`, `db.SQL.*`, `db.state.*`, `db.IO.*`, `db.Cache.*`, `db.Concurrency.deadlocks.avg`, `os.cpuUtilization.*`, `os.memory.*`, `os.network.*`, `os.loadAverageMinute.*`, `os.tasks.*`, `os.swap.*` |
| `RdsCluster` | `VolumeBytesUsed`, `VolumeReadIOPs`, `VolumeWriteIOPs` |
| `DocumentDbCluster` | `CPUUtilization`, `DatabaseConnections`, `FreeableMemory`, `VolumeBytesUsed` |
| `NeptuneCluster` | `CPUUtilization`, `GremlinWebSocketOpenConnections`, `FreeableMemory`, `GremlinRequestsPerSec` |
| `RedshiftCluster` | `CPUUtilization`, `DatabaseConnections`, `HealthStatus`, `PercentageDiskSpaceUsed`; plus query-latency metrics |
| `ElastiCacheCluster` | `CPUUtilization`, `CurrConnections`, `CacheHits`, `CacheMisses` |
| `DynamoDbTable` | `ConsumedReadCapacityUnits`, `ConsumedWriteCapacityUnits`, `ThrottledRequests`; per-operation adds `SuccessfulRequestLatency`, `SystemErrors`, `ReturnedItemCount` |
| `OpenSearchDomain` | `CPUUtilization`, `JVMMemoryPressure`, `ClusterStatus.red`, `ClusterStatus.yellow`, `SearchLatency`, `IndexingLatency` |
| `LambdaFunction` | `Invocations`, `Errors`, `Duration`, `Throttles` |
| `EcsCluster` | `CPUUtilization`, `MemoryUtilization`, `ContainerInstanceCount`, `TaskCount`, `ServiceCount` |
| `EcsService` | `CPUUtilization`, `MemoryUtilization` |
| `EcsTaskDefinition` | `CpuUtilized`, `MemoryUtilized` (dimensioned by task-definition *family*, not revision) |
| `EcsContainer` | `ContainerCpuUtilization`, `ContainerMemoryUtilization`, `ContainerCpuUtilized`, `ContainerMemoryUtilized`, `ContainerNetworkRxBytes`, `ContainerNetworkTxBytes`, `ContainerStorageReadBytes`, `ContainerStorageWriteBytes`, `RestartCount`, `UnHealthyContainerHealthStatus` |
| `EksCluster` | `cluster_node_count`, `cluster_failed_node_count`, `pod_cpu_utilization`, `pod_memory_utilization` |
| `S3Bucket` | `BucketSizeBytes`, `NumberOfObjects` (daily; `BucketSizeBytes` is split by a `storage_type` dimension) |
| `SqsQueue` | `NumberOfMessagesSent`, `ApproximateNumberOfMessagesVisible`, `NumberOfMessagesDeleted` |
| `SnsTopic` | `NumberOfMessagesPublished`, `NumberOfNotificationsDelivered`, `NumberOfNotificationsFailed` |
| `EventBridgeBus` | `Invocations`, `FailedInvocations`, `MatchedEvents`, `TriggeredRules` |
| `KinesisStream` | `GetRecords.IteratorAgeMilliseconds`, `IncomingRecords`, `IncomingBytes` |
| `FirehoseStream` | `IncomingRecords`, `IncomingBytes`, `DeliveryToS3.Records`, `DeliveryToS3.Success` |
| `MskCluster` | Cluster: `ActiveControllerCount`, `OfflinePartitionsCount`, `GlobalPartitionCount`, `GlobalTopicCount`. Broker: `CpuUser`, `CpuSystem`, `CpuIdle`, `MemoryUsed`, `KafkaDataLogsDiskUsed`, `BytesInPerSec`, `BytesOutPerSec`, `MessagesInPerSec`, `ConnectionCount`, `UnderReplicatedPartitions` |
| `ApiGatewayApi` | REST: `Count`, `4XXError`, `5XXError`, `Latency`, `IntegrationLatency`. HTTP: `Count`, `4xx`, `5xx`, `Latency`. WebSocket: `ConnectCount`, `MessageCount`, `ClientError`, `ExecutionError`, `IntegrationError` |
| `CloudFrontDistribution` | `Requests`, `BytesDownloaded`, `BytesUploaded`, `4xxErrorRate`, `5xxErrorRate`, `TotalErrorRate` |
| `Route53HealthCheck` | `HealthCheckStatus`, `HealthCheckPercentageHealthy` |
| `Route53HostedZone` | `DNSQueries` |
| `WafWebAcl` | `AllowedRequests`, `BlockedRequests`, `CountedRequests`, `PassedRequests` |
| `TransitGateway` | `BytesIn`, `BytesOut`, `PacketsIn`, `PacketsOut`, `PacketDropCountBlackhole` |
| `StepFunctionsStateMachine` | `ExecutionsStarted`, `ExecutionsSucceeded`, `ExecutionsFailed`, `ExecutionsTimedOut`, `ExecutionTime` |
| `SageMakerEndpoint` | `Invocations`, `InvocationsPerInstance`, `ModelLatency`, `OverheadLatency`, `Invocation4XXErrors`, `Invocation5XXErrors`, `InvocationModelErrors` |

EKS and ECS cluster/container metrics come from the `ECS/ContainerInsights` and
`ContainerInsights` namespaces — absent unless Container Insights is enabled on the
cluster. `db.*` / `os.*` need Performance Insights (and Enhanced Monitoring for `os.*`)
on the RDS instance.

## GCP

`provider="gcp"`. Collected from Cloud Monitoring. `metric_name` is a **short friendly
name**, not the full metric type — `cpu_utilization`, not
`compute.googleapis.com/instance/cpu/utilization`. Dimensions: `region`, plus any
metric labels the definition keeps. `account_id` is the project.

| `resource_type` | Core metrics |
|---|---|
| `GceInstance` | `cpu_utilization`, `network_received_bytes`, `network_sent_bytes`, `disk_read_bytes`, `disk_write_bytes` |
| `GkeCluster` | `node_cpu_allocatable_utilization`, `node_memory_allocatable_utilization` |
| `CloudSql` | `cpu_utilization`, `memory_utilization`, `disk_utilization` |
| `AlloyDbCluster` | `memory_utilization`, `postgres_connections`, `storage_used_bytes` |
| `SpannerInstance` | `cpu_utilization`, `storage_used_bytes`, `session_count` |
| `BigtableInstance` | `cpu_load`, `disk_load`, `storage_utilization`, `server_request_count` |
| `FirestoreDatabase` | `document_read_count`, `document_write_count`, `document_delete_count` |
| `BigQueryDataset` | `stored_bytes`, `table_count` |
| `GcsBucket` | `total_bytes`, `object_count` |
| `FilestoreInstance` | `used_bytes_percent`, `write_bytes`, `read_bytes` |
| `CloudRunService` | `request_count`, `request_latencies_p99`, `instance_count` |
| `CloudRunJob` | `job_completed_executions`, `job_completed_task_attempts` |
| `CloudFunction` | `execution_count`, `execution_times_p99`, `user_memory_bytes_p99` |
| `AppEngineApp` | `http_response_count`, `http_response_latencies_p99`, `cpu_usage`, `memory_usage` |
| `PubSubTopic` | `send_message_operation_count`, `send_request_count`, `byte_cost` |
| `PubSubSubscription` | `sent_message_count`, `ack_message_count`, `oldest_unacked_message_age`, `num_undelivered_messages` |
| `CloudTasksQueue` | `queue_depth`, `task_attempt_count`, `api_request_count` |
| `ManagedKafkaCluster` | `cpu_utilization`, `memory_utilization` |
| `MemorystoreRedis` | `memory_usage_ratio`, `connected_clients`, `cache_hit_ratio` |
| `MemorystoreMemcached` | `cpu_utilization`, `memory_utilization`, `hit_ratio`, `operation_count` |
| `GceHttpsLb` | `request_count`, `total_latencies_p99`, `response_bytes_count`, `backend_request_count` |
| `GceInternalLb` | `egress_bytes`, `ingress_bytes`, `egress_packets` |
| `GceNetworkLb` | `egress_bytes`, `ingress_bytes`, `egress_packets` |
| `GceTcpSslProxyLb` | `open_connections`, `egress_bytes`, `ingress_bytes` |
| `DataflowJob` | `is_failed`, `system_lag`, `elapsed_time` |
| `DataprocCluster` | `hdfs_storage_utilization`, `job_running_count` |
| `ComposerEnvironment` | `environment_healthy`, `unfinished_task_instances`, `dag_processing_processes` |

## Azure

`provider="azure"`. Collected from Azure Monitor. `account_id` is the subscription id;
the only dimension is `region`.

> [!NOTE]
> Azure IaaS metric names are **space-separated title case** (`Percentage CPU`), while
> Azure PaaS/database names are snake_case (`cpu_percent`). Both are exact-match label
> values.

| `resource_type` | Core metrics |
|---|---|
| `AzureVm`, `AzureVmScaleSet` | `Percentage CPU`, `Network In Total`, `Network Out Total`, `Disk Read Bytes`, `Disk Write Bytes` |
| `AksCluster` | `apiserver_cpu_usage_percentage`, `apiserver_memory_usage_percentage`, `etcd_cpu_usage_percentage`, `etcd_memory_usage_percentage` |
| `AzureSql` | `cpu_percent`, `storage_percent`, `connection_failed`, `blocked_by_firewall` |
| `AzureSqlDatabase` | `cpu_percent`, `physical_data_read_percent`, `dtu_consumption_percent`, `storage_percent` |
| `AzureSqlElasticPool` | `cpu_percent`, `dtu_consumption_percent`, `storage_percent`, `workers_percent` |
| `AzureSqlManagedInstance` | `avg_cpu_percent`, `storage_space_used_mb`, `reserved_storage_mb`, `io_bytes_read`, `io_bytes_written`, `io_requests` |
| `AzureDbMySql`, `AzureDbPostgreSql` | `cpu_percent`, `memory_percent`, `io_consumption_percent`, `storage_percent`, `active_connections` |
| `AzureCosmosDb` | `TotalRequestUnits`, `TotalRequests`, `ServerSideLatency`, `NormalizedRUConsumption` |
| `AzureCosmosDbPostgreSql` | `cpu_percent`, `memory_percent`, `storage_percent`, `active_connections` |
| `AzureRedisCache` | `usedmemorypercentage`, `connectedclients`, `cachehits`, `cachemisses`, `percentProcessorTime` |
| `AzureAppService` | `Requests`, `Http5xx`, `Http2xx`, `CpuTime`, `MemoryWorkingSet` |
| `AzureAppServicePlan` | `CpuPercentage`, `MemoryPercentage`, `DiskQueueLength`, `HttpQueueLength`, `BytesReceived`, `BytesSent` |
| `AzureFunctionApp` | `FunctionExecutionCount`, `FunctionExecutionUnits`, `OnDemandFunctionExecutionCount`, `OnDemandFunctionExecutionUnits`, `MemoryWorkingSet`, `InstanceCount` |
| `AzureContainerApp` | `UsageNanoCores`, `WorkingSetBytes`, `Requests`, `RestartCount` |
| `AzureContainerAppEnvironment` | `NodeCount`, `IngressCpuPercentage`, `IngressMemoryPercentage`, `IngressUsageNanoCores`, `IngressUsageBytes`, `EnvCoresQuotaLimit`, `EnvCoresQuotaUtilization` |
| `AzureContainerInstance` | `CpuUsage`, `MemoryUsage`, `NetworkBytesReceivedPerSecond`, `NetworkBytesTransmittedPerSecond` |
| `AzureBlobStorage` | `Transactions`, `Ingress`, `Egress`, `SuccessE2ELatency` |
| `AzureApplicationGateway` | `Throughput`, `HealthyHostCount`, `UnhealthyHostCount`, `FailedRequests`, `ResponseStatus`, `TotalRequests` |
| `AzureLoadBalancer` | `ByteCount`, `PacketCount`, `SYNCount`, `SnatConnectionCount` |
| `AzureApiManagement` | `Requests`, `Capacity`, `Duration` |
| `EventHubsNamespace` | `IncomingMessages`, `OutgoingMessages`, `IncomingBytes`, `OutgoingBytes`, `ActiveConnections`, `ThrottledRequests` |
| `AzureServiceBus` | `IncomingMessages`, `OutgoingMessages`, `ActiveConnections`, `ThrottledRequests`, `ServerErrors`, `UserErrors` |
| `AzureEventGrid` | `PublishSuccessCount`, `PublishFailCount`, `DeliverySuccessCount`, `DeliveryAttemptFailCount`, `MatchedEventCount` |
| `AzureLogicApp` | `RunsStarted`, `RunsCompleted`, `RunsSucceeded`, `RunsFailed`, `RunLatency` |
| `AzureDataFactory` | `PipelineSucceededRuns`, `PipelineFailedRuns`, `ActivitySucceededRuns`, `ActivityFailedRuns`, `TriggerSucceededRuns`, `TriggerFailedRuns` |
| `AzureKeyVault` | `ServiceApiHit`, `ServiceApiLatency`, `ServiceApiResult`, `Availability` |
| `AzureIotHub` | `connectedDeviceCount`, `totalDeviceCount`, `d2c.telemetry.ingress.success`, `d2c.telemetry.egress.success`, `c2d.commands.success` |
| `AzureVirtualNetwork` | `PingMeshAverageRoundtripMs`, `PingMeshProbesFailedPercent` |

## MongoDB Atlas

`provider="mongodbatlas"`, `account_id` = the Atlas organisation id. Measurement names
are SCREAMING_SNAKE, taken verbatim from the Administration API.

| `resource_type` | Scope |
|---|---|
| `AtlasCluster` | Cluster-level rollup of the process measurements |
| `AtlasNode` | Per-`mongod`/`mongos` process. **M10+ only** — shared tiers (M0/M2/M5) expose no per-process measurements |
| `AtlasDatabase` | Per-database `DATABASE_*` measurements |

Dimensions: `project_id`, `project_name`, `cluster`, `process`, `process_type`, and
`database` on `AtlasDatabase`. Disk measurements add a partition dimension.

Core measurements: `PROCESS_CPU_USER`, `SYSTEM_NORMALIZED_CPU_USER`, `MEMORY_RESIDENT`,
`COMPUTED_MEMORY`, `CACHE_USED_BYTES`, `CONNECTIONS`, `CONNECTIONS_PERCENT`,
`OPCOUNTER_QUERY`, `OPCOUNTER_INSERT`, `OPCOUNTER_UPDATE`, `OPCOUNTER_DELETE`,
`READS_OPS`, `WRITES_OPS`, `AVERAGE_READS_LATENCY`, `AVERAGE_WRITES_LATENCY`,
`OP_EXECUTION_TIME_READS`, `OP_EXECUTION_TIME_WRITES`, `READS_P99_VALUE`,
`WRITES_P99_VALUE`, `TICKETS_AVAILABLE_READS`, `TICKETS_AVAILABLE_WRITE`,
`QUERY_TARGETING_SCANNED_PER_RETURNED`, `OPLOG_REPLICATION_LAG_TIME`,
`NETWORK_BYTES_IN`, `NETWORK_BYTES_OUT`, `DISK_PARTITION_IOPS_TOTAL`,
`DISK_PARTITION_UTILIZATION`, `DISK_PARTITION_SPACE_PERCENT_USED`,
`DATABASE_DATA_SIZE`, `DATABASE_INDEX_SIZE`, `DATABASE_STORAGE_SIZE`.

The Expanded tier adds assertion counters, per-command latency percentiles, cache
detail, cursor counts and the `ASSERT_*` family. Atlas Search measurements
(`FTS_*`) are Expanded-only and need Atlas Search enabled on the cluster.

## Confluent Cloud

`provider="confluent"`, `account_id` = the Confluent org id. `metric_name` is the
Confluent Metrics API path, slashes and all.

| `resource_type` | Core metrics |
|---|---|
| `ConfluentCluster` | `io.confluent.kafka.server/active_connection_count`, `/cluster_load_percent`, `/partition_count`, `/received_bytes`, `/received_records`, `/request_count`, `/retained_bytes`, `/sent_bytes`, `/sent_records` |
| `ConfluentTopic` | `io.confluent.kafka.server/received_bytes`, `/sent_bytes`, `/received_records`, `/sent_records`, `/retained_bytes` |
| `ConfluentConsumerGroup` | `io.confluent.kafka.server/consumer_lag_offsets` |
| `ConfluentConnector` | `io.confluent.kafka.connect/connector_status`, `/connector_task_status`, `/dead_letter_queue_records`, `/received_bytes`, `/received_records`, `/records_lag_max`, `/sent_bytes`, `/sent_records` |
| `ConfluentKsqlDB` | `io.confluent.kafka.ksql/offsets_processed_total`, `/processing_errors_total`, `/query_restarts`, `/query_saturation`, `/storage_utilization`, `/streaming_unit_count` |
| `ConfluentSchemaRegistry` | `io.confluent.kafka.schema_registry/request_count`, `/schema_count`, `/schema_operations_count` |
| `ConfluentFlinkComputePool` | `io.confluent.flink/compute_pool_utilization/cfu_limit`, `/cfu_minutes_consumed`, `/current_cfus`, `io.confluent.flink/num_records_in`, `/num_records_in_errors`, `/num_records_out`, `/pending_records` |

Dimensions: `resource_id`, `resource_name`, `environment`; sub-entities add `topic` or
`consumer_group_id` and `cluster_id` (the parent `lkc-…`). Topic and consumer-group
series are **re-homed onto the sub-entity** — `resource_id` becomes
`<lkc-id>/<topic-or-group>`, not the cluster.

## Kong

`provider="kong"`, `account_id` = the org id. Metric names are dotted and every one is a
gauge, including the counters — Konnect analytics and the Prometheus plugin are both
sampled per window, not accumulated.

| `resource_type` | Core metrics |
|---|---|
| `KongCluster` | `kong.requests`, `kong.bandwidth_bytes`, `kong.latency_request`, `kong.latency_proxy`, `kong.latency_upstream` |
| `KongService` | `kong.service.request_count`, `kong.service.latency`, `kong.service.upstream_latency`, `kong.service.errors` |
| `KongRoute` | `kong.route.request_count`, `kong.route.latency` |
| `KongPlugin` | `kong.plugin.request_count`, `kong.plugin.latency` |
| `KongConsumer` | `kong.consumer.request_count` |

Expanded adds connection-state gauges, per-status-class counts (`kong.service.4xx`,
`.5xx`), Lua VM memory and `kong.database_reachable` on the cluster. Dimension:
`control_plane`. Self-managed gateways need the Prometheus plugin enabled; without it
nothing is published.

## What is *not* in VictoriaMetrics

Per-query database telemetry — GCP Cloud SQL **Query Insights** and AWS RDS
**Performance Insights top-N queries** — is too high-cardinality for a metric series
(one series per distinct SQL statement). It is ranked at collection time and written to
ClickHouse instead, reachable through the cloud query-insights API, not PromQL. Only
the aggregate PI counters (`db.*` / `os.*` on `RdsInstance`) live here.

## Worked examples

```promql
# Top 10 hottest EC2 instances right now  (query_type: "instant")
topk(10, kubesense_cloud_resource_metric{
  provider="aws", resource_type="Ec2Instance", metric_name="CPUUtilization"})

# ALB 5xx rate as a percentage of requests, per load balancer
sum by (resource_id) (kubesense_cloud_resource_metric{
    provider="aws", resource_type="LoadBalancer", metric_name="HTTPCode_Target_5XX_Count"})
  /
sum by (resource_id) (kubesense_cloud_resource_metric{
    provider="aws", resource_type="LoadBalancer", metric_name="RequestCount"}) * 100

# Lambda error ratio over the window
sum(sum_over_time(kubesense_cloud_resource_metric{
    provider="aws", resource_type="LambdaFunction", metric_name="Errors"}[1h]))
  /
sum(sum_over_time(kubesense_cloud_resource_metric{
    provider="aws", resource_type="LambdaFunction", metric_name="Invocations"}[1h])) * 100

# Azure VMs above 80% CPU  (note the space in the metric name)
kubesense_cloud_resource_metric{
  provider="azure", resource_type="AzureVm", metric_name="Percentage CPU"} > 80

# Atlas replica-set lag by node
max by (resource_id, cluster) (kubesense_cloud_resource_metric{
  provider="mongodbatlas", resource_type="AtlasNode",
  metric_name="OPLOG_REPLICATION_LAG_TIME"})

# Consumer-group lag across a Confluent cluster
sum by (consumer_group_id) (kubesense_cloud_resource_metric{
  provider="confluent", resource_type="ConfluentConsumerGroup",
  metric_name="io.confluent.kafka.server/consumer_lag_offsets"})

# S3 bucket size by storage class, over a week (daily series — needs a wide window)
max by (resource_id, storage_type) (kubesense_cloud_resource_metric{
  provider="aws", resource_type="S3Bucket", metric_name="BucketSizeBytes"})
```

## Rules

1. The metric name is always `kubesense_cloud_resource_metric`. The provider's metric
   name is the `metric_name` **label**.
2. Discover with `count by (metric_name, ...) (...)` through `analyze-metrics`;
   `get-available-metrics` cannot see into label values.
3. Never `rate()` a cloud metric — the provider's aggregation is already applied.
   Use the raw value or `*_over_time`.
4. Always pin `resource_type` alongside `metric_name`; names collide across services.
5. No `clusterId` / `namespace` / `pod` here. Selectors from Kubernetes metrics do not
   transfer.
6. Azure names contain spaces; quote and match them exactly.
7. Never filter on `unit`.
8. Metrics roll up onto parent types on AWS — no `PerformanceInsights`,
   `NetworkLoadBalancer`, `MskBroker`, `EbsVolumeNitro` or `DynamoDbTableOperation`
   resource types exist in the label.
9. A series silent for >15 minutes is genuinely absent, not zero — the forward-fill
   stops there deliberately.
10. Keep query windows ≥10m; native resolution is a 5-minute tick.
