#!/usr/bin/env python3
"""Regenerate the tables in kubesense-dashboards/references/metrics-functions.md.

The source is the function catalog kubeapi generates at
schema/gen/metrics-functions.json. The script rewrites only the text between
the BEGIN/END GENERATED markers. Run from the repo root:

    python3 scripts/sync-builder-functions.py ../kubeapi/schema/gen/metrics-functions.json
"""

import json
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / (
    "kubesense-dashboards/references/metrics-functions.md"
)
BEGIN = "<!-- BEGIN GENERATED: scripts/sync-builder-functions.py -->"
END = "<!-- END GENERATED -->"

CATEGORIES = [
    ("rollup", "Rollup"),
    ("transform", "Transform"),
    ("label", "Label"),
    ("aggregate", "Aggregate"),
    ("operator", "Operator"),
]


def kind_text(kind: dict) -> str:
    name = kind["kind"]
    if name == "number":
        bounds = []
        if "min" in kind and "max" in kind:
            bounds.append(f"{kind['min']}–{kind['max']}")
        elif "min" in kind:
            bounds.append(f"≥ {kind['min']}")
        if kind.get("integer"):
            bounds.append("integer")
        return "number" + (f" ({', '.join(bounds)})" if bounds else "")
    if name == "numbers":
        return "number list"
    if name == "window":
        return "window"
    if name == "duration":
        return "duration"
    if name == "timestamp":
        return "timestamp"
    if name == "string":
        return {"label": "label name", "text": "text", "regex": "regex"}[kind["role"]]
    if name == "enum":
        return " \\| ".join(f"`{v}`" for v in kind["values"])
    if name == "labels":
        return "label list"
    if name == "pairs":
        return "list of `[" + ", ".join(kind["roles"]) + "]` pairs"
    if name == "rollups":
        return "rollup-function names"
    if name == "flag":
        return "`true`"
    return name


def params_text(spec: dict) -> str:
    parts = []
    for param in spec["params"]:
        text = f"`{param['name']}`: {kind_text(param['kind'])}"
        if param.get("optional"):
            text += ", optional"
        elif "default" in param:
            text += f", default `{json.dumps(param['default'])}`"
        if param.get("aliases"):
            text += " (also `" + "`, `".join(param["aliases"]) + "`)"
        parts.append(text)
    return "<br>".join(parts) if parts else "none"


def example_text(example: dict) -> str:
    """The example's arguments and rendered PromQL, with any preceding functions
    and query-level selectorModifiers it relies on."""
    compact = {"separators": (", ", ": ")}
    text = f"`{json.dumps(example.get('args', {}), **compact)}`"
    if example.get("selectorModifiers"):
        text += f" with `selectorModifiers: {json.dumps(example['selectorModifiers'], **compact)}`"
    if example.get("chain"):
        text = "after " + " → ".join(f"`{step['name']}`" for step in example["chain"]) + ": " + text
    promql = example.get("promql", "").replace("|", "\\|")
    return f"{text} → `{promql}`"


def render(catalog: dict) -> str:
    out = [BEGIN, ""]
    for category, title in CATEGORIES:
        names = sorted(n for n, s in catalog.items() if s["category"] == category)
        out += [
            f"### {title} ({len(names)})",
            "",
            "| Function | `type` | Arguments | Example → PromQL |",
            "|---|---|---|---|",
        ]
        for name in names:
            spec = catalog[name]
            label = f"`{name}`" + ("" if spec.get("menu", True) else " (legacy)")
            out.append(
                f"| {label} | `{spec['type']}` | {params_text(spec)} "
                f"| {example_text(spec.get('example', {}))} |"
            )
        out.append("")
    out.append(END)
    return "\n".join(out)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    catalog = json.loads(Path(sys.argv[1]).read_text())
    current = TARGET.read_text()
    start, stop = current.index(BEGIN), current.index(END) + len(END)
    TARGET.write_text(current[:start] + render(catalog) + current[stop:])
    print(f"wrote {TARGET}")


if __name__ == "__main__":
    main()
