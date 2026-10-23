#!/usr/bin/env python3
"""Regenerate kubesense-rum/references/field-catalog.md from kubeapi's RUM catalog.

Reads kubeapi/observability/fieldcatalog/rum.go and rum_units.go and evaluates
the small constructor DSL they use (lowCards, exacts, numbers, flags, frees,
hidden, free, exactAs, withEnum, slices.Concat, rumCatalog). It does not run Go.

    python3 scripts/gen-rum-field-catalog.py [--kubeapi PATH] [--out PATH]
    python3 scripts/gen-rum-field-catalog.py --check      # exit 1 if the file is stale
    python3 scripts/gen-rum-field-catalog.py --json       # print the parsed catalog

--kubeapi defaults to $KUBEAPI_DIR, then ../../kubeapi relative to this
repo's parent workspace (a ksw workspace puts kubeapi next to this repo).
The catalog is the source of truth: rerun this after any change to rum.go, then run
scripts/verify-rum-field-catalog.sh to compare this parser with the catalog Go builds.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO, "kubesense-rum", "references", "field-catalog.md")

EVENT_ORDER = ["session", "view", "action", "error", "resource", "long_task"]
GO_CONST_TO_TYPE = {
    "RUMSession": "session", "RUMView": "view", "RUMAction": "action",
    "RUMError": "error", "RUMResource": "resource", "RUMLongTask": "long_task",
}
PLATFORM_CONST = {"RUMPlatformBrowser": "browser", "RUMPlatformMobile": "mobile"}


# ---- tokenizer and parser for the Go subset -------------------------------

TOKEN = re.compile(r'\s*(?:(//[^\n]*)|("(?:[^"\\]|\\.)*")|([A-Za-z_][\w.]*)|(\d[\d_]*)|([(){},:]))')


def tokenize(src):
    out, pos = [], 0
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m:
            if src[pos:].strip() == "":
                break
            pos += 1  # operators the DSL never needs (=, [], &, ...) are skipped
            continue
        pos = m.end()
        comment, string, ident, number, punct = m.groups()
        if comment:
            continue
        if string:
            out.append(("str", json.loads(string)))
        elif ident:
            out.append(("id", ident))
        elif number:
            out.append(("num", int(number.replace("_", ""))))
        else:
            out.append(("p", punct))
    return out


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def expr(self):
        kind, val = self.t[self.i]
        self.i += 1
        if kind in ("str", "num"):
            return (kind, val)
        if kind == "id":
            if self.peek() == ("p", "("):
                self.i += 1
                args = []
                while self.peek() != ("p", ")"):
                    args.append(self.expr())
                    if self.peek() == ("p", ","):
                        self.i += 1
                self.i += 1
                return ("call", val, args)
            return ("id", val)
        raise ValueError(f"unexpected token {kind} {val!r} at {self.i}")


def find_block(src, header):
    """Text of the {...} block whose opener follows `header`."""
    start = src.index(header)
    open_at = src.index("{", start)
    depth = 0
    for j in range(open_at, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[open_at + 1:j]
    raise ValueError(f"unbalanced block after {header}")


def var_exprs(src):
    """name -> AST for every top-level `var name = expr` in the source."""
    exprs = {}
    for m in re.finditer(r"^var (\w+) = ", src, re.M):
        toks = tokenize(src[m.end():m.end() + 6000])
        # Stop at the first top-level token that begins another declaration.
        exprs[m.group(1)] = Parser(toks).expr()
    return exprs


# ---- the constructors rum.go defines --------------------------------------

def entry(name, value, typ):
    return {"name": name, "value": value, "type": typ, "like": None, "group": None,
            "filter": None, "free": False, "enum": [], "platforms": []}


def copy_entry(e):
    c = dict(e)
    c["enum"] = list(e["enum"])
    c["platforms"] = list(e["platforms"])
    return c


def mark(e, **kw):
    e = copy_entry(e)
    e.update(kw)
    return e


def exact_as(name, value):
    return mark(entry(name, value, "string"), like=False)


class Evaluator:
    def __init__(self, exprs):
        self.exprs, self.cache = exprs, {}

    def var(self, name):
        if name not in self.cache:
            self.cache[name] = self.ev(self.exprs[name])
        return self.cache[name]

    def ev(self, node):
        kind = node[0]
        if kind in ("str", "num"):
            return node[1]
        if kind == "id":
            return self.var(node[1])
        _, fn, raw = node
        a = [self.ev(x) for x in raw]
        many = lambda f: [f(n) for n in a]
        table = {
            "lowCard": lambda: entry(a[0], a[0], "string"),
            "exact": lambda: exact_as(a[0], a[0]),
            "exactAs": lambda: exact_as(a[0], a[1]),
            "number": lambda: entry(a[0], a[0], "float"),
            "flag": lambda: entry(a[0], a[0], "boolean"),
            "rumEntry": lambda: entry(a[0], a[1], a[2]),
            "hidden": lambda: mark(a[0], filter=False, group=False),
            "free": lambda: mark(a[0], group=False, free=True),
            "withEnum": lambda: mark(a[0], enum=list(a[1:])),
            "entries": lambda: list(a),
            "lowCards": lambda: many(lambda n: entry(n, n, "string")),
            "exacts": lambda: many(lambda n: exact_as(n, n)),
            "numbers": lambda: many(lambda n: entry(n, n, "float")),
            "flags": lambda: many(lambda n: entry(n, n, "boolean")),
            "frees": lambda: many(lambda n: mark(exact_as(n, n), group=False, free=True)),
            "slices.Concat": lambda: [e for part in a for e in part],
        }
        return table[fn]()


# ---- catalog assembly -------------------------------------------------------

def parse_platforms(src):
    body = find_block(src, "var rumPlatformFields")
    out = {}
    for m in re.finditer(r'"(\w+)":\s*\{(\w+)\}', body):
        out[m.group(1)] = [PLATFORM_CONST[m.group(2)]]
    return out


def parse_set(src, header):
    return set(re.findall(r'"(\w+)":\s*true', find_block(src, header)))


def effective_group(e, nanos):
    if e["group"] is False or e["name"] in nanos:
        return False
    return True


def build(kubeapi):
    base = os.path.join(kubeapi, "observability", "fieldcatalog")
    rum = open(os.path.join(base, "rum.go")).read()
    units = open(os.path.join(base, "rum_units.go")).read()

    platforms = parse_platforms(rum)
    arrays = parse_set(rum, "var rumArrayColumns")
    nanos = parse_set(units, "var rumNanosecondColumns")
    suffixes = [("_ms", 1_000_000), ("_s", 1_000_000_000)]

    ev = Evaluator(var_exprs(rum))

    registry = {}
    reg_body = find_block(rum, "var rumRegistry")
    for m in re.finditer(r"(RUM\w+):\s*rumCatalog\(", reg_body):
        call = Parser(tokenize(reg_body[m.end() - len("rumCatalog("):])).expr()
        _, _, args = call
        etype = GO_CONST_TO_TYPE[args[0][1]]
        groups = [ev.ev(g) for g in args[1:]]
        registry[etype] = [e for g in groups for e in g]

    catalogs = {}
    for etype in EVENT_ORDER:
        base_entries = [copy_entry(e) for e in registry[etype]]
        for e in base_entries:
            e["platforms"] = list(platforms.get(e["name"], []))
        out = list(base_entries)
        for e in base_entries:
            if e["name"] != e["value"] or e["name"] not in nanos:
                continue
            for suffix, _ in suffixes:
                d = entry(e["name"] + suffix, e["name"], "float")
                d["group"] = False
                d["platforms"] = list(e["platforms"])
                d["unit_of"] = e["name"]
                out.append(d)
        for e in out:
            is_array = e["value"] in arrays or (etype == "view" and e["value"] == "ip")
            if is_array:
                e["group"] = False
                e["array"] = True
        names = [e["name"] for e in out]
        dup = {n for n in names if names.count(n) > 1}
        if dup:
            raise SystemExit(f"{etype}: duplicate field names {sorted(dup)}")
        catalogs[etype] = out
    return catalogs, nanos


def to_json(catalogs, nanos):
    """Normalised view compared against the Go dump in the verification step."""
    out = {}
    for etype, es in catalogs.items():
        rows = []
        for e in es:
            rows.append({
                "name": e["name"], "value": e["value"], "type": e["type"],
                "like": e["type"] == "string" and e["like"] is not False,
                "group": e["group"] is not False,
                "filter": e["filter"] is not False,
                "free": e["free"], "enum": e["enum"], "platforms": e["platforms"],
            })
        out[etype] = rows
    return out


# ---- markdown ---------------------------------------------------------------

TYPE_WORD = {"string": "string", "float": "number", "boolean": "boolean"}


def yn(b):
    return "yes" if b else "no"


def render(catalogs, nanos):
    lines = [
        "# RUM Field Catalog",
        "",
        "<!-- Generated by scripts/gen-rum-field-catalog.py from",
        "     kubeapi/observability/fieldcatalog/rum.go and rum_units.go. Do not edit by hand. -->",
        "",
        "The fields each RUM event type accepts in `where`, `group_by_fields`, `fields` and",
        "`sort_by`. Type the **Field** column. Rules for reading the columns are in",
        "[SKILL.md](../SKILL.md#rules); the short version:",
        "",
        "- **LIKE**: `yes` means `LIKE` / `ILIKE` are accepted. `no` means the column is not",
        "  low-cardinality, so use `=` or `IN`. `-` means not a string.",
        "- **Group**: `yes` means the field can be a `group_by_fields` entry. Array fields,",
        "  free-search ids and text, raw nanosecond durations and `_ms` / `_s` fields are `no`.",
        "- **Platform**: `browser` or `mobile` means only that platform's SDK sends the field.",
        "  Empty means every platform. Explorer queries do not enforce it: a field the",
        "  application's SDK never sends is just empty.",
        "- **boolean** fields take `true` or `false`.",
        "- **Storage** is shown only where it differs from the field name. Type the field name;",
        "  a storage name that differs is rejected.",
        "- Every field also accepts `feature_flag.<key>` and, with `is_attribute`, an `@key`",
        "  attribute. See SKILL.md.",
        "",
    ]
    for etype in EVENT_ORDER:
        es = catalogs[etype]
        shown = [e for e in es if e["filter"] is not False or e["group"] is not False]
        hidden = [e["name"] for e in es if e["filter"] is False and e["group"] is False]
        raw_units = [e for e in es if "unit_of" not in e]
        unit_bases = [e["name"] for e in raw_units if e["name"] in nanos and e["name"] == e["value"]]
        main = [e for e in shown if "unit_of" not in e]
        lines += [
            f"## `rum_{etype}` ({len(main)} fields, plus {len(unit_bases) * 2} `_ms` / `_s` fields)",
            "",
        ]
        lines.append("| Field | Type | LIKE | Group | Platform | Storage | Notes |")
        lines.append("|---|---|---|---|---|---|---|")
        for e in main:
            notes = []
            if e["name"] in nanos:
                notes.append("nanoseconds; use `" + e["name"] + "_ms` / `_s` to filter")
            if e.get("array"):
                notes.append("list; filter only (`=` is membership)")
            if e["free"]:
                notes.append("free search")
            if e["enum"]:
                notes.append("values: " + " ".join(f"`{v}`" for v in e["enum"]))
            like = "-" if e["type"] != "string" else yn(e["like"] is not False)
            storage = f"`{e['value']}`" if e["value"] != e["name"] else ""
            lines.append(
                f"| `{e['name']}` | {TYPE_WORD[e['type']]} | {like} | "
                f"{yn(effective_group(e, nanos))} | {'/'.join(e['platforms'])} | {storage} | {'; '.join(notes)} |"
            )
        lines.append("")
        if unit_bases:
            lines.append(
                "Duration variants: `<name>_ms` and `<name>_s` (number; filter and measure only) for "
                + ", ".join(f"`{n}`" for n in unit_bases)
                + "."
            )
            lines.append("")
        if hidden:
            lines.append("Not filterable or groupable: " + ", ".join(f"`{h}`" for h in hidden) + ".")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def default_kubeapi():
    env = os.environ.get("KUBEAPI_DIR")
    if env:
        return env
    return os.path.join(os.path.dirname(REPO), "kubeapi")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kubeapi", default=default_kubeapi())
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    catalogs, nanos = build(args.kubeapi)
    if args.json:
        json.dump(to_json(catalogs, nanos), sys.stdout, indent=1, sort_keys=True)
        print()
        return
    text = render(catalogs, nanos)
    if args.check:
        current = open(args.out).read() if os.path.exists(args.out) else ""
        if current != text:
            print(f"{args.out} is stale; rerun scripts/gen-rum-field-catalog.py", file=sys.stderr)
            sys.exit(1)
        return
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(text)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
