# MetricsQL reference

`analyze-metrics` accepts **MetricsQL**: all of PromQL plus the syntax and
functions below. Look up a function here before using it. Many exist only in
MetricsQL, and several take their scalar argument before the series
(`quantile(0.9, q)`), not after.

## Syntax beyond PromQL

**Windows and steps**

- **The window is optional.** `rate(m)` is valid. The metrics store uses
  `max(step, scrape_interval)` for `rate` and `default_rollup`, and one step
  (`1i`) for every other rollup. In KubeSense, `$__rate_interval` (see the
  skill) is the explicit, predictable choice.
- **`i` is a step unit.** `rate(m[10i] offset 5i)` spans 10 steps, offset by 5.
- **Subqueries.** `max_over_time(rate(m[5m])[1h:30s])` runs the inner query every
  30s over the last hour. The step is optional (`[1h]` means `[1h:1i]`), and a
  rollup applied to anything other than a selector becomes a subquery by
  itself: `rate(sum(m))` runs as `rate(sum(m)[1i:1i])`.

**Modifiers**

- **`offset` and `@` go anywhere,** not just on a selector. Examples:
  `sum(foo) offset 24h`, `sum(foo) @ end()`, `foo @ (end() - 1h)`.
- **Aggregates take `by (...)` or `without (...)`,** before or after the
  arguments: `sum by (pod) (q)` or `sum(q) by (pod)`.
- **Aggregates take a trailing `limit N`,** which keeps only N output series:
  `sum(x) by (y) limit 3`.
- **Aggregates accept several queries:** `avg(q1, q2, q3)`.
- **`keep_metric_names`.** Functions and binary operators drop the metric name
  by default, which fails with `duplicate time series` when the input has
  several names. Append `keep_metric_names` to a rollup, transform or binary
  operator to keep them: `rate({__name__=~"foo|bar"}) keep_metric_names`.

**Binary operators**

- **`q1 default q2`** fills gaps in `q1` from `q2`. `sum(x) default 0` turns
  "no data" into 0.
- **`q1 if q2`** keeps `q1` only where `q2` has a value. **`q1 ifnot q2`**
  keeps `q1` only where `q2` has none.
- **Matching several constants:** `status_code == (300, 301, 304)`.
- **`group_left(*)` and `group_right(*)`** copy every label from the one side,
  and `prefix "ns_"` renames them:
  `kube_pod_info * on(namespace) group_left(*) prefix "ns_" kube_namespace_labels`.

**Selectors**

- **`or` inside the braces** selects either label set:
  `{env="prod",job="a" or env="dev",job="b"}`.
- **Match metric names by regex** with `{__name__=~"foo|bar"}`.

**Literals and templates**

- **Durations are numbers too:**
  - fractional durations work: `[1.5m]`, `offset 0.5d`
  - a bare number is seconds: `[300]` is `[5m]`
  - a duration can stand in arithmetic: `sum_over_time(m[1h]) / 1h`
- **Numeric suffixes:** `K`, `Ki`, `M`, `Mi`, `G`, `Gi`, `T` and `Ti`, as in
  `8K` or `1.2Mi`. Underscores are allowed: `1_000_000`.
- **`WITH` templates** name reusable subexpressions:
  `WITH (cpu = rate(container_cpu_usage_seconds_total{container!=""}[5m])) sum(cpu) by (namespace)`.
  String literals concatenate with `+` inside them.
- **Trailing commas** are allowed in every list.

## Functions

232 functions; the 77 marked ✓ also work in stock Prometheus.

### Rollup functions (80)

Take a series selector with a lookbehind window `[d]` and compute one value per series per step from the raw samples in that window.

