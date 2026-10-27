#!/usr/bin/env python3
"""Check that every relative markdown link in the repo resolves, anchors included.

    python3 scripts/check-links.py            # exit 1 if any link is broken
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r"\]\(([^)\s]+)\)")
FENCE = re.compile(r"^\s*```")


def slug(heading):
    # GitHub keeps underscores in anchors: `by_count` -> by_count.
    h = re.sub(r"[`*]", "", heading.strip().lower())
    h = re.sub(r"[^\w\s-]", "", h)
    return re.sub(r"\s", "-", h)


def anchors(path):
    out, in_fence = set(), False
    for line in open(path, encoding="utf-8"):
        if FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and line.startswith("#"):
            out.add(slug(line.lstrip("#")))
    return out


def md_files():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in ("node_modules", ".git")]
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(d, f)


def main():
    bad, cache = [], {}
    for path in md_files():
        in_fence = False
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            if FENCE.match(line):
                in_fence = not in_fence
            if in_fence:
                continue
            for target in LINK.findall(line):
                if re.match(r"[a-z]+:", target) or target.startswith("#") and False:
                    continue
                file_part, _, frag = target.partition("#")
                dest = path if not file_part else os.path.normpath(os.path.join(os.path.dirname(path), file_part))
                if not os.path.exists(dest):
                    bad.append(f"{os.path.relpath(path, ROOT)}:{n}: missing file {target}")
                elif frag and dest.endswith(".md"):
                    cache.setdefault(dest, anchors(dest))
                    if frag.lower() not in cache[dest]:
                        bad.append(f"{os.path.relpath(path, ROOT)}:{n}: missing anchor {target}")
    print("\n".join(bad) if bad else "all relative links resolve")
    sys.exit(1 if bad else 0)


main()
