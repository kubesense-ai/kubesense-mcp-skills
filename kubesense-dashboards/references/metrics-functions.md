# Metrics builder functions

Every function a builder-mode metrics query can hold in `functions`, with its
stored `type`, its arguments and a verified example. The example PromQL is
what the Explorer renders for those arguments on a metric `m`.

## Stored shape

```json
{ "type": "rollup", "name": "quantile_over_time",
  "arguments": [ { "arg_name": "over", "arg_value": "5m" },
                 { "arg_name": "phi", "arg_value": 0.9 } ] }
```

- **`name` picks the function.** Write `type` from the table below; it must
  match the function.
- **`arguments` is a list of `{arg_name, arg_value}`,** in any order. Each
  `arg_name` must be one of that function's arguments.
- **Leave an argument out** to take its default. An optional argument that is
  left out is simply not rendered. For example, a rollup with no `over` lets
  the query engine pick the window.
- **`functions` is a pipeline:** each function applies to the result of the one
  before it.

## Argument kinds

| Kind | `arg_value` |
|---|---|
| number | a JSON number within the stated bounds |
| number list | `[0.5, 0.9, 0.99]` |
| window | a duration such as `"30s"`, `"15m"` or `"1h30m"`, or a macro: `"$__rate_interval"`, `"$__interval"`, `"$__time_filter"` |
| duration | a duration such as `"1m"` (the subquery step for `step`) |
| label name / text / regex | a string, written without quotes |
| label list | `["pod", "namespace"]` |
| list of pairs | `[["env", "prod"], ["team", "core"]]` |
| rollup-function names | `["min_over_time", "max_over_time"]` |
| `true` | a flag: present as `true` to switch it on, absent to leave it off |

Aggregates group with `by` **or** `without`, each a label list; set one, not
both. `limit` keeps only that many output series.

<!-- BEGIN GENERATED: scripts/sync-builder-functions.py -->

### Rollup (80)

