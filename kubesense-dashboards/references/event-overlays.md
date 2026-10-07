# Event Overlays

Read this when a dashboard should mark **events** (deployments, releases, CI runs, pushes)
on its charts. An overlay draws one vertical marker per matching event across the panel's
time axis; hovering a marker shows the event and links to the Events page.

Two fields carry overlays, and both are optional:

| Field | Where | Meaning |
|---|---|---|
| `eventOverlays` | top level of the preset, beside `panels` | overlays every inheriting panel draws |
| `config.eventOverlay` | on one panel | how that panel picks its overlays |

Omit both and the dashboard draws no markers.

## Schema

One overlay:

```json
{
  "name": "Deployments",
  "color": "purple",
  "filters": { "type": ["deployment"] },
  "filterMode": "MFD"
}
```

| Key | Type | Default | Notes |
|---|---|---|---|
| `name` | string | `"Events"` in the legend | label on the legend and the hover card |
| `color` | `red` \| `purple` \| `orange` \| `gray` \| `green` \| `blue` | `red` | a palette name, never a hex value |
| `filters` | `Record<string, string[]>` | `{}` | which events to mark, the same shape as an events query's `filters` |
| `filterMode` | `MFD` \| `ADVANCED_QUERY` | `MFD` | `ADVANCED_QUERY` reads the WHERE text from `filters.advanced_query` |

`eventOverlays` is an array of these. A panel's choice:

```json
"config": { "eventOverlay": { "mode": "custom", "overlays": [ /* overlays */ ] } }
```

| `mode` | The panel draws |
|---|---|
| `inherit` (also what an absent `eventOverlay` means) | the dashboard's `eventOverlays` |
| `custom` | its own `overlays` **instead of** the dashboard's. The two lists never merge. |
| `off` | nothing |

`mode` is required whenever `eventOverlay` is present. `overlays` is read only under
`custom`; to add one marker set to a panel and keep the dashboard's, repeat the dashboard's
overlays inside `overlays`.

### Filters

Overlay filters are an events query's filters, so everything in the SKILL.md sections
**Filtering a logs / traces / events query** and **Events query** applies:

- `MFD` takes equality lists: `{"source": ["github"], "type": ["deployment"]}`. Values in
  one list are OR'd, keys are AND'd, a `-` prefix excludes, and `$name` reads a dashboard
  variable.
- `ADVANCED_QUERY` takes one WHERE string:
  `{"advanced_query": ["type = deployment AND environment = production"]}`.
- Field names are the events catalog: `type`, `category`, `source`, `repository`,
  `environment`, `status`, `actor`, `severity`, `service`, `namespace`, `cluster`, and the
  rest that `get-fields` returns with `signal: "events"`. Discover values with it before
  writing a filter.

`filters: {}` marks **every** event in the time range. Always filter.

## What hard-fails validation

`validate-dashboard-json`, `create-dashboard` and `update-dashboard` refuse:

1. A panel `eventOverlay.mode` other than `inherit`, `custom` or `off` (e.g. `merge`), or an
   `eventOverlay` with no `mode`.
2. An overlay `filterMode` other than `MFD` or `ADVANCED_QUERY`. Events have no `SPL` or
   `SQL`.
3. An overlay `color` outside the six palette names. Hex (`#F54E42`) is refused.
4. `filters` values that are not string arrays, or `eventOverlays` that is not an array.

A bad panel `eventOverlay` reports two findings: the real one under
`/panels/N/config/eventOverlay/...`, and `additional properties 'eventOverlay' not allowed`
at `/panels/N/config`. The second is a side effect of the first. Fix the nested one and both
clear.

## What validates and does nothing

These pass validation. Check them by hand.

- **Only `timeSeries` and `bar` panels draw markers.** An `eventOverlay` on a `table`,
  `stat`, `pie`, or any other panel type is accepted and ignored.
- `overlays` under `mode: "inherit"` or `"off"` is ignored.
- `mode: "custom"` with no `overlays` draws nothing, the same as `off`.
- An overlay draws at most the **latest 2,000** matching events in the time range; older
  matches are dropped without notice. A filter that broad is unreadable anyway, so narrow it.
- **Public dashboards never draw overlays.**
- Validation checks shape only. A filter on a field or value no event carries draws no
  markers.

## Worked example

GitHub deployments marked on every chart, with one panel opted out. Panel 0 inherits by
omission; panel 1 sets `off`.

```json
{
  "gridLayout": [
    { "i": "0", "x": 0, "y": 0, "w": 6, "h": 4 },
    { "i": "1", "x": 6, "y": 0, "w": 6, "h": 4 }
  ],
  "eventOverlays": [
    {
      "name": "Deployments",
      "color": "purple",
      "filters": { "source": ["github"], "type": ["deployment"] },
      "filterMode": "MFD"
    }
  ],
  "panels": [
    {
      "name": "Requests",
      "panelType": "timeSeries",
      "queries": [
        {
          "selectedMode": "traces",
          "label": "A",
          "columnFields": [],
          "aggregation": { "function": "row_count" },
          "chart_type": "timeseries"
        }
      ],
      "config": {}
    },
    {
      "name": "Requests (no markers)",
      "panelType": "timeSeries",
      "queries": [
        {
          "selectedMode": "traces",
          "label": "A",
          "columnFields": [],
          "aggregation": { "function": "row_count" },
          "chart_type": "timeseries"
        }
      ],
      "config": { "eventOverlay": { "mode": "off" } }
    }
  ]
}
```

To give a panel production deployments only, replace its dashboard overlays:

```json
"config": {
  "eventOverlay": {
    "mode": "custom",
    "overlays": [
      {
        "name": "Prod deployments",
        "color": "orange",
        "filters": { "advanced_query": ["type = deployment AND environment = production"] },
        "filterMode": "ADVANCED_QUERY"
      }
    ]
  }
}
```

To add overlays to an existing dashboard, `eventOverlays` is outside any panel, so it needs
the whole-preset rewrite in SKILL.md (**Editing an existing dashboard**). A single panel's
`eventOverlay` is an `update_panel` patch:
`{"op": "update_panel", "position": 1, "panel": {"config": {"eventOverlay": {"mode": "off"}}}}`.
