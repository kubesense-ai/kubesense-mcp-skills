# Panel `config` Reference

Source of truth: `webapp/src/pages/explorer/v2/utils/zod-schemas.ts` (`panelConfigSchema`).

**Every field has a `.catch()`, and so does the whole object.** `config: {}` is always
valid and inherits all defaults. A bad value never fails import — it silently reverts to
the default. Unknown keys are stripped.

## Full field list

| Field | Type / allowed values | Default |
|---|---|---|
| `lineWidth` | number 0–10 | `1.5` |
| `fillOpacity` | number 0–100 | `0` |
| `stackSeries` | boolean | `false` |
| `showTrend` | boolean | `false` |
| `showLabel` | boolean | `false` |
| `showPercentageChange` | boolean | `false` |
| `percentageChangeColorMode` | `standard` \| `invert` \| `same_as_value` | `standard` |
| `mergeTables` | `z.literal(true)` — always true, cannot be disabled | `true` |
| `legendVisibility` | boolean | `true` |
| `legendPlacement` | `bottom` \| `right` | `bottom` |
| `tooltipMode` | `single` \| `all` | `single` |
| `yAxisLabelFormatter` | one of the 199 units below | `auto` |
| `yAxisMin` | number \| null | `null` |
| `yAxisMax` | number \| null | `null` |
| `yAxisIncludeZero` | boolean | `false` |
| `step` | `"auto"` \| **positive integer** | `auto` |
| `thresholds` | array, see below | one default entry |
| `thresholdDisplayMode` | see below | `off` |
| `valueOptions` | `{show, calculation}` | `{show:"calculate",calculation:"last"}` |
| `colorScheme` | 5-variant union, see below | `{type:"palette",palette:"default"}` |
| `tableSettings` | `{columnWidths: Record<string, number>}` | `{columnWidths:{}}` |
| `alignColumns` | array, see below | `[]` |
| `columnFormatting` | array, see below | `[]` |

`step` must be an *integer* — `60.5` silently becomes `"auto"`.

## `thresholdDisplayMode`

```
off | lines | lines_dashed | filled_regions | filled_regions_and_lines | filled_regions_and_lines_dashed
```

There is **no `enableThresholds` field** — it was removed. Use this instead.

## `thresholds[]`

```json
{ "threshold": 80, "color": "#e24d42", "isDefault": false, "isLabelShown": true, "label": "warn" }
```

| Field | Type | Default |
|---|---|---|
| `threshold` | number \| `"-Infinity"` \| `"Infinity"` | `"-Infinity"` |
| `color` | **any string** — hex expected | `"#56a64b"` |
| `isDefault` | boolean | — |
| `isLabelShown` | boolean, optional | — |
| `label` | string, optional | — |

The default `thresholds` value is **not** `[]` — it is one entry:

```json
[{ "threshold": "-Infinity", "color": "#56a64b", "isDefault": true, "isLabelShown": false, "label": "" }]
```

`color` is an unconstrained string, so named colors like `"green"` validate but will not
render as intended. The named constants in the codebase are hex: `#56a64b` (green),
`#ef843c` (orange), `#e24d42` (red).

## `colorScheme`

Discriminated on `type` — five variants:

```json
{ "type": "palette",    "palette": "default" }
{ "type": "single",     "color": "#e24d42" }
{ "type": "shades",     "color": "#e24d42" }
{ "type": "thresholds", "seriesReducer": "last" }
{ "type": "custom",     "colors": ["#e24d42", "#56a64b"] }
```

- `palette` — only `default`, `success`, `warning`, `error`. (`classic`, `warm`, `cool`,
  `vivid`, `muted` do **not** exist and silently fall back to `default`.)
- `seriesReducer` — `last` \| `min` \| `max`.
- `custom.colors` — at least one entry, each matching
  `/^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/`.

There is **no `colorPalette` field** — it was replaced by `colorScheme`.

## `valueOptions`

```json
{ "show": "calculate", "calculation": "last" }
```

`show` is the literal `"calculate"`. `calculation` — 10 values:

```
mean | standard_deviation | sum | max | min | median | last | first | range | min_above_zero
```

## `alignColumns[]`

```json
{
  "id": "col-1",
  "displayName": "",
  "mappings": [ { "queryLabel": "A", "field": "namespace", "is_attribute": false } ]
}
```

Used to align columns across queries in a table panel.

## `columnFormatting[]`

Per-column overrides for a **table** panel — display name, visibility, cell rendering, and
colouring. One entry per column you want to change; a column with no entry renders with its
default name and a plain numeric cell. Ignored by non-table panels.

