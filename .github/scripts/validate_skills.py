#!/usr/bin/env python3
"""Repo-shape checks: marketplace manifest, SKILL.md frontmatter, referenced paths.

Run from the repository root:  python3 .github/scripts/validate_skills.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTMATTER_LIMIT = 1024          # agentskills.io/specification
errors: list[str] = []


def ok(msg: str) -> None:
    print(f"  ok   {msg}")


def bad(msg: str) -> None:
    errors.append(msg)
    print(f"  FAIL {msg}")


def check_manifest() -> None:
    print("marketplace manifest")
    path = ROOT / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        return bad(".claude-plugin/marketplace.json is missing")
    try:
        manifest = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return bad(f"marketplace.json is not valid JSON: {e}")
    for key in ("name", "owner", "plugins"):
        if key not in manifest:
            bad(f"marketplace.json has no {key!r}")
    for plugin in manifest.get("plugins", []):
        for rel in plugin.get("skills", []):
            if (ROOT / rel / "SKILL.md").is_file():
                ok(f"{plugin['name']} -> {rel}")
            else:
                bad(f"{plugin['name']} points at {rel}, which has no SKILL.md")


def check_frontmatter() -> None:
    print("SKILL.md frontmatter")
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    if not skills:
        return bad("no skills/*/SKILL.md found")
    for f in skills:
        m = re.match(r"---\n(.*?)\n---\n", f.read_text(), re.S)
        if not m:
            bad(f"{f.relative_to(ROOT)} has no YAML frontmatter")
            continue
        fm = m.group(1)
        if len(fm) > FRONTMATTER_LIMIT:
            bad(f"{f.relative_to(ROOT)} frontmatter is {len(fm)} chars (limit {FRONTMATTER_LIMIT})")
        name_m = re.search(r"^name: (.+)$", fm, re.M)
        desc_m = re.search(r"^description: (.+)$", fm, re.M)
        if not name_m or not name_m.group(1).strip():
            bad(f"{f.relative_to(ROOT)} has no non-empty 'name'")
            continue
        if not desc_m or not desc_m.group(1).strip():
            bad(f"{f.relative_to(ROOT)} has no non-empty 'description'")
        name = name_m.group(1).strip()
        if not re.fullmatch(r"[A-Za-z0-9-]+", name):
            bad(f"{f.relative_to(ROOT)} name {name!r}: letters, numbers and hyphens only")
        elif name != f.parent.name:
            bad(f"{f.relative_to(ROOT)} name {name!r} != directory {f.parent.name!r}")
        else:
            ok(f"{f.relative_to(ROOT)} ({len(fm)} chars, name matches directory)")


def check_referenced_paths() -> None:
    print("paths referenced from SKILL.md")
    for f in sorted((ROOT / "skills").glob("*/SKILL.md")):
        refs = sorted(set(re.findall(r"`((?:references|scripts)/[\w.-]+)`", f.read_text())))
        if not refs:
            ok(f"{f.relative_to(ROOT)} references no sibling files")
        for rel in refs:
            if (f.parent / rel).exists():
                ok(f"{f.parent.name}/{rel}")
            else:
                bad(f"{f.relative_to(ROOT)} references {rel}, which does not exist")


def main() -> int:
    for check in (check_manifest, check_frontmatter, check_referenced_paths):
        check()
        print()
    if errors:
        print(f"FAILED ({len(errors)} problem{'s' if len(errors) > 1 else ''})")
        return 1
    print("all repo checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
