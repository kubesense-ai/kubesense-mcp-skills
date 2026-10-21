#!/usr/bin/env bash
# Compare the generator's parse of rum.go with the catalog Go itself builds.
# Runs a throwaway Go program through `go run -overlay`, so nothing is written
# into kubeapi. Usage: scripts/verify-rum-field-catalog.sh [path-to-kubeapi]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
kubeapi="$(cd "${1:-${KUBEAPI_DIR:-$here/../../kubeapi}}" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/main.go" <<'GO'
package main

import (
	"encoding/json"
	"os"

	"go.kubesense.ai/api/observability/fieldcatalog"
)

func main() {
	out := map[string][]map[string]any{}
	for _, t := range fieldcatalog.RUMEventTypes {
		es, _ := fieldcatalog.RUM(t)
		rows := []map[string]any{}
		for _, e := range es {
			enum, platforms := e.EnumValues, e.Platforms
			if enum == nil {
				enum = []string{}
			}
			if platforms == nil {
				platforms = []string{}
			}
			rows = append(rows, map[string]any{
				"name": e.Name, "value": e.Value, "type": e.Type[0],
				"like":   fieldcatalog.AllowsLike(e),
				"group":  fieldcatalog.AllowsGrouping(e) && !fieldcatalog.RUMIsArrayColumn(t, e.Value),
				"filter": fieldcatalog.AllowsFiltering(e),
				"free":   e.IsFreeSearch != nil && *e.IsFreeSearch,
				"enum":   enum, "platforms": platforms,
			})
		}
		out[string(t)] = rows
	}
	json.NewEncoder(os.Stdout).Encode(out)
}
GO
printf '{"Replace":{"%s/observability/zz_rumdump/main.go":"%s/main.go"}}' "$kubeapi" "$tmp" >"$tmp/overlay.json"
(cd "$kubeapi" && go run -overlay "$tmp/overlay.json" ./observability/zz_rumdump) >"$tmp/go.json"
python3 -I "$here/gen-rum-field-catalog.py" --kubeapi "$kubeapi" --json >"$tmp/py.json"
python3 -I - "$tmp/go.json" "$tmp/py.json" <<'PY'
import json, sys
go, py = (json.load(open(p)) for p in sys.argv[1:3])
bad = 0
for t in go:
    if [r["name"] for r in go[t]] != [r["name"] for r in py[t]]:
        print(f"{t}: field list or order differs"); bad += 1; continue
    for g, p in zip(go[t], py[t]):
        if g != p:
            print(f"{t}.{g['name']}: go={g} generator={p}"); bad += 1
print("MISMATCH" if bad else f"ok: {sum(len(v) for v in go.values())} fields across {len(go)} event types match")
sys.exit(1 if bad else 0)
PY