```json
{
  "id": "b1e2…",
  "columnId": "count-a",
  "cellType": "number",
  "colorMode": "conditions",
  "conditions": [ { "operator": ">", "value": 100, "style": "red-background" } ],
  "range": { "palette": "green", "scale": "logarithmic", "min": null, "max": null },
  "displayName": "Requests",
  "hidden": false,
  "width": 120
}
```

| Field | Type / allowed values | Default |
|---|---|---|
| `id` | string — a uuid, the array key | required |
| `columnId` | string — the rendered column id this applies to | required |
| `cellType` | `number` \| `trend` \| `bar` | `number` |
| `colorMode` | `conditions` \| `range` | `conditions` |
| `conditions` | array of condition objects, see below | `[]` |
| `range` | object, see below | omitted |
| `trend` | object, see below | omitted |
| `displayName` | string | omitted |
| `hidden` | boolean | omitted |
| `width` | positive number (px) | omitted |

`columnId` is the id the renderer assigns, which differs by table shape: a merged dimension
column is its metric key (`service`, `@service`), a merged value column is the kebab-cased
query label (`a`, `count-a`), and an SPL/SQL column is `<name>-<index>`. A `columnId` matching
nothing currently rendered is **not** an error — the entry simply does not apply, which is
what lets a saved panel survive a query edit.

`displayName` is the outermost of the column-naming layers and wins over
`alignColumns[].displayName`, `columnFields[].alias`, and the field-catalog label. An empty or
whitespace-only value counts as absent (the derived name shows instead).

**`conditions[]`** — first match wins, in list order (not most-specific, not last):

| Field | Type | Notes |
|---|---|---|
| `operator` | `>` \| `>=` \| `<` \| `<=` \| `=` \| `!=` | required |
| `value` | number | required |
| `style` | see list below | `red-background` on a bad value |
| `color` | string (hex) | read only for `custom-background` / `custom-text` |

`style` values: `red-background`, `yellow-background`, `green-background`,
`light-red-background`, `light-yellow-background`, `light-green-background`, `red-text`,
`yellow-text`, `green-text`, `custom-background`, `custom-text`.

**`range`** — continuous colouring, read when `colorMode` is `range`:

| Field | Type | Default |
|---|---|---|
| `palette` | see list below | `green` |
| `scale` | `linear` \| `logarithmic` | `logarithmic` |
| `min` | number \| null (`null` = derive from data) | `null` |
| `max` | number \| null (`null` = derive from data) | `null` |

`palette` values: `green`, `orange`, `red`, `blue`, `red-green`, `red-blue`, `solid-green`,
`solid-orange`, `solid-red`, `solid-blue`, `solid-red-green`, `solid-red-blue`. Gradient
palettes go transparent→colour; two-hue ramps name their direction (`red-green` = red at the
minimum, green at the maximum).

**`trend`** — sparkline settings, read only when `cellType` is `trend`:

| Field | Type | Default |
|---|---|---|
| `uniformYAxes` | boolean (shared y-range across rows) | `true` |
| `display` | `area` \| `bar` \| `line` | `line` |

> [!NOTE]
> The webapp currently colours **`bar`** cells by `conditions` only (the bar length carries
> the magnitude) and hides the **`trend`** cell type until per-row time series are fetched.
> The import schema still accepts `range` on any cell type and the full `trend` object, so
> presets are forward-compatible.
>
> `columnFormatting` ships with the panel field-overrides release. A server that predates it
> strips the key (like any unknown field), so the panel renders unformatted rather than
> failing import.

## `yAxisLabelFormatter` — all 199 values

Also the enum for `fieldConfig.unit` on any query.

> [!WARNING]
> `percent`, `percent_unit`, `short`, `ops`, `bps`, `celsius`, `fahrenheit`, and `none` are
> **not** in this list. They silently become `auto`. Use `percentage`, `number`,
> `mCPU`/`CPU`, `bytes/sec` instead.

**general** — `auto`, `number`, `raw`, `percentage`

**cpu** — `mCPU`, `CPU`

**time** — `nanoseconds`, `microseconds`, `milliseconds`, `seconds`, `minutes`, `hours`,
`days`

**data** — `bytes`, `bytes_iec`, `bytes_si`, `bits_iec`, `bits_si`, `kibibytes`,
`kilobytes`, `mebibytes`, `megabytes`, `gibibytes`, `gigabytes`, `tebibytes`, `terabytes`,
`pebibytes`, `petabytes`