| Function | `type` | Arguments | Example → PromQL |
|---|---|---|---|
| `absent_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "10m"}` → `absent_over_time(m[10m])` |
| `aggr_over_time` | `rollup` | `rollups`: rollup-function names, default `["min_over_time", "max_over_time"]`<br>`over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m", "rollups": ["min_over_time", "max_over_time", "rate"]}` → `aggr_over_time(("min_over_time", "max_over_time", "rate"), m[5m])` |
| `ascent_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `ascent_over_time(m[5m])` |
| `avg_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "30s"}` → `avg_over_time(m[30s])` |
| `changes` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"keep_metric_names": true, "over": "1h"}` → `changes(m[1h]) keep_metric_names` |
| `changes_prometheus` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `changes_prometheus(m[5m])` |
| `count_eq_over_time` | `rollup` | `over`: window, optional<br>`eq`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"eq": 0, "over": "5m"}` → `count_eq_over_time(m[5m], 0)` |
| `count_gt_over_time` | `rollup` | `over`: window, optional<br>`gt`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"gt": 100, "over": "5m"}` → `count_gt_over_time(m[5m], 100)` |
| `count_le_over_time` | `rollup` | `over`: window, optional<br>`le`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"le": 0, "over": "5m"}` → `count_le_over_time(m[5m], 0)` |
| `count_ne_over_time` | `rollup` | `over`: window, optional<br>`ne`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"ne": 0, "over": "5m"}` → `count_ne_over_time(m[5m], 0)` |
| `count_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `count_over_time(m[5m])` |
| `count_values_over_time` | `rollup` | `label`: label name, default `"value"`<br>`over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"label": "value", "over": "1h"}` → `count_values_over_time("value", m[1h])` |
| `decreases_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `decreases_over_time(m[5m])` |
| `default_rollup` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{}` → `default_rollup(m)` |
| `delta` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `delta(m[5m])` |
| `delta_prometheus` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` with `selectorModifiers: {"offset": "1h"}` → `delta_prometheus(m[5m] offset 1h)` |
| `deriv` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "10m"}` → `deriv(m[10m])` |
| `deriv_fast` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `deriv_fast(m[5m])` |
| `descent_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `descent_over_time(m[5m])` |
| `distinct_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `distinct_over_time(m[5m])` |
| `duration_over_time` | `rollup` | `over`: window, optional<br>`max_interval`: duration, default `"1m"`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"max_interval": "30s", "over": "1h"}` → `duration_over_time(m[1h], 30s)` |
| `first_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `first_over_time(m[5m])` |
| `geomean_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `geomean_over_time(m[5m])` |
| `histogram_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `histogram_over_time(m[5m])` |
| `hoeffding_bound_lower` | `rollup` | `phi`: number (0–1), default `0.95`<br>`over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h", "phi": 0.9}` → `hoeffding_bound_lower(0.9, m[1h])` |
| `hoeffding_bound_upper` | `rollup` | `phi`: number (0–1), default `0.95`<br>`over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h", "phi": 0.9}` → `hoeffding_bound_upper(0.9, m[1h])` |
| `holt_winters` | `rollup` | `over`: window, optional<br>`sf`: number (0–1), default `0.5`<br>`tf`: number (0–1), default `0.5`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h", "sf": 0.3, "tf": 0.1}` → `holt_winters(m[1h], 0.3, 0.1)` |
| `idelta` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `idelta(m[5m])` |
| `ideriv` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `ideriv(m[5m])` |
| `increase` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h"}` → `increase(m[1h])` |
| `increase_prometheus` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h", "step": "5m"}` → `increase_prometheus(m[1h:5m])` |
| `increase_pure` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `increase_pure(m[5m])` |
| `increases_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h"}` → `increases_over_time(m[1h])` |
| `integrate` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `integrate(m[5m])` |
| `irate` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1m"}` → `irate(m[1m])` |
| `lag` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{}` → `lag(m)` |
| `last_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `last_over_time(m[5m])` |
| `lifetime` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `lifetime(m[5m])` |
| `mad_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `mad_over_time(m[5m])` |
| `max_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | after `rate`: `{"over": "1h", "step": "1m"}` → `max_over_time(rate(m[5m])[1h:1m])` |
| `median_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `median_over_time(m[5m])` |
| `min_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `min_over_time(m[5m])` |
| `mode_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `mode_over_time(m[5m])` |
| `outlier_iqr_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `outlier_iqr_over_time(m[5m])` |
| `predict_linear` | `rollup` | `over`: window, optional<br>`t`: number, default `3600`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h", "t": 14400}` → `predict_linear(m[1h], 14400)` |
| `present_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "10m"}` → `present_over_time(m[10m])` |
| `quantile_over_time` | `rollup` | `over`: window, optional<br>`quantile`: number (0–1), default `0.95`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m", "quantile": 0.99}` → `quantile_over_time(0.99, m[5m])` |
| `quantiles_over_time` | `rollup` | `phi_label`: label name, default `"quantile"`<br>`phis`: number list, default `[0.5, 0.9, 0.99]`<br>`over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m", "phi_label": "phi", "phis": [0.5, 0.99]}` → `quantiles_over_time("phi", 0.5, 0.99, m[5m])` |
| `range_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h"}` → `range_over_time(m[1h])` |
| `rate` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `rate(m[5m])` |
| `rate_over_sum` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `rate_over_sum(m[5m])` |
| `rate_prometheus` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` with `selectorModifiers: {"at": "end()", "offset": "1h"}` → `rate_prometheus(m[5m] offset 1h @ end())` |
| `resets` | `range` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h"}` → `resets(m[1h])` |
| `rollup` | `rollup` | `over`: window, optional<br>`rollup`: `min` \| `max` \| `avg`, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m", "rollup": "max"}` → `rollup(m[5m], "max")` |
| `rollup_candlestick` | `rollup` | `over`: window, optional<br>`ohlc`: `open` \| `high` \| `low` \| `close`, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"ohlc": "close", "over": "1h"}` → `rollup_candlestick(m[1h], "close")` |
| `rollup_delta` | `rollup` | `over`: window, optional<br>`rollup`: `min` \| `max` \| `avg`, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `rollup_delta(m[5m])` |
| `rollup_deriv` | `rollup` | `over`: window, optional<br>`rollup`: `min` \| `max` \| `avg`, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `rollup_deriv(m[5m])` |
| `rollup_increase` | `rollup` | `over`: window, optional<br>`rollup`: `min` \| `max` \| `avg`, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `rollup_increase(m[5m])` |
| `rollup_rate` | `rollup` | `over`: window, optional<br>`rollup`: `min` \| `max` \| `avg`, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `rollup_rate(m[5m])` |
| `rollup_scrape_interval` | `rollup` | `over`: window, optional<br>`rollup`: `min` \| `max` \| `avg`, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `rollup_scrape_interval(m[5m])` |
| `scrape_interval` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"step": "1m"}` → `scrape_interval(m[:1m])` |
| `share_eq_over_time` | `rollup` | `over`: window, optional<br>`eq`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"eq": 0, "over": "5m"}` → `share_eq_over_time(m[5m], 0)` |
| `share_gt_over_time` | `rollup` | `over`: window, optional<br>`gt`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"gt": 0, "over": "1d"}` → `share_gt_over_time(m[1d], 0)` |
| `share_le_over_time` | `rollup` | `over`: window, optional<br>`le`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"le": 0.5, "over": "1d"}` → `share_le_over_time(m[1d], 0.5)` |
| `stale_samples_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `stale_samples_over_time(m[5m])` |
| `stddev_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h"}` → `stddev_over_time(m[1h])` |
| `stdvar_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h"}` → `stdvar_over_time(m[1h])` |
| `sum2_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `sum2_over_time(m[5m])` |
| `sum_eq_over_time` | `rollup` | `over`: window, optional<br>`eq`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"eq": 0, "over": "5m"}` → `sum_eq_over_time(m[5m], 0)` |
| `sum_gt_over_time` | `rollup` | `over`: window, optional<br>`gt`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"gt": 0, "over": "5m"}` → `sum_gt_over_time(m[5m], 0)` |
| `sum_le_over_time` | `rollup` | `over`: window, optional<br>`le`: number, default `0`<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"le": 0, "over": "5m"}` → `sum_le_over_time(m[5m], 0)` |
| `sum_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "1h"}` → `sum_over_time(m[1h])` |
| `tfirst_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `tfirst_over_time(m[5m])` |
| `timestamp` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `timestamp(m[5m])` |
| `timestamp_with_name` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `timestamp_with_name(m[5m])` |
| `tlast_change_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `tlast_change_over_time(m[5m])` |
| `tlast_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `tlast_over_time(m[5m])` |
| `tmax_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `tmax_over_time(m[5m])` |
| `tmin_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"over": "5m"}` → `tmin_over_time(m[5m])` |
| `zscore_over_time` | `rollup` | `over`: window, optional<br>`step`: duration, optional<br>`keep_metric_names`: `true`, optional | `{"keep_metric_names": true, "over": "1d"}` → `zscore_over_time(m[1d]) keep_metric_names` |

