# SQL Recipes

Patterns that justify reaching for `execute-sql` over `analyze-*`. Every query assumes
`$__timeFilter(timestamp)` and `$__clusters` are present; the `from_time` / `to_time`
arguments supply the window.

Field names are catalog labels — see the [skill](../SKILL.md) for the full contract, and
remember traces use `duration_ms` (milliseconds), not `duration`.

## Ranking within a group

Top endpoint per service, rather than the global top-N `analyze-traces` gives you.

```sql
SELECT service, resource, calls, p95_ms FROM (
  SELECT service, resource, count(*) AS calls,
         quantile(0.95)(duration_ms) AS p95_ms,
         row_number() OVER (PARTITION BY service ORDER BY count(*) DESC) AS rn
  FROM traces
  WHERE $__timeFilter(timestamp) AND $__clusters AND role = 'server'
  GROUP BY service, resource
) WHERE rn <= 3 ORDER BY service, calls DESC
```

## Two conditions in one pass

`countIf` / `sumIf` / `quantileIf` compute several filtered aggregates over a single
scan — cheaper than two `analyze-*` calls, and directly comparable.

```sql
SELECT service,
       countIf(status = 'error') AS errors,
       count(*) AS total,
       round(100.0 * countIf(status = 'error') / count(*), 2) AS error_pct
FROM traces
WHERE $__timeFilter(timestamp) AND $__clusters
GROUP BY service HAVING total > 100 ORDER BY error_pct DESC
```

`analyze-telemetry` with a formula does the same for two whole queries; this is the
single-query form.

## Period-over-period comparison

Pass a window covering **both** periods, then split it with the scalar macros.

```sql
SELECT workload,
       countIf(timestamp >= $__toTime - INTERVAL 1 HOUR)  AS recent,
       countIf(timestamp <  $__fromTime + INTERVAL 1 HOUR) AS baseline
FROM logs
WHERE $__timeFilter(timestamp) AND $__clusters AND type = 'ERROR'
GROUP BY workload
HAVING recent > baseline * 2
ORDER BY recent DESC
```

## Latest row per entity

`argMax` picks the value at the maximum timestamp without a self-join.

```sql
SELECT instance,
       argMax(body, timestamp) AS last_message,
       max(timestamp) AS last_seen
FROM logs
WHERE $__timeFilter(timestamp) AND $__clusters AND type IN ('ERROR', 'FATAL')
GROUP BY instance ORDER BY last_seen DESC
```

## Bucketed trend with a derived rate

When the series you want is arithmetic over two aggregates per bucket.

```sql
SELECT toStartOfMinute(timestamp) AS bucket,
       count(*) AS calls,
       round(quantile(0.99)(duration_ms), 1) AS p99_ms,
       round(100.0 * countIf(status_code >= '500') / count(*), 2) AS pct_5xx
FROM traces
WHERE $__timeFilter(timestamp) AND $__clusters AND service = 'checkout'
GROUP BY bucket ORDER BY bucket
```

`status_code` is a **string** column — compare it as one, or wrap it in
`toUInt16OrNull()` for numeric ranges.

## Attribute breakdown

Attributes are strings and are never validated, so confirm the key with
`get-trace-or-log-fields` and treat an all-empty column as a wrong key.

```sql
SELECT @http.route AS route,
       count(*) AS calls,
       round(avg(toFloat64OrNull(@http.response_time_ms)), 1) AS avg_ms
FROM logs
WHERE $__timeFilter(timestamp) AND $__clusters AND @http.route != ''
GROUP BY route ORDER BY calls DESC LIMIT 50
```

## Cardinality check before a group-by

Cheap guard against grouping by something with a million values.

```sql
SELECT uniq(instance) AS pods, uniq(workload) AS workloads, count(*) AS rows
FROM logs
WHERE $__timeFilter(timestamp) AND $__clusters
```

## What SQL cannot do here

- **Join logs to traces.** They are separate tables; one statement cannot reach both. Run
  two queries and correlate, or use `analyze-telemetry`, which combines signals in one call.
- **Query metrics.** Metrics live in VictoriaMetrics, not ClickHouse — use
  `analyze-metrics` with PromQL.
- **Read more than 1000 rows** without an explicit `LIMIT`, and only ever as rows, not as
  a substitute for aggregating.
- **Write anything.** Execution is read-only.