| Signature | What it does | PromQL |
|---|---|---|
| `absent_over_time(series_selector[d])` | Returns 1 if the given lookbehind window `d` doesn't contain raw samples. | ✓ |
| `aggr_over_time(("rollup_func1", "rollup_func2", ...), series_selector[d])` | Calculates all the listed `rollup_func*` for raw samples on the given lookbehind window `d`. |  |
| `ascent_over_time(series_selector[d])` | Calculates ascent of raw sample values on the given lookbehind window `d`. |  |
| `avg_over_time(series_selector[d])` | Calculates the average value over raw samples on the given lookbehind window `d`. | ✓ |
| `changes(series_selector[d])` | Calculates the number of times the raw samples changed on the given lookbehind window `d`. | ✓ |
| `changes_prometheus(series_selector[d])` | Calculates the number of times the raw samples changed on the given lookbehind window `d`. | ✓ |
| `count_eq_over_time(series_selector[d], eq)` | Calculates the number of raw samples on the given lookbehind window `d`, which are equal to `eq`. |  |
| `count_gt_over_time(series_selector[d], gt)` | Calculates the number of raw samples on the given lookbehind window `d`, which are bigger than `gt`. |  |
| `count_le_over_time(series_selector[d], le)` | Calculates the number of raw samples on the given lookbehind window `d`, which don't exceed `le`. |  |
| `count_ne_over_time(series_selector[d], ne)` | Calculates the number of raw samples on the given lookbehind window `d`, which aren't equal to `ne`. |  |
| `count_over_time(series_selector[d])` | Calculates the number of raw samples on the given lookbehind window `d`. | ✓ |
| `count_values_over_time("label", series_selector[d])` | Counts the number of raw samples with the same value over the given lookbehind window and stores the counts in a time series with an additional `label`, which contains each initial value. |  |
| `decreases_over_time(series_selector[d])` | Calculates the number of raw sample value decreases over the given lookbehind window `d`. |  |
| `default_rollup(series_selector[d])` | Returns the last raw sample value on the given lookbehind window `d`. |  |
| `delta(series_selector[d])` | Calculates the difference between the last sample before the given lookbehind window `d` and the last sample at the given lookbehind window `d`. | ✓ |
| `delta_prometheus(series_selector[d])` | Calculates the difference between the first and the last samples at the given lookbehind window `d`. |  |
| `deriv(series_selector[d])` | Calculates per-second derivative over the given lookbehind window `d`. | ✓ |
| `deriv_fast(series_selector[d])` | Calculates per-second derivative using the first and the last raw samples on the given lookbehind window `d`. |  |
| `descent_over_time(series_selector[d])` | Calculates descent of raw sample values on the given lookbehind window `d`. |  |
| `distinct_over_time(series_selector[d])` | Returns the number of unique raw sample values on the given lookbehind window `d`. |  |
| `duration_over_time(series_selector[d], max_interval)` | Returns the duration in seconds when time series returned from the given series_selector were present over the given lookbehind window `d`. |  |
| `first_over_time(series_selector[d])` | Returns the first raw sample value on the given lookbehind window `d`. |  |
| `geomean_over_time(series_selector[d])` | Calculates geometric mean over raw samples on the given lookbehind window `d`. |  |
| `histogram_over_time(series_selector[d])` | Calculates a histogram (buckets labelled `vmrange`) over raw samples on the given lookbehind window `d`. |  |
| `hoeffding_bound_lower(phi, series_selector[d])` | Calculates lower Hoeffding bound for the given `phi` in the range `[0...1]`. |  |
| `hoeffding_bound_upper(phi, series_selector[d])` | Calculates upper Hoeffding bound for the given `phi` in the range `[0...1]`. |  |
| `holt_winters(series_selector[d], sf, tf)` | Calculates Holt-Winters value (aka double exponential smoothing) for raw samples over the given lookbehind window `d` using the given smoothing factor `sf` and the given trend factor `tf`. | ✓ |
| `idelta(series_selector[d])` | Calculates the difference between the last two raw samples on the given lookbehind window `d`. | ✓ |
| `ideriv(series_selector[d])` | Calculates the per-second derivative based on the last two raw samples over the given lookbehind window `d`. |  |
| `increase(series_selector[d])` | Calculates the increase over the given lookbehind window `d`. | ✓ |
| `increase_prometheus(series_selector[d])` | Calculates the increase over the given lookbehind window `d`. |  |
| `increase_pure(series_selector[d])` | Works the same as increase except of the following corner case - it assumes that counters always start from 0, while increase ignores the first value in a series if it is too big. |  |
| `increases_over_time(series_selector[d])` | Calculates the number of raw sample value increases over the given lookbehind window `d`. |  |
| `integrate(series_selector[d])` | Calculates the integral over raw samples on the given lookbehind window `d`. |  |
| `irate(series_selector[d])` | Calculates the "instant" per-second increase rate over the last two raw samples on the given lookbehind window `d`. | ✓ |
| `lag(series_selector[d])` | Returns the duration in seconds between the last sample on the given lookbehind window `d` and the timestamp of the current point. |  |
| `last_over_time(series_selector[d])` | Returns the last raw sample value on the given lookbehind window `d`. | ✓ |
| `lifetime(series_selector[d])` | Returns the duration in seconds between the last and the first sample on the given lookbehind window `d`. |  |
| `mad_over_time(series_selector[d])` | Calculates median absolute deviation over raw samples on the given lookbehind window `d`. |  |
| `max_over_time(series_selector[d])` | Calculates the maximum value over raw samples on the given lookbehind window `d`. | ✓ |
| `median_over_time(series_selector[d])` | Calculates median value over raw samples on the given lookbehind window `d`. |  |
| `min_over_time(series_selector[d])` | Calculates the minimum value over raw samples on the given lookbehind window `d`. | ✓ |
| `mode_over_time(series_selector[d])` | Calculates mode) for raw samples on the given lookbehind window `d`. |  |
| `outlier_iqr_over_time(series_selector[d])` | Returns the last sample on the given lookbehind window `d` if its value is either smaller than the `q25-1.5*iqr` or bigger than `q75+1.5*iqr` where:. |  |
| `predict_linear(series_selector[d], t)` | Calculates the value `t` seconds in the future using linear interpolation over raw samples on the given lookbehind window `d`. | ✓ |
| `present_over_time(series_selector[d])` | Returns 1 if there is at least a single raw sample on the given lookbehind window `d`. | ✓ |
| `quantile_over_time(phi, series_selector[d])` | Calculates `phi`-quantile over raw samples on the given lookbehind window `d`. | ✓ |
| `quantiles_over_time("phiLabel", phi1, ..., phiN, series_selector[d])` | Calculates `phi*`-quantiles over raw samples on the given lookbehind window `d`. |  |
| `range_over_time(series_selector[d])` | Calculates value range over raw samples on the given lookbehind window `d`. |  |
| `rate(series_selector[d])` | Calculates the average per-second increase rate over the given lookbehind window `d`. | ✓ |
| `rate_prometheus(series_selector[d])` | `rate_prometheus(series_selector[d])` {{% available_from "v1.120.0" %}} is a rollup function, which calculates the average per-second increase rate over the given lookbehind window `d`. |  |
| `rate_over_sum(series_selector[d])` | Calculates per-second rate over the sum of raw samples on the given lookbehind window `d`. |  |
| `resets(series_selector[d])` | Returns the number of counter resets over the given lookbehind window `d`. | ✓ |
| `rollup(series_selector[d])` | Calculates `min`, `max` and `avg` values for raw samples on the given lookbehind window `d` and returns them in time series with `rollup="min"`, `rollup="max"` and `rollup="avg"` additional labels. |  |
| `rollup_candlestick(series_selector[d])` | Calculates `open`, `high`, `low` and `close` values (aka OHLC) over raw samples on the given lookbehind window `d` and returns them in time series with `rollup="open"`, `rollup="high"`, `rollup="low"` and `rollup="close"` additional labels. |  |
| `rollup_delta(series_selector[d])` | Calculates differences between adjacent raw samples on the given lookbehind window `d` and returns `min`, `max` and `avg` values for the calculated differences and returns them in time series with `rollup="min"`, `rollup="max"` and `rollup="avg"` additional labels. |  |
| `rollup_deriv(series_selector[d])` | Calculates per-second derivatives for adjacent raw samples on the given lookbehind window `d` and returns `min`, `max` and `avg` values for the calculated per-second derivatives and returns them in time series with `rollup="min"`, `rollup="max"` and `rollup="avg"` additional labels. |  |
| `rollup_increase(series_selector[d])` | Calculates increases for adjacent raw samples on the given lookbehind window `d` and returns `min`, `max` and `avg` values for the calculated increases and returns them in time series with `rollup="min"`, `rollup="max"` and `rollup="avg"` additional labels. |  |
| `rollup_rate(series_selector[d])` | Calculates per-second change rates for adjacent raw samples on the given lookbehind window `d` and returns `min`, `max` and `avg` values for the calculated per-second change rates and returns them in time series with `rollup="min"`, `rollup="max"` and `rollup="avg"` additional labels. |  |
| `rollup_scrape_interval(series_selector[d])` | Calculates the interval in seconds between adjacent raw samples on the given lookbehind window `d` and returns `min`, `max` and `avg` values for the calculated interval and returns them in time series with `rollup="min"`, `rollup="max"` and `rollup="avg"` additional labels. |  |
| `scrape_interval(series_selector[d])` | Calculates the average interval in seconds between raw samples on the given lookbehind window `d`. |  |
| `share_gt_over_time(series_selector[d], gt)` | Returns share (in the range `[0...1]`) of raw samples on the given lookbehind window `d`, which are bigger than `gt`. |  |
| `share_le_over_time(series_selector[d], le)` | Returns share (in the range `[0...1]`) of raw samples on the given lookbehind window `d`, which are smaller or equal to `le`. |  |
| `share_eq_over_time(series_selector[d], eq)` | Returns share (in the range `[0...1]`) of raw samples on the given lookbehind window `d`, which are equal to `eq`. |  |
| `stale_samples_over_time(series_selector[d])` | Calculates the number of staleness markers on the given lookbehind window `d` per each time series matching the given series_selector. |  |
| `stddev_over_time(series_selector[d])` | Calculates standard deviation over raw samples on the given lookbehind window `d`. | ✓ |
| `stdvar_over_time(series_selector[d])` | Calculates standard variance over raw samples on the given lookbehind window `d`. | ✓ |
| `sum_eq_over_time(series_selector[d], eq)` | Calculates the sum of raw sample values equal to `eq` on the given lookbehind window `d`. |  |
| `sum_gt_over_time(series_selector[d], gt)` | Calculates the sum of raw sample values bigger than `gt` on the given lookbehind window `d`. |  |
| `sum_le_over_time(series_selector[d], le)` | Calculates the sum of raw sample values smaller or equal to `le` on the given lookbehind window `d`. |  |
| `sum_over_time(series_selector[d])` | Calculates the sum of raw sample values on the given lookbehind window `d`. | ✓ |
| `sum2_over_time(series_selector[d])` | Calculates the sum of squares for raw sample values on the given lookbehind window `d`. |  |
| `timestamp(series_selector[d])` | Returns the timestamp in seconds with millisecond precision for the last raw sample on the given lookbehind window `d`. | ✓ |
| `timestamp_with_name(series_selector[d])` | Returns the timestamp in seconds with millisecond precision for the last raw sample on the given lookbehind window `d`. |  |
| `tfirst_over_time(series_selector[d])` | Returns the timestamp in seconds with millisecond precision for the first raw sample on the given lookbehind window `d`. |  |
| `tlast_change_over_time(series_selector[d])` | Returns the timestamp in seconds with millisecond precision for the last change on the given lookbehind window `d`. |  |
| `tlast_over_time(series_selector[d])` | Is an alias for timestamp. |  |
| `tmax_over_time(series_selector[d])` | Returns the timestamp in seconds with millisecond precision for the raw sample with the maximum value on the given lookbehind window `d`. |  |
| `tmin_over_time(series_selector[d])` | Returns the timestamp in seconds with millisecond precision for the raw sample with the minimum value on the given lookbehind window `d`. |  |
| `zscore_over_time(series_selector[d])` | Returns z-score for raw samples on the given lookbehind window `d`. |  |

