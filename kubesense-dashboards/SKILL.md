---
title: KubeSense Dashboard JSON Generator
description: Generate complete KubeSense dashboard JSON configurations (preset format) based on user requirements for panels, metrics, logs, traces, variables, and grid layouts.
---

# KubeSense Dashboard JSON Generator

Generate complete KubeSense dashboard JSON configurations (preset format) based on user requirements.

## When to Use

User asks to:

- "Create a dashboard for..."
- "Give me the dashboard JSON for..."
- "Build a dashboard with panels for..."
- "Generate a dashboard preset"

## Output Format

Always output the complete dashboard JSON in this structure:

```json
{
  "name": "<dashboard name>",
  "description": "<description>",
  "preset": {
    "gridLayout": [],
    "panels": [],
    "variables": [],
    "subGrids": [],
    "subGridLayout": []
  }
}
```

## Schema Reference

### Panel (`panelEditorFormValuesBaseSchema`)

```json
{
  "name": "string (required)",
  "description": "string (optional)",
  "panelType": "timeSeries | stat | table | list | bar | pie | topList | spl",
  "queries": [],
  "config": {}
}
```

### Panel Config (defaults)

```json
{
  "lineWidth": 1.5,
  "fillOpacity": 0,
  "stackSeries": false,
  "showTrend": false,
  "showLabel": false,
  "showPercentageChange": false,
  "percentageChangeColorMode": "standard",
  "mergeTables": false,
  "legendVisibility": true,
  "legendPlacement": "bottom",
  "tooltipMode": "single",
  "yAxisLabelFormatter": "auto",
  "step": "auto",
  "thresholds": [],
  "enableThresholds": true,
  "valueOptions": { "show": "calculate", "calculation": "last" },
  "colorPalette": "default"
}
```

### Metrics Query

```json
{
  "selectedMode": "metrics",
  "label": "A",
  "selectedMetric": "metric_name",
  "functions": [],
  "filters": {},
  "queryMode": "builder",
  "visible": true,
  "variables": [],
  "labelOptions": { "type": "auto" },
  "pagination": { "page": 1, "page_size": 50 },
  "fieldConfig": {}
}
```

### Logs/Traces Query

```json
{
  "selectedMode": "logs",
  "label": "A",
  "filters": {},
  "queryMode": "builder",
  "filterMode": "MFD",
  "visible": true,
  "variables": [],
  "labelOptions": { "type": "auto" },
  "aggregation": { "function": "row_count" },
  "groupBy": [],
  "pagination": { "page": 1, "page_size": 50 },
  "sorting": {
    "sortBy": { "field": "", "type": "string", "is_attribute": false },
    "sortOrder": "ASC"
  },
  "query": "",
  "chart_type": "table",
  "columnFields": [],
  "xaxis": "auto",
  "yaxis": "auto",
  "source": "auto",
  "topListLabel": [],
  "topListValue": "auto",
  "fieldConfig": {}
}
```

### Formula Query

```json
{
  "selectedMode": "formula",
  "label": "C",
  "expression": "A+B",
  "visible": true,
  "labelOptions": { "type": "auto" },
  "fieldConfig": {}
}
```

### Metrics Query Functions (`panelMetricsQueryFormulaSchema`)

**Range:**

```json
{
  "type": "range",
  "name": "rate | increase | resets",
  "arguments": [{ "arg_name": "over", "arg_value": "5m" }]
}
```

**Aggregations:**

```json
{
  "type": "aggregations",
  "name": "sum | avg | max | min | count | No_Aggregations",
  "arguments": [{ "arg_name": "by", "arg_value": ["label1", "label2"] }]
}
```

**Top/Bottom:**

```json
{
  "type": "top_bottom",
  "name": "top | bottom",
  "arguments": [
    { "arg_name": "k", "arg_value": 5 },
    { "arg_name": "by", "arg_value": "max" }
  ]
}
```

**Rollup:**

```json
{
  "type": "rollup",
  "name": "avg_over_time | sum_over_time | max_over_time | min_over_time | count_over_time | last_over_time | absent_over_time | present_over_time | increases_over_time | range_over_time | quantile_over_time",
  "arguments": [{ "arg_name": "over", "arg_value": "5m" }]
}
```

**Comparison:**

```json
{
  "type": "comparison",
  "name": "greater | lesser | greater_than_or_equal | less_than_or_equal | equal | not_equal",
  "arguments": [{ "arg_name": "than", "arg_value": 100 }]
}
```

**Transform:**

```json
{
  "type": "transform",
  "name": "abs | clamp | clamp_max | clamp_min | round | histogram_quantile | sort | sort_desc",
  "arguments": [{ "arg_name": "quantile", "arg_value": 0.95 }]
}
```

### Grid Layout Item

```json
{ "i": "panel-0", "x": 0, "y": 0, "w": 6, "h": 4 }
```

- `i`: unique ID (use `panel-0`, `panel-1`, etc.)
- `x`: 0-11 (12-column grid)
- `y`: auto-increment based on previous items
- `w`: 1-12
- `h`: height in 100px units

### Variable

```json
{
  "id": "uuid",
  "name": "variable_name",
  "label": "Display Label",
  "variableType": "textbox | custom | traces | logs | metrics",
  "multiSelect": false
}
```

### Sub-Grid (Row)

```json
{
  "id": "subgrid-uuid",
  "title": "Row Name",
  "collapsed": false,
  "panels": [],
  "gridLayout": []
}
```

## Y-Axis Formatter Options

`auto`, `bytes`, `seconds`, `milliseconds`, `percent`, `percent_unit`, `ops`, `bps`, `short`, `celsius`, `fahrenheit`, `none`

## Rollup Time Ranges

`30s`, `1m`, `5m`, `30m`, `1h`, `1d`

## Aggregation Functions (logs/traces)

`row_count`, `unique_count`, `avg`, `sum`, `max`, `min`, `p99`, `p95`, `p90`, `p75`, `p50`

## Color Palette Keys

`default`, `classic`, `warm`, `cool`, `vivid`, `muted`

## Threshold Colors

`green`, `yellow`, `orange`, `red`, `blue`, `purple`

## Rules

1. Always output valid JSON — no markdown wrapping unless in a code block
2. Use `panel-0`, `panel-1` etc. for layout `i` values
3. Grid `x` values: place panels side by side (0, 6 for 2-column; 0, 4, 8 for 3-column)
4. Grid `y` values: increment based on previous panel height
5. Each metrics query needs a unique `label` (A, B, C...) for formula references
6. Formula expressions use query labels: `A+B`, `A/B*100`, `(A-B)/A*100`
7. Include `config` on every panel with defaults unless user specifies otherwise
8. For time series panels, typically use `rate()` + aggregation as first two functions
9. Empty `filters: {}` is valid — no need to populate unless user specifies filters
10. Generate UUIDs for variable IDs and sub-grid IDs