### Transform (81)

| Function | `type` | Arguments | Example → PromQL |
|---|---|---|---|
| `abs` | `transform` | `keep_metric_names`: `true`, optional | `{"keep_metric_names": true}` → `abs(m) keep_metric_names` |
| `absent` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `absent(m)` |
| `acos` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `acos(m)` |
| `acosh` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `acosh(m)` |
| `asin` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `asin(m)` |
| `asinh` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `asinh(m)` |
| `atan` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `atan(m)` |
| `atanh` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `atanh(m)` |
| `bitmap_and` | `transform` | `mask`: number (≥ 0, integer), default `1`<br>`keep_metric_names`: `true`, optional | `{"mask": 255}` → `bitmap_and(m, 255)` |
| `bitmap_or` | `transform` | `mask`: number (≥ 0, integer), default `1`<br>`keep_metric_names`: `true`, optional | `{"mask": 1}` → `bitmap_or(m, 1)` |
| `bitmap_xor` | `transform` | `mask`: number (≥ 0, integer), default `1`<br>`keep_metric_names`: `true`, optional | `{"mask": 3}` → `bitmap_xor(m, 3)` |
| `buckets_limit` | `transform` | `limit`: number (≥ 1, integer), default `10`<br>`keep_metric_names`: `true`, optional | `{"limit": 10}` → `buckets_limit(10, m)` |
| `ceil` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `ceil(m)` |
| `clamp` | `transform` | `min`: number, default `0`<br>`max`: number, default `0`<br>`keep_metric_names`: `true`, optional | `{"max": 100, "min": 0}` → `clamp(m, 0, 100)` |
| `clamp_max` | `transform` | `max`: number, default `0`<br>`keep_metric_names`: `true`, optional | `{"max": 100}` → `clamp_max(m, 100)` |
| `clamp_min` | `transform` | `min`: number, default `0`<br>`keep_metric_names`: `true`, optional | `{"min": 0}` → `clamp_min(m, 0)` |
| `cos` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `cos(m)` |
| `cosh` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `cosh(m)` |
| `day_of_month` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `day_of_month(m)` |
| `day_of_week` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `day_of_week(m)` |
| `day_of_year` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `day_of_year(m)` |
| `days_in_month` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `days_in_month(m)` |
| `deg` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `deg(m)` |
| `drop_empty_series` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `drop_empty_series(m)` |
| `exp` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `exp(m)` |
| `floor` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `floor(m)` |
| `histogram_avg` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `histogram_avg(m)` |
| `histogram_fraction` | `transform` | `lower_le`: number, default `0`<br>`upper_le`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"lower_le": 0.1, "upper_le": 0.5}` → `histogram_fraction(0.1, 0.5, m)` |
| `histogram_quantile` | `transform` | `quantile`: number (0–1), default `0.95`<br>`bounds_label`: label name, optional<br>`keep_metric_names`: `true`, optional | after `rate` → `sum`: `{"quantile": 0.95}` → `histogram_quantile(0.95, sum by (le) (rate(m[5m])))` |
| `histogram_quantiles` | `transform` | `phi_label`: label name, default `"quantile"`<br>`phis`: number list, default `[0.5, 0.9, 0.99]`<br>`keep_metric_names`: `true`, optional | `{"phi_label": "phi", "phis": [0.5, 0.9]}` → `histogram_quantiles("phi", 0.5, 0.9, m)` |
| `histogram_share` | `transform` | `le`: number, default `1`<br>`bounds_label`: label name, optional<br>`keep_metric_names`: `true`, optional | `{"bounds_label": "bounds", "le": 0.5}` → `histogram_share(0.5, m, "bounds")` |
| `histogram_stddev` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `histogram_stddev(m)` |
| `histogram_stdvar` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `histogram_stdvar(m)` |
| `hour` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `hour(m)` |
| `interpolate` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `interpolate(m)` |
| `keep_last_value` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `keep_last_value(m)` |
| `keep_next_value` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `keep_next_value(m)` |
| `limit_offset` | `transform` | `limit`: number (≥ 1, integer), default `10`<br>`offset`: number (≥ 0, integer), default `0`<br>`keep_metric_names`: `true`, optional | `{"limit": 10, "offset": 20}` → `limit_offset(10, 20, m)` |
| `ln` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `ln(m)` |
| `log10` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `log10(m)` |
| `log2` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `log2(m)` |
| `minute` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `minute(m)` |
| `month` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `month(m)` |
| `prometheus_buckets` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `prometheus_buckets(m)` |
| `rad` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `rad(m)` |
| `range_avg` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_avg(m)` |
| `range_first` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_first(m)` |
| `range_last` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_last(m)` |
| `range_linear_regression` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_linear_regression(m)` |
| `range_mad` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_mad(m)` |
| `range_max` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_max(m)` |
| `range_median` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_median(m)` |
| `range_min` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_min(m)` |
| `range_normalize` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_normalize(m)` |
| `range_quantile` | `transform` | `phi`: number (0–1), default `0.95`<br>`keep_metric_names`: `true`, optional | `{"phi": 0.5}` → `range_quantile(0.5, m)` |
| `range_stddev` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_stddev(m)` |
| `range_stdvar` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_stdvar(m)` |
| `range_sum` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_sum(m)` |
| `range_trim_outliers` | `transform` | `k`: number, default `3`<br>`keep_metric_names`: `true`, optional | `{"k": 3}` → `range_trim_outliers(3, m)` |
| `range_trim_spikes` | `transform` | `phi`: number (0–1), default `0.01`<br>`keep_metric_names`: `true`, optional | `{"phi": 0.05}` → `range_trim_spikes(0.05, m)` |
| `range_trim_zscore` | `transform` | `z`: number, default `3`<br>`keep_metric_names`: `true`, optional | `{"z": 2}` → `range_trim_zscore(2, m)` |
| `range_zscore` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `range_zscore(m)` |
| `remove_resets` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `remove_resets(m)` |
| `round` | `transform` | `to_nearest`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"to_nearest": 0.1}` → `round(m, 0.1)` |
| `running_avg` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `running_avg(m)` |
| `running_max` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `running_max(m)` |
| `running_min` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `running_min(m)` |
| `running_sum` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `running_sum(m)` |
| `scalar` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `scalar(m)` |
| `sgn` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `sgn(m)` |
| `sin` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `sin(m)` |
| `sinh` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `sinh(m)` |
| `smooth_exponential` | `transform` | `sf`: number (0–1), default `0.5`<br>`keep_metric_names`: `true`, optional | `{"sf": 0.2}` → `smooth_exponential(m, 0.2)` |
| `sort` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `sort(m)` |
| `sort_desc` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `sort_desc(m)` |
| `sqrt` | `transform` | `keep_metric_names`: `true`, optional | `{"keep_metric_names": true}` → `sqrt(m) keep_metric_names` |
| `tan` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `tan(m)` |
| `tanh` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `tanh(m)` |
| `ttf` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `ttf(m)` |
| `vector` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `vector(m)` |
| `year` | `transform` | `keep_metric_names`: `true`, optional | `{}` → `year(m)` |