### Transform functions (93)

Apply to every point of every series returned by `q`.

| Signature | What it does | PromQL |
|---|---|---|
| `abs(q)` | Calculates the absolute value. | ✓ |
| `absent(q)` | Returns 1 if `q` has no points. | ✓ |
| `acos(q)` | Returns inverse cosine. | ✓ |
| `acosh(q)` | Returns inverse hyperbolic cosine. | ✓ |
| `asin(q)` | Returns inverse sine. | ✓ |
| `asinh(q)` | Returns inverse hyperbolic sine. | ✓ |
| `atan(q)` | Returns inverse tangent. | ✓ |
| `atanh(q)` | Returns inverse hyperbolic tangent. | ✓ |
| `bitmap_and(q, mask)` | Calculates bitwise `v & mask` for every `v` point of every time series returned from `q`. |  |
| `bitmap_or(q, mask)` | Calculates bitwise `v \| mask` for every `v` point of every time series returned from `q`. |  |
| `bitmap_xor(q, mask)` | Calculates bitwise `v ^ mask` for every `v` point of every time series returned from `q`. |  |
| `buckets_limit(limit, buckets)` | Limits the number of histogram buckets to the given `limit`. |  |
| `ceil(q)` | Rounds every point to the upper nearest integer. | ✓ |
| `clamp(q, min, max)` | Clamps every point with the given `min` and `max` values. | ✓ |
| `clamp_max(q, max)` | Clamps every point with the given `max` value. | ✓ |
| `clamp_min(q, min)` | Clamps every point with the given `min` value. | ✓ |
| `cos(q)` | Returns `cos(v)` for every `v` point of every time series returned by `q`. | ✓ |
| `cosh(q)` | Returns hyperbolic cosine. | ✓ |
| `day_of_month(q)` | Returns the day of month. | ✓ |
| `day_of_week(q)` | Returns the day of week. | ✓ |
| `day_of_year(q)` | Returns the day of year. | ✓ |
| `days_in_month(q)` | Returns the number of days in the month identified by every point of every time series returned by `q`. | ✓ |
| `deg(q)` | Converts Radians to degrees. | ✓ |
| `drop_empty_series(q)` | Drops empty series from `q`. |  |
| `end()` | Returns the unix timestamp in seconds for the last point. |  |
| `exp(q)` | Calculates the `e^v` for every point `v` of every time series returned by `q`. | ✓ |
| `floor(q)` | Rounds every point to the lower nearest integer. | ✓ |
| `histogram_avg(buckets)` | Calculates the average value for the given `buckets`. |  |
| `histogram_fraction(lowerLe, upperLe, buckets)` | Calculates the share (in the range `[0...1]`) for `buckets` that fall between `lowerLe` and `upperLe`. | ✓ |
| `histogram_quantile(phi, buckets)` | Calculates `phi`-percentile over the given histogram buckets. | ✓ |
| `histogram_quantiles("phiLabel", phi1, ..., phiN, buckets)` | Calculates the given `phi*`-quantiles over the given histogram buckets. |  |
| `histogram_share(le, buckets)` | Calculates the share (in the range `[0...1]`) for `buckets` that fall below `le`. |  |
| `histogram_stddev(buckets)` | Calculates standard deviation for the given `buckets`. |  |
| `histogram_stdvar(buckets)` | Calculates standard variance for the given `buckets`. |  |
| `hour(q)` | Returns the hour. | ✓ |
| `interpolate(q)` | Fills gaps with linearly interpolated values calculated from the last and the next non-empty points. |  |
| `keep_last_value(q)` | Fills gaps with the value of the last non-empty point in every time series returned by `q`. |  |
| `keep_next_value(q)` | Fills gaps with the value of the next non-empty point in every time series returned by `q`. |  |
| `limit_offset(limit, offset, q)` | Skips `offset` time series from series returned by `q` and then returns up to `limit` of the remaining time series per each group. |  |
| `ln(q)` | Calculates `ln(v)` for every point `v` of every time series returned by `q`. | ✓ |
| `log2(q)` | Calculates `log2(v)` for every point `v` of every time series returned by `q`. | ✓ |
| `log10(q)` | Calculates `log10(v)` for every point `v` of every time series returned by `q`. | ✓ |
| `minute(q)` | Returns the minute. | ✓ |
| `month(q)` | Returns the month. | ✓ |
| `now()` | Returns the current timestamp as a floating-point value in seconds. |  |
| `pi()` | Returns Pi number. | ✓ |
| `rad(q)` | Converts degrees to Radians. | ✓ |
| `prometheus_buckets(buckets)` | Converts histogram buckets with `vmrange` labels, as `histogram` and `histogram_over_time` return them, to Prometheus-style buckets with `le` labels. |  |
| `rand(seed)` | Returns pseudo-random numbers on the range `[0...1]` with even distribution. |  |
| `rand_exponential(seed)` | Returns pseudo-random numbers with exponential distribution. |  |
| `rand_normal(seed)` | Returns pseudo-random numbers with normal distribution. |  |
| `range_avg(q)` | Calculates the avg value across points. |  |
| `range_first(q)` | Returns the value for the first point. |  |
| `range_last(q)` | Returns the value for the last point. |  |
| `range_linear_regression(q)` | Calculates simple linear regression over the selected time range. |  |
| `range_mad(q)` | Calculates the median absolute deviation across points. |  |
| `range_max(q)` | Calculates the max value across points. |  |
| `range_median(q)` | Calculates the median value across points. |  |
| `range_min(q)` | Calculates the min value across points. |  |
| `range_normalize(q1, ...)` | Normalizes values for time series returned by `q1, ...` into `[0 ... 1]` range. |  |
| `range_quantile(phi, q)` | Returns `phi`-quantile across points. |  |
| `range_stddev(q)` | Calculates standard deviation on the selected time range. |  |
| `range_stdvar(q)` | Calculates standard variance on the selected time range. |  |
| `range_sum(q)` | Calculates the sum of points. |  |
| `range_trim_outliers(k, q)` | Drops points located farther than `k*range_mad(q)` from the `range_median(q)`. |  |
| `range_trim_spikes(phi, q)` | Drops `phi` percent of biggest spikes from time series returned by `q`. |  |
| `range_trim_zscore(z, q)` | Drops points located farther than `z*range_stddev(q)` from the `range_avg(q)`. |  |
| `range_zscore(q)` | Calculates z-score for points returned by `q`, e.g. it is equivalent to the following query: `(q - range_avg(q)) / range_stddev(q)`. |  |
| `remove_resets(q)` | Removes counter resets from time series returned by `q`. |  |
| `round(q, nearest)` | Rounds every point of every time series returned by `q` to the `nearest` multiple. | ✓ |
| `ru(free, max)` | Calculates resource utilization in the range `[0%...100%]` for the given `free` and `max` resources. |  |
| `running_avg(q)` | Calculates the running avg. |  |
| `running_max(q)` | Calculates the running max. |  |
| `running_min(q)` | Calculates the running min. |  |
| `running_sum(q)` | Calculates the running sum. |  |
| `scalar(q)` | Returns `q` if `q` contains only a single time series. | ✓ |
| `sgn(q)` | Returns `1` if `v>0`, `-1` if `v<0` and `0` if `v==0` for every point `v` of every time series returned by `q`. | ✓ |
| `sin(q)` | Returns `sin(v)` for every `v` point of every time series returned by `q`. |  |
| `sinh(q)` | Returns hyperbolic sine. |  |
| `tan(q)` | Returns `tan(v)` for every `v` point of every time series returned by `q`. |  |
| `tanh(q)` | Returns hyperbolic tangent. |  |
| `smooth_exponential(q, sf)` | Smooths points using exponential moving average with the given smooth factor `sf`. |  |
| `sort(q)` | Sorts series in ascending order by the last point in every time series returned by `q`. | ✓ |
| `sort_desc(q)` | Sorts series in descending order by the last point in every time series returned by `q`. | ✓ |
| `sqrt(q)` | Calculates square root. | ✓ |
| `start()` | Returns unix timestamp in seconds for the first point. |  |
| `step()` | Returns the step in seconds (aka interval) between the returned points. |  |
| `time()` | Returns unix timestamp for every returned point. | ✓ |
| `timezone_offset(tz)` | Returns offset in seconds for the given timezone `tz` relative to UTC. |  |
| `ttf(free)` | Estimates the time in seconds needed to exhaust `free` resources. |  |
| `union(q1, ..., qN)` | Returns a union of time series returned from `q1`, ..., `qN`. |  |
| `vector(q)` | Returns `q`, e.g. it does nothing in MetricsQL. | ✓ |
| `year(q)` | Returns the year. | ✓ |

