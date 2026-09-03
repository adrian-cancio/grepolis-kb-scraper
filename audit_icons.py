"""Audit icon coverage in a scraped snapshot.

Reports which icons the pipeline resolved to a label and which ones are still
unlabeled, so lost table meaning can be spotted instead of silently shipped.

Usage:
    python audit_icons.py <locale> [--delay 0.5]
"""

from __future__ import annotations

import argparse
import collections
from bs4 import BeautifulSoup

import scrape_kb as kb


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locale", nargs="?", default="es_ES", choices=sorted(kb.LOCALES))
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    scope = kb.locale_base_url(args.locale)
    fetcher = kb.Fetcher(delay=args.delay, locale=args.locale)
    pages, raw_html, legend = kb.crawl(
        scope, fetcher, scope, max_pages=args.max_pages
    )

    # Count every icon occurrence and whether the legend covers it.
    resolved: collections.Counter[str] = collections.Counter()
    unresolved: collections.Counter[str] = collections.Counter()
    where: dict[str, set[str]] = collections.defaultdict(set)

    for page in pages:
        html = raw_html.get(page.url)
        if not html:
            continue
        content = kb._select_content(BeautifulSoup(html, "lxml"))
        if content is None:
            continue
        for img in content.find_all("img"):
            key = kb.icon_key(str(img.get("src", "")))
            cell = img.find_parent(["td", "th"])
            # Icons inside a cell that already has text are cosmetic.
            if cell is not None and not cell.get_text(strip=True):
                if key in legend:
                    resolved[key] += 1
                else:
                    unresolved[key] += 1
                    where[key].add(page.title)

    print("\n" + "=" * 66)
    print(f" ICON AUDIT — {args.locale}")
    print("=" * 66)
    print(f" legend entries      : {len(legend)}")
    print(f" icon-only cells     : {sum(resolved.values()) + sum(unresolved.values())}")
    print(f"   labeled           : {sum(resolved.values())}")
    print(f"   still unlabeled   : {sum(unresolved.values())}")
    total = sum(resolved.values()) + sum(unresolved.values())
    if total:
        print(f"   coverage          : {sum(resolved.values()) / total:.1%}")

    print("\n Learned labels:")
    for key, label in sorted(legend.items(), key=lambda kv: kv[1]):
        print(f"   {key[:8]}  {resolved[key]:>4}x  {label}")

    if unresolved:
        print("\n Unlabeled icons (data columns losing meaning):")
        for key, count in unresolved.most_common():
            sample = sorted(where[key])[:3]
            print(f"   {key[:8]}  {count:>4}x  e.g. {', '.join(s[:26] for s in sample)}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
