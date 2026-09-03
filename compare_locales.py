"""Compare two scraped knowledge base snapshots.

Article IDs are stable across locales (`/435/...` is the same article in every
language), so snapshots can be cross-referenced by ID rather than by title.

Usage:
    python compare_locales.py <dir_a> <dir_b>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def load(directory: Path) -> tuple[dict, dict[tuple[str, str], dict]]:
    meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    keyed: dict[tuple[str, str], dict] = {}
    for page in meta["pages"]:
        url = page["url"]
        tail = url.split("/Grepolis/", 1)[1]
        match = re.search(r"/(?:articles/)?(\d+)(?:/|$)", tail)
        keyed[(page["kind"], match.group(1) if match else "root")] = page
    return meta, keyed


def body_chars(directory: Path, page: dict) -> int:
    """Characters of article prose, excluding frontmatter."""
    if not page.get("local_path"):
        return 0
    text = (directory / page["local_path"]).read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return len(parts[2].strip()) if len(parts) > 2 else len(text)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1

    dir_a, dir_b = Path(argv[0]), Path(argv[1])
    meta_a, a = load(dir_a)
    meta_b, b = load(dir_b)

    def label(meta: dict, directory: Path) -> str:
        # Snapshots taken before the `locale` field was added fall back to the
        # locale embedded in the source URL.
        if "locale" in meta:
            return meta["locale"]
        match = re.search(r"/Grepolis/([a-z]{2}_[A-Z]{2})", meta.get("source", ""))
        return match.group(1) if match else directory.name

    label_a, label_b = label(meta_a, dir_a), label(meta_b, dir_b)

    print(f"{label_a}: {len(meta_a['pages'])} pages   ({dir_a})")
    print(f"{label_b}: {len(meta_b['pages'])} pages   ({dir_b})")

    only_a = sorted(set(a) - set(b), key=lambda k: (k[0], int(k[1]) if k[1].isdigit() else 0))
    only_b = sorted(set(b) - set(a), key=lambda k: (k[0], int(k[1]) if k[1].isdigit() else 0))
    shared = set(a) & set(b)

    print(f"\nshared articles : {len(shared)}")
    print(f"only in {label_a}  : {len(only_a)}")
    print(f"only in {label_b}  : {len(only_b)}")

    if only_a:
        print(f"\n--- Only in {label_a} ---")
        for key in only_a:
            print(f"  [{key[0]:7}] id={key[1]:>5}  {a[key]['title'][:66]}")
    if only_b:
        print(f"\n--- Only in {label_b} ---")
        for key in only_b:
            print(f"  [{key[0]:7}] id={key[1]:>5}  {b[key]['title'][:66]}")

    # Length gaps on shared articles reveal untranslated or abridged versions.
    print(f"\n--- Largest content gaps on shared articles ---")
    rows = []
    for key in shared:
        if a[key]["kind"] != "article":
            continue
        ca, cb = body_chars(dir_a, a[key]), body_chars(dir_b, b[key])
        if ca and cb:
            rows.append((cb - ca, ca, cb, a[key]["title"], b[key]["title"]))

    rows.sort()
    print(f"\n  {label_a} substantially longer:")
    for delta, ca, cb, ta, tb in rows[:8]:
        print(f"    {ca:>6} vs {cb:>6}  ({delta:+6})  {ta[:52]}")
    print(f"\n  {label_b} substantially longer:")
    for delta, ca, cb, ta, tb in rows[-8:][::-1]:
        print(f"    {ca:>6} vs {cb:>6}  ({delta:+6})  {tb[:52]}")

    total_a = sum(body_chars(dir_a, p) for p in meta_a["pages"] if p.get("local_path"))
    total_b = sum(body_chars(dir_b, p) for p in meta_b["pages"] if p.get("local_path"))
    print(f"\ntotal prose {label_a}: {total_a:,} chars")
    print(f"total prose {label_b}: {total_b:,} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