### Label (22)

| Function | `type` | Arguments | Example → PromQL |
|---|---|---|---|
| `alias` | `label` | `name`: text, default `""` | `{"name": "requests"}` → `alias(m, "requests")` |
| `drop_common_labels` | `label` | none | `{}` → `drop_common_labels(m)` |
| `label_copy` | `label` | `pairs`: list of `[label, label]` pairs, default `[]` | `{"pairs": [["pod", "instance"]]}` → `label_copy(m, "pod", "instance")` |
| `label_del` | `label` | `labels`: label list, default `[]` | `{"labels": ["pod", "instance"]}` → `label_del(m, "pod", "instance")` |
| `label_graphite_group` | `label` | `group_nums`: number list, default `[0]` | `{"group_nums": [0, 2]}` → `label_graphite_group(m, 0, 2)` |
| `label_join` | `label` | `dst_label`: label name, default `""`<br>`separator`: text, default `"-"`<br>`src_labels`: label list, default `[]` | `{"dst_label": "target", "separator": ":", "src_labels": ["namespace", "pod"]}` → `label_join(m, "target", ":", "namespace", "pod")` |
| `label_keep` | `label` | `labels`: label list, default `[]` | `{"labels": ["job"]}` → `label_keep(m, "job")` |
| `label_lowercase` | `label` | `labels`: label list, default `[]` | `{"labels": ["method"]}` → `label_lowercase(m, "method")` |
| `label_map` | `label` | `label`: label name, default `""`<br>`value_pairs`: list of `[text, text]` pairs, default `[]` | `{"label": "code", "value_pairs": [["200", "ok"], ["500", "error"]]}` → `label_map(m, "code", "200", "ok", "500", "error")` |
| `label_match` | `label` | `label`: label name, default `""`<br>`regex`: regex, default `".*"` | `{"label": "pod", "regex": "api-.*"}` → `label_match(m, "pod", "api-.*")` |
| `label_mismatch` | `label` | `label`: label name, default `""`<br>`regex`: regex, default `".*"` | `{"label": "pod", "regex": "api-.*"}` → `label_mismatch(m, "pod", "api-.*")` |
| `label_move` | `label` | `pairs`: list of `[label, label]` pairs, default `[]` | `{"pairs": [["pod", "instance"]]}` → `label_move(m, "pod", "instance")` |
| `label_replace` | `label` | `dst_label`: label name, default `""`<br>`replacement`: text, default `"$1"`<br>`src_label`: label name, default `""`<br>`regex`: regex, default `"(.*)"` | `{"dst_label": "app", "regex": "(.*)-[a-z0-9]+", "replacement": "$1", "src_label": "pod"}` → `label_replace(m, "app", "$1", "pod", "(.*)-[a-z0-9]+")` |
| `label_set` | `label` | `label_values`: list of `[label, text]` pairs, default `[]` | `{"label_values": [["env", "prod"], ["team", "core"]]}` → `label_set(m, "env", "prod", "team", "core")` |
| `label_transform` | `label` | `label`: label name, default `""`<br>`regex`: regex, default `"(.*)"`<br>`replacement`: text, default `"$1"` | `{"label": "pod", "regex": "-", "replacement": "_"}` → `label_transform(m, "pod", "-", "_")` |
| `label_uppercase` | `label` | `labels`: label list, default `[]` | `{"labels": ["method"]}` → `label_uppercase(m, "method")` |
| `label_value` | `label` | `label`: label name, default `""` | `{"label": "le"}` → `label_value(m, "le")` |
| `labels_equal` | `label` | `labels`: label list, default `[]` | `{"labels": ["src", "dst"]}` → `labels_equal(m, "src", "dst")` |
| `sort_by_label` | `label` | `labels`: label list, default `[]` | `{"labels": ["pod"]}` → `sort_by_label(m, "pod")` |
| `sort_by_label_desc` | `label` | `labels`: label list, default `[]` | `{"labels": ["pod"]}` → `sort_by_label_desc(m, "pod")` |
| `sort_by_label_numeric` | `label` | `labels`: label list, default `[]` | `{"labels": ["code"]}` → `sort_by_label_numeric(m, "code")` |
| `sort_by_label_numeric_desc` | `label` | `labels`: label list, default `[]` | `{"labels": ["code"]}` → `sort_by_label_numeric_desc(m, "code")` |

