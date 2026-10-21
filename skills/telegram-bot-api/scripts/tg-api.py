#!/usr/bin/env python3
"""Query and refresh a local snapshot of the Telegram Bot API reference.

The snapshot (spec.json) is parsed straight from core.telegram.org/bots/api, so
`show` prints the real parameter table rather than a recollection of one.

    tg-api.py version                 # snapshot version + live version, compared
    tg-api.py show sendMessage        # full parameter table for a method or type
    tg-api.py search photo            # methods/types whose name or summary matches
    tg-api.py list methods [regex]    # names only
    tg-api.py fields sendPhoto        # parameter names only, one per line
    tg-api.py since 10.0              # changelog entries at or after a version
    tg-api.py refresh                 # re-fetch and rewrite spec.json
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "spec.json")
API_URL = "https://core.telegram.org/bots/api"
CHANGELOG_URL = "https://core.telegram.org/bots/api-changelog"


# --------------------------------------------------------------------------- fetch

def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "tg-api-skill/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def _body(page: str) -> str:
    m = re.search(r'<div id="dev_page_content"[^>]*>(.*)', page, re.S)
    b = m.group(1) if m else page
    i = b.find('<div class="footer_wrap">')
    return b[:i] if i > 0 else b


def _text(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def refresh() -> dict:
    body = _body(_get(API_URL))

    sections = [(m.start(), _text(m.group(1))) for m in re.finditer(r"<h3>(.*?)</h3>", body, re.S)]

    def section_of(pos: int) -> str:
        cur = ""
        for p, name in sections:
            if p <= pos:
                cur = name
            else:
                break
        return cur

    entries = {}
    h4s = list(re.finditer(r"<h4>(.*?)</h4>", body, re.S))
    for i, m in enumerate(h4s):
        name = _text(m.group(1))
        chunk = body[m.end():(h4s[i + 1].start() if i + 1 < len(h4s) else len(body))]
        tbl = re.search(r'<table class="table">(.*?)</table>', chunk, re.S)
        desc_html = chunk[:tbl.start()] if tbl else chunk
        desc = " ".join(x for x in (_text(p) for p in re.findall(r"<p>(.*?)</p>", desc_html, re.S)) if x)
        cols, rows = [], []
        if tbl:
            head = re.search(r"<thead>(.*?)</thead>", tbl.group(1), re.S)
            if head:
                cols = [_text(c) for c in re.findall(r"<th>(.*?)</th>", head.group(1), re.S)]
            for tr in re.findall(r"<tr>(.*?)</tr>", tbl.group(1), re.S):
                tds = re.findall(r"<td>(.*?)</td>", tr, re.S)
                if tds:
                    rows.append([_text(t) for t in tds])
        entries[name] = {"name": name, "section": section_of(m.start()),
                         "desc": desc, "cols": cols, "rows": rows}

    changelog = _text(_body(_get(CHANGELOG_URL)))
    version = "unknown"
    vm = re.search(r"Bot API (\d+\.\d+)", changelog)
    if vm:
        version = vm.group(1)

    # changelog entries, newest first: (version, date, [bullet, ...])
    cl_body = _body(_get(CHANGELOG_URL))
    releases = []
    heads = list(re.finditer(r"<h4>(?:<a\b[^>]*>.*?</a>)?(.*?)</h4>", cl_body, re.S))
    for i, h in enumerate(heads):
        seg = cl_body[h.end():(heads[i + 1].start() if i + 1 < len(heads) else len(cl_body))]
        v = re.search(r"<p><strong>Bot API ([\d.]+)</strong></p>", seg)
        bullets = [_text(li) for li in re.findall(r"<li>(.*?)</li>", seg, re.S)]
        releases.append({"date": _text(h.group(1)), "version": v.group(1) if v else None,
                         "bullets": bullets})

    spec = {"version": version, "source": API_URL, "entries": entries, "releases": releases}
    with open(SPEC, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return spec


def load() -> dict:
    if not os.path.exists(SPEC):
        sys.exit("spec.json missing - run: tg-api.py refresh")
    with open(SPEC, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- commands

def _is_method(name: str) -> bool:
    return bool(re.match(r"^[a-z]\w*$", name))


def cmd_version(spec: dict) -> None:
    print(f"snapshot: Bot API {spec['version']}")
    try:
        live = re.search(r"Bot API (\d+\.\d+)", _text(_body(_get(CHANGELOG_URL))))
        live_v = live.group(1) if live else "?"
    except Exception as e:  # offline is not an error worth failing on
        print(f"live:     unavailable ({e.__class__.__name__})")
        return
    print(f"live:     Bot API {live_v}")
    if live_v != spec["version"]:
        print(f"\nSTALE - run `{os.path.basename(__file__)} refresh`, then re-read the skill's"
              f" references/ for anything the new release touches.")


def cmd_show(spec: dict, name: str) -> None:
    ents = spec["entries"]
    key = next((k for k in ents if k.lower() == name.lower()), None)
    if not key:
        near = [k for k in ents if name.lower() in k.lower()][:12]
        sys.exit(f"no entry {name!r}" + (f"\ndid you mean: {', '.join(near)}" if near else ""))
    e = ents[key]
    print(f"# {e['name']}   [{e['section']}]")
    print(f"{API_URL}#{e['name'].lower()}\n")
    if e["desc"]:
        print(e["desc"] + "\n")
    if e["rows"]:
        w = max(len(r[0]) for r in e["rows"])
        for r in e["rows"]:
            req = f" ({r[2]})" if len(r) == 4 else ""
            print(f"  {r[0]:<{w}}  {r[1]}{req}\n      {r[-1]}")


def cmd_search(spec: dict, term: str) -> None:
    t = term.lower()
    for k, e in spec["entries"].items():
        if t in k.lower() or t in e["desc"].lower():
            kind = "method" if _is_method(k) else "type  "
            print(f"{kind} {k:<44} {e['desc'][:90]}")


def cmd_list(spec: dict, what: str, pattern: str | None) -> None:
    rx = re.compile(pattern, re.I) if pattern else None
    for k in spec["entries"]:
        if what.startswith("method") and not _is_method(k):
            continue
        if what.startswith("type") and not re.match(r"^[A-Z]\w*$", k):
            continue
        if rx and not rx.search(k):
            continue
        print(k)


def cmd_fields(spec: dict, name: str) -> None:
    ents = spec["entries"]
    key = next((k for k in ents if k.lower() == name.lower()), None)
    if not key:
        sys.exit(f"no entry {name!r}")
    for r in ents[key]["rows"]:
        print(r[0])


def cmd_since(spec: dict, version: str) -> None:
    def tup(v):
        return tuple(int(x) for x in v.split("."))
    floor = tup(version)
    for rel in spec["releases"]:
        if not rel["version"] or tup(rel["version"]) < floor:
            continue
        print(f"\n## Bot API {rel['version']} - {rel['date']}")
        for b in rel["bullets"]:
            print(f"  - {b}")


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = argv[0]
    if cmd == "refresh":
        spec = refresh()
        print(f"spec.json rewritten: Bot API {spec['version']}, "
              f"{len(spec['entries'])} entries, {len(spec['releases'])} releases")
        return
    spec = load()
    if cmd == "version":
        cmd_version(spec)
    elif cmd == "show" and len(argv) > 1:
        cmd_show(spec, argv[1])
    elif cmd == "search" and len(argv) > 1:
        cmd_search(spec, argv[1])
    elif cmd == "list" and len(argv) > 1:
        cmd_list(spec, argv[1], argv[2] if len(argv) > 2 else None)
    elif cmd == "fields" and len(argv) > 1:
        cmd_fields(spec, argv[1])
    elif cmd == "since" and len(argv) > 1:
        cmd_since(spec, argv[1])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
