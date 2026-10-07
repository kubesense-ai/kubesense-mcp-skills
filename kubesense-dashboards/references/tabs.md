# Tabs

Read this when a dashboard should be split into **tabs**: pages the viewer switches
between, one visible at a time. Tabs are optional. Omit `tabs`, or send `[]`, and the
dashboard is one page, as before.

## Tabs or rows

| Use | When |
|---|---|
| Rows (`subGrids`) | The panels belong on one page and the viewer scrolls or collapses groups. For example, one service's latency, errors and saturation. |
| Tabs (`tabs`) | The groups are separate views a viewer reads one at a time. For example, an overview, node health and per-service detail. |

A tab can hold rows, so a large tab can still be grouped. Only the open tab's panels load,
so tabs also keep a dashboard with many panels fast to open. Each tab has its own URL
(`?tab=<id>`), which makes a link to one view possible.

## Shape

A **page** is `{panels, gridLayout, subGrids, subGridLayout}`. An untabbed dashboard's top
level is one page. A tabbed dashboard has one page per tab:

```json
{ "id": "node-health", "title": "Node health", "panels": [], "gridLayout": [], "subGrids": [], "subGridLayout": [] }
```

| Key | Rule |
|---|---|
| `id` | Matches `^[a-z0-9][a-z0-9-]{0,39}$`. Unique in the dashboard. The UI slugs it from the title once and never changes it on rename, so links stay valid. |
| `title` | Non-empty after trimming, at most 50 characters. Unique in the dashboard, compared case-insensitively after trimming. |
| `panels`, `gridLayout` | Paired by array index inside the tab, exactly like the top level. `y` starts at 0 in each tab. |
| `subGrids`, `subGridLayout` | Rows inside the tab, same shape as in [variables-and-rows.md](./variables-and-rows.md). |

Rules that span the dashboard:

- When `tabs` is non-empty, the top-level `panels`, `gridLayout`, `subGrids` and
  `subGridLayout` must be present and empty. Validation refuses a preset with panels in
  both places.
- Sub-grid ids are unique across the whole dashboard, not per tab. Two tabs cannot both
  have a row `row-1`.
- `variables`, `eventOverlays` and `publicDashboardPath` stay at the top level. A variable
  feeds `$name` into every tab's panels, and the overlay applies to every inheriting panel
  on every tab.
- Tab order is array order. The first tab opens by default.
- A one-element `tabs` array validates, but the UI never makes one. Deleting down to one
  tab moves that tab's page to the top level and drops its title. Write an untabbed
  dashboard instead of a single tab.

## Complete example

Two tabs and one dashboard-wide variable. The second tab holds a row. Pass this object to
`validate-dashboard-json` and `create-dashboard`, or stringify it into the import
envelope's `preset`. Replace the metric names with ones `get-available-metrics` returns.

```json
{
  "gridLayout": [],
  "panels": [],
  "subGrids": [],
  "subGridLayout": [],
  "variables": [
    {
      "name": "namespace",
      "description": "",
      "meta": { "variableType": "custom", "options": ["prod", "staging"], "value": ["prod"], "selectType": "single" }
    }
  ],
  "tabs": [
    {
      "id": "overview",
      "title": "Overview",
      "panels": [
        {
          "name": "Targets up",
          "panelType": "stat",
          "queries": [{ "selectedMode": "metrics", "label": "A", "selectedMetric": "up", "filters": { "namespace": ["$namespace"] }, "functions": [] }],
          "config": {}
        },
        {
          "name": "Pod restarts",
          "panelType": "timeSeries",
          "queries": [{ "selectedMode": "metrics", "label": "A", "selectedMetric": "kube_pod_container_status_restarts_total", "filters": { "namespace": ["$namespace"] }, "functions": [] }],
          "config": {}
        }
      ],
      "gridLayout": [
        { "i": "0", "x": 0, "y": 0, "w": 4, "h": 3 },
        { "i": "1", "x": 4, "y": 0, "w": 8, "h": 3 }
      ],
      "subGrids": [],
      "subGridLayout": []
    },
    {
      "id": "node-health",
      "title": "Node health",
      "panels": [
        {
          "name": "Node CPU",
          "panelType": "timeSeries",
          "queries": [{ "selectedMode": "metrics", "label": "A", "selectedMetric": "node_cpu_seconds_total", "functions": [] }],
          "config": {}
        }
      ],
      "gridLayout": [{ "i": "0", "x": 0, "y": 0, "w": 12, "h": 4 }],
      "subGrids": [
        {
          "id": "node-disk",
          "title": "Disk",
          "collapsed": false,
          "panels": [
            {
              "name": "Disk read bytes",
              "panelType": "timeSeries",
              "queries": [{ "selectedMode": "metrics", "label": "A", "selectedMetric": "node_disk_read_bytes_total", "functions": [] }],
              "config": {}
            }
          ],
          "gridLayout": [{ "i": "0", "x": 0, "y": 0, "w": 12, "h": 4 }]
        }
      ],
      "subGridLayout": [{ "i": "sg-node-disk", "x": 0, "y": 4, "w": 12, "h": 1 }]
    }
  ]
}
```

## Editing a tabbed dashboard

`get-dashboard-details` returns `tab_id` and `tab_title` on each panel row, and the list of
tabs. With `panel_operations`, every operation needs `tab_id`, beside `sub_grid_id` and
`position`. A missing or unknown `tab_id` refuses the call, and the error lists the valid
ids.

Adding, removing, renaming and reordering tabs, and moving a panel between tabs, are
whole-preset rewrites: read with `get-dashboard-details raw=true`, edit the `tabs` array,
validate, and send the whole preset back. Keep the `tabs` key in what you send. A preset
with no `tabs` key over a tabbed dashboard is refused with 409, because the server reads it
as a client that would drop the tabs.

To turn an untabbed dashboard into tabs, do what the UI does. Move the existing top-level
page into a first tab, `{"id": "overview", "title": "Overview", ...}`, then empty the
top-level `panels`, `gridLayout`, `subGrids` and `subGridLayout`.