**data_rate** — `bytes/sec`, `packets_per_sec`, `bytes_per_sec_iec`, `bytes_per_sec_si`,
`bits_per_sec_iec`, `bits_per_sec_si`, `kibibytes_per_sec`, `kibibits_per_sec`,
`kilobytes_per_sec`, `kilobits_per_sec`, `mebibytes_per_sec`, `mebibits_per_sec`,
`megabytes_per_sec`, `megabits_per_sec`, `gibibytes_per_sec`, `gibibits_per_sec`,
`gigabytes_per_sec`, `gigabits_per_sec`, `tebibytes_per_sec`, `tebibits_per_sec`,
`terabytes_per_sec`, `terabits_per_sec`, `pebibytes_per_sec`, `pebibits_per_sec`,
`petabytes_per_sec`, `petabits_per_sec`

**currency** — `dollars`, `pounds`, `euro`, `yen`, `rubles`, `hryvnias`, `real`,
`danish_krone`, `icelandic_krona`, `norwegian_krone`, `swedish_krona`, `czech_koruna`,
`swiss_franc`, `polish_zloty`, `bitcoin`, `milli_bitcoin`, `micro_bitcoin`,
`south_african_rand`, `indian_rupee`, `south_korean_won`, `indonesian_rupiah`,
`philippine_peso`, `vietnamese_dong`, `turkish_lira`, `malaysian_ringgit`, `cfp_franc`,
`bulgarian_lev`, `guarani`, `inr`

**energy** — `watt`, `kilowatt`, `megawatt`, `gigawatt`, `milliwatt`,
`watt_per_square_meter`, `volt_ampere`, `kilovolt_ampere`, `volt_ampere_reactive`,
`kilovolt_ampere_reactive`, `watt_hour`, `watt_hour_per_kilogram`, `kilowatt_hour`,
`kilowatt_min`, `megawatt_hour`, `ampere_hour`, `kiloampere_hour`, `milliampere_hour`,
`joule`, `electron_volt`, `ampere`, `kiloampere`, `milliampere`, `volt`, `kilovolt`,
`millivolt`, `decibel_milliwatt`, `milliohm`, `ohm`, `kiloohm`, `megaohm`, `farad`,
`microfarad`, `nanofarad`, `picofarad`, `femtofarad`, `henry`, `millihenry`, `microhenry`,
`lumens`

**data science / concentration** — `ppm`, `ppb`, `ng_m3`, `ng_Nm3`, `ug_m3`, `ug_Nm3`,
`mg_m3`, `mg_Nm3`, `g_m3`, `g_Nm3`, `mg_dL`, `mmol_L`

**acceleration** — `meters_per_sec2`, `feet_per_sec2`, `g_unit`

**angle** — `degrees`, `radians`, `gradian`, `arc_minutes`, `arc_seconds`

**area** — `square_meters`, `square_feet`, `square_miles`, `acres`, `hectares`

**flow** — `gallons_per_min`, `cubic_meters_per_sec`, `cubic_feet_per_sec`,
`cubic_feet_per_min`, `litre_per_hour`, `litre_per_min`, `millilitre_per_min`, `lux`

**force** — `newton_meters`, `kilonewton_meters`, `newtons`, `kilonewtons`

**hash_rate** — `hashes_per_sec`, `kilohashes_per_sec`, `megahashes_per_sec`,
`gigahashes_per_sec`, `terahashes_per_sec`, `petahashes_per_sec`, `exahashes_per_sec`

**mass** — `milligram`, `gram`, `pound`, `kilogram`, `metric_ton`

**length** — `millimeter`, `inch`, `feet`, `meter`, `kilometer`, `mile`

**pressure** — `millibars`, `bars`, `kilobars`, `pascals`, `hectopascals`, `kilopascals`,
`inches_of_mercury`, `psi`

**radiation** — `becquerel`, `curie`, `gray`, `rad`, `sievert`, `millisievert`,
`microsievert`, `rem`, `exposure`, `roentgen`, `sievert_per_hour`,
`millisievert_per_hour`, `microsievert_per_hour`

## Picking a unit

| Data | Unit |
|---|---|
| Trace `duration` aggregation | `nanoseconds` (auto-scales to µs/ms/s) |
| Ratio or error rate (already ×100) | `percentage` |
| Memory, disk, payload size | `bytes` |
| Throughput | `bytes/sec` |
| CPU from `rate(container_cpu_usage_seconds_total[5m])` | `CPU`, or `mCPU` after ×1000 |
| Plain counts | `number` |