### Label manipulation functions (22)

Rewrite, filter or sort series by their labels.

| Signature | What it does | PromQL |
|---|---|---|
| `alias(q, "name")` | Sets the given `name` to all the time series returned by `q`. |  |
| `drop_common_labels(q1, ...., qN)` | Drops common `label="value"` pairs among time series returned from `q1, ..., qN`. |  |
| `label_copy(q, "src_label1", "dst_label1", ..., "src_labelN", "dst_labelN")` | Copies label values from `src_label*` to `dst_label*`. |  |
| `label_del(q, "label1", ..., "labelN")` | Deletes the given `label*` labels from all the time series returned by `q`. |  |
| `label_graphite_group(q, groupNum1, ... groupNumN)` | Replaces metric names returned from `q` with the given Graphite group values concatenated via `.` char. |  |
| `label_join(q, "dst_label", "separator", "src_label1", ..., "src_labelN")` | Joins `src_label*` values with the given `separator` and stores the result in `dst_label`. | ✓ |
| `label_keep(q, "label1", ..., "labelN")` | Deletes all the labels except of the listed `label*` labels in all the time series returned by `q`. |  |
| `label_lowercase(q, "label1", ..., "labelN")` | Lowercases values for the given `label*` labels in all the time series returned by `q`. |  |
| `label_map(q, "label", "src_value1", "dst_value1", ..., "src_valueN", "dst_valueN")` | Maps `label` values from `src_*` to `dst*`. |  |
| `label_match(q, "label", "regexp")` | Drops time series from `q` with `label` not matching the given `regexp`. |  |
| `label_mismatch(q, "label", "regexp")` | Drops time series from `q` with `label` matching the given `regexp`. |  |
| `label_move(q, "src_label1", "dst_label1", ..., "src_labelN", "dst_labelN")` | Moves label values from `src_label*` to `dst_label*`. |  |
| `label_replace(q, "dst_label", "replacement", "src_label", "regex")` | Applies the given `regex` to `src_label` and stores the `replacement` in `dst_label` if the given `regex` matches `src_label`. | ✓ |
| `label_set(q, "label1", "value1", ..., "labelN", "valueN")` | Sets `{label1="value1", ..., labelN="valueN"}` labels to all the time series returned by `q`. |  |
| `label_transform(q, "label", "regexp", "replacement")` | Substitutes all the `regexp` occurrences by the given `replacement` in the given `label`. |  |
| `label_uppercase(q, "label1", ..., "labelN")` | Uppercases values for the given `label*` labels in all the time series returned by `q`. |  |
| `label_value(q, "label")` | Returns numeric values for the given `label`. |  |
| `labels_equal(q, "label1", "label2", ...)` | Returns `q` series with identical values for the listed labels "label1", "label2", etc. |  |
| `sort_by_label(q, "label1", ... "labelN")` | Sorts series in ascending order by the given set of labels. |  |
| `sort_by_label_desc(q, "label1", ... "labelN")` | Sorts series in descending order by the given set of labels. |  |
| `sort_by_label_numeric(q, "label1", ... "labelN")` | Sorts series in ascending order by the given set of labels using numeric sort. |  |
| `sort_by_label_numeric_desc(q, "label1", ... "labelN")` | Sorts series in descending order by the given set of labels using numeric sort. |  |