### Aggregate (40)

| Function | `type` | Arguments | Example → PromQL |
|---|---|---|---|
| `No_Aggregations` (legacy) | `aggregations` | `by`: label list, default `[]` | `{"by": []}` → `m` |
| `any` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `any(m)` |
| `avg` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": [], "without": ["instance"]}` → `avg without (instance) (m)` |
| `bottom` (legacy) | `top_bottom` | `k`: number, default `5`<br>`by`: `max` \| `min` \| `avg` \| `median` \| `last`, default `"max"` | `{"by": "avg", "k": 3}` → `bottomk_avg(3, m)` |
| `bottomk` | `aggregations` | `k`: number, default `5`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 3}` → `bottomk(3, m)` |
| `bottomk_avg` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `bottomk_avg(5, m)` |
| `bottomk_last` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `bottomk_last(5, m)` |
| `bottomk_max` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `bottomk_max(5, m)` |
| `bottomk_median` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `bottomk_median(5, m)` |
| `bottomk_min` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["namespace"], "k": 5}` → `bottomk_min by (namespace) (5, m)` |
| `count` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["namespace"]}` → `count by (namespace) (m)` |
| `count_values` | `aggregations` | `label`: label name, default `"value"`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": [], "label": "version"}` → `count_values("version", m)` |
| `distinct` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `distinct(m)` |
| `geomean` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `geomean(m)` |
| `group` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["pod"]}` → `group by (pod) (m)` |
| `histogram` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `histogram(m)` |
| `limitk` | `aggregations` | `k`: number, default `5`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["job"], "k": 2}` → `limitk by (job) (2, m)` |
| `mad` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `mad(m)` |
| `max` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["job"], "limit": 3}` → `max by (job) (m) limit 3` |
| `median` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `median(m)` |
| `min` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": []}` → `min(m)` |
| `mode` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `mode(m)` |
| `outliers_iqr` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `outliers_iqr(m)` |
| `outliers_mad` | `aggregations` | `tolerance`: number, default `3`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"tolerance": 2.5}` → `outliers_mad(2.5, m)` |
| `outliersk` | `aggregations` | `k`: number, default `5`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 2}` → `outliersk(2, m)` |
| `quantile` | `aggregations` | `phi`: number (0–1), default `0.95`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["job"], "phi": 0.9}` → `quantile by (job) (0.9, m)` |
| `quantiles` | `aggregations` | `phi_label`: label name, default `"quantile"`<br>`phis`: number list, default `[0.5, 0.9, 0.99]`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"phi_label": "phi", "phis": [0.5, 0.9]}` → `quantiles("phi", 0.5, 0.9, m)` |
| `share` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["le"]}` → `share by (le) (m)` |
| `stddev` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["job"]}` → `stddev by (job) (m)` |
| `stdvar` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["job"]}` → `stdvar by (job) (m)` |
| `sum` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": ["job"]}` → `sum by (job) (m)` |
| `sum2` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"by": []}` with `selectorModifiers: {"at": "end()"}` → `sum2(m @ end())` |
| `top` (legacy) | `top_bottom` | `k`: number, default `5`<br>`by`: `max` \| `min` \| `avg` \| `median` \| `last`, default `"max"` | `{"by": "max", "k": 5}` → `topk_max(5, m)` |
| `topk` | `aggregations` | `k`: number, default `5`<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 3}` → `topk(3, m)` |
| `topk_avg` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `topk_avg(5, m)` |
| `topk_last` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `topk_last(5, m)` |
| `topk_max` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5, "other": "pod=other"}` → `topk_max(5, m, "pod=other")` |
| `topk_median` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `topk_median(5, m)` |
| `topk_min` | `aggregations` | `k`: number, default `5`<br>`other`: text, optional<br>`by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{"k": 5}` → `topk_min(5, m)` |
| `zscore` | `aggregations` | `by`: label list, default `[]`<br>`without`: label list, optional<br>`limit`: number (≥ 1, integer), optional | `{}` → `zscore(m)` |

### Operator (15)

| Function | `type` | Arguments | Example → PromQL |
|---|---|---|---|
| `add` | `arithmetic` | `value`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"value": 1}` → `m + 1` |
| `default` | `operator` | `value`: number, default `0`<br>`keep_metric_names`: `true`, optional | `{"value": 0}` with `selectorModifiers: {"offset": "1d"}` → `m offset 1d default 0` |
| `divide` | `arithmetic` | `value`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"keep_metric_names": true, "value": 1024}` → `(m / 1024) keep_metric_names` |
| `equal` | `comparison` | `to`: number, default `0` (also `than`)<br>`bool`: `true`, optional<br>`keep_metric_names`: `true`, optional | `{"to": 0}` → `m == 0` |
| `greater` | `comparison` | `than`: number, default `0` (also `to`)<br>`bool`: `true`, optional<br>`keep_metric_names`: `true`, optional | `{"than": 0.5}` → `m > 0.5` |
| `greater_than_or_equal` | `comparison` | `to`: number, default `0` (also `than`)<br>`bool`: `true`, optional<br>`keep_metric_names`: `true`, optional | `{"to": 1}` → `m >= 1` |
| `if` | `operator` | `value`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"value": 1}` → `m if 1` |
| `ifnot` | `operator` | `value`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"value": 1}` → `m ifnot 1` |
| `less_than_or_equal` | `comparison` | `to`: number, default `0` (also `than`)<br>`bool`: `true`, optional<br>`keep_metric_names`: `true`, optional | `{"bool": true, "keep_metric_names": true, "to": 1}` → `(m <= bool 1) keep_metric_names` |
| `lesser` | `comparison` | `than`: number, default `0` (also `to`)<br>`bool`: `true`, optional<br>`keep_metric_names`: `true`, optional | `{"bool": true, "than": 100}` → `m < bool 100` |
| `modulo` | `arithmetic` | `value`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"value": 60}` → `m % 60` |
| `multiply` | `arithmetic` | `value`: number, default `100`<br>`keep_metric_names`: `true`, optional | after `greater`: `{"value": 100}` → `(m > 5) * 100` |
| `not_equal` | `comparison` | `to`: number, default `0` (also `than`)<br>`bool`: `true`, optional<br>`keep_metric_names`: `true`, optional | `{"to": 0}` → `m != 0` |
| `power` | `arithmetic` | `value`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"value": 2}` → `m ^ 2` |
| `subtract` | `arithmetic` | `value`: number, default `1`<br>`keep_metric_names`: `true`, optional | `{"value": 1}` → `m - 1` |

<!-- END GENERATED -->