### Aggregate functions (37)

Combine series into groups. All accept `by (...)` / `without (...)` and a trailing `limit N`.

| Signature | What it does | PromQL |
|---|---|---|
| `any(q) by (group_labels)` | Returns a single series per `group_labels` out of time series returned by `q`. |  |
| `avg(q) by (group_labels)` | Returns the average value per `group_labels` for time series returned by `q`. | ✓ |
| `bottomk(k, q)` | Returns up to `k` points with the smallest values across all the time series returned by `q`. | ✓ |
| `bottomk_avg(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the smallest averages. |  |
| `bottomk_last(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the smallest last values. |  |
| `bottomk_max(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the smallest maximums. |  |
| `bottomk_median(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the smallest medians. |  |
| `bottomk_min(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the smallest minimums. |  |
| `count(q) by (group_labels)` | Returns the number of non-empty points per `group_labels` for time series returned by `q`. | ✓ |
| `count_values("label", q)` | Counts the number of points with the same value and stores the counts in a time series with an additional `label`, which contains each initial value. | ✓ |
| `distinct(q)` | Calculates the number of unique values per each group of points with the same timestamp. |  |
| `geomean(q)` | Calculates geometric mean per each group of points with the same timestamp. |  |
| `group(q) by (group_labels)` | Returns `1` per each `group_labels` for time series returned by `q`. | ✓ |
| `histogram(q)` | Calculates a histogram (buckets labelled `vmrange`) per each group of points with the same timestamp. |  |
| `limitk(k, q) by (group_labels)` | Returns up to `k` time series per each `group_labels` out of time series returned by `q`. |  |
| `mad(q) by (group_labels)` | Returns the Median absolute deviation per each `group_labels`. |  |
| `max(q) by (group_labels)` | Returns the maximum value per each `group_labels`. | ✓ |
| `median(q) by (group_labels)` | Returns the median value per each `group_labels`. |  |
| `min(q) by (group_labels)` | Returns the minimum value per each `group_labels`. | ✓ |
| `mode(q) by (group_labels)` | Returns mode) per each `group_labels`. |  |
| `outliers_iqr(q)` | Returns time series from `q` with at least a single point outside e.g. Interquartile range outlier bounds `[q25-1.5*iqr .. q75+1.5*iqr]` comparing to other time series at the given point, where:. |  |
| `outliers_mad(tolerance, q)` | Returns time series from `q` with at least a single point outside Median absolute deviation (aka MAD) multiplied by `tolerance`. |  |
| `outliersk(k, q)` | Returns up to `k` time series with the biggest standard deviation (aka outliers) out of time series returned by `q`. |  |
| `quantile(phi, q) by (group_labels)` | Calculates `phi`-quantile per each `group_labels`. | ✓ |
| `quantiles("phiLabel", phi1, ..., phiN, q)` | Calculates `phi*`-quantiles and return them in time series with `{phiLabel="phi*"}` label. |  |
| `share(q) by (group_labels)` | Returns shares in the range `[0..1]` for every non-negative points returned by `q` per each timestamp, so the sum of shares per each `group_labels` equals 1. |  |
| `stddev(q) by (group_labels)` | Calculates standard deviation per each `group_labels`. | ✓ |
| `stdvar(q) by (group_labels)` | Calculates standard variance per each `group_labels`. | ✓ |
| `sum(q) by (group_labels)` | Returns the sum per each `group_labels`. | ✓ |
| `sum2(q) by (group_labels)` | Calculates the sum of squares per each `group_labels`. |  |
| `topk(k, q)` | Returns up to `k` points with the biggest values across all the time series returned by `q`. | ✓ |
| `topk_avg(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the biggest averages. |  |
| `topk_last(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the biggest last values. |  |
| `topk_max(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the biggest maximums. |  |
| `topk_median(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the biggest medians. |  |
| `topk_min(k, q, "other_label=other_value")` | Returns up to `k` time series from `q` with the biggest minimums. |  |
| `zscore(q) by (group_labels)` | Returns z-score values per each `group_labels`. |  |

