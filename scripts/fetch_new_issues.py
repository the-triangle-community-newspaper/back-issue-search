#!/usr/bin/env python3
"""
Monthly incremental updater for The Triangle back-issue search.

- Re-reads the public "Back Issues" listing page (just the HTML page, not any
  PDFs) to refresh scripts/issues_manifest.json with the current set of
  issues and their live URLs.
- Compares that against the issues already indexed in site/issues/.
- For any issue that's new (i.e. published since the last run), downloads
  ONLY that issue's PDF, extracts its text, writes a stub page, and
  immediately discards the PDF -- nothing is ever stored in this repo except
  the extracted text.
- Existing, already-indexed issues are never re-downloaded.

Intended to run monthly via GitHub Actions (see
.github/workflows/build-and-deploy.yml), a couple of days after the
publisher's usual first-of-the-month publish date, but is idempotent and
safe to run manually or more often -- it's a no-op if nothing new is found.
"""
import json
import re
import sys
from html import escape
from pathlib import Path

import fitz  # pymupdf
import requests
from bs4 import BeautifulSoup

BACK_ISSUES_URL = "https://thetriangle.org.au/back-issues/"
ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = Path(__file__).resolve().parent / "issues_manifest.json"
ISSUES_DIR = ROOT / "site" / "issues"

MONTHS = {m.lower(): i + 1 for i, m in enumerate([
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
])}
MONTH_NAMES = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
               7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TriangleSearchBot/1.0)"}


def parse_manifest_from_page(html: str):
    soup = BeautifulSoup(html, "lxml")
    current_year = None
    results = []
    for el in soup.descendants:
        name = getattr(el, "name", None)
        if name == "h2":
            t = el.get_text(strip=True)
            if re.fullmatch(r"20\d{2}", t):
                current_year = int(t)
        elif name == "a" and el.get("href", "").lower().endswith(".pdf"):
            label = el.get_text(strip=True).lower().rstrip(",").strip()
            if label in MONTHS and current_year:
                results.append({
                    "year": current_year,
                    "month": MONTHS[label],
                    "url": el["href"],
                })
    return results


def write_stub(year: int, month: int, url: str, page_texts: list[str]):
    label = f"{MONTH_NAMES[month]} {year}"
    date_str = f"{year:04d}-{month:02d}-01"
    full_text = "\n\n".join(page_texts)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(label)}</title>
</head>
<body>
<main data-pagefind-body
      data-pagefind-filter="year:{year}">
<h1 data-pagefind-meta="title">{escape(label)}</h1>
<a data-pagefind-meta="pdf[href]" href="{escape(url)}" data-pagefind-ignore style="display:none">PDF</a>
<span data-pagefind-meta="date" data-pagefind-sort="date" data-pagefind-ignore style="display:none">{date_str}</span>
<pre>{escape(full_text)}</pre>
</main>
</body>
</html>
"""
    (ISSUES_DIR / f"{year:04d}-{month:02d}.html").write_text(html, encoding="utf-8")
    print(f"  indexed {label} ({len(page_texts)} pages, {len(full_text)} chars) -> {url}")


def main():
    print(f"Fetching {BACK_ISSUES_URL} ...")
    resp = requests.get(BACK_ISSUES_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    live_issues = parse_manifest_from_page(resp.text)
    if not live_issues:
        print("WARNING: parsed 0 issues from the back-issues page -- page structure "
              "may have changed. Leaving existing manifest/index untouched.")
        return 1

    # Refresh the manifest to match the live page exactly (also drops any
    # issues the publisher has since delinked).
    MANIFEST_PATH.write_text(json.dumps(live_issues, indent=2), encoding="utf-8")
    print(f"Refreshed manifest: {len(live_issues)} issue(s) currently listed.")

    already_indexed = {p.stem for p in ISSUES_DIR.glob("*.html")}
    new_count = 0
    for item in live_issues:
        key = f"{item['year']:04d}-{item['month']:02d}"
        if key in already_indexed:
            continue
        url = item["url"]
        if not url:
            continue
        print(f"New issue found: {MONTH_NAMES[item['month']]} {item['year']} -> {url}")
        try:
            pdf_resp = requests.get(url, headers=HEADERS, timeout=60)
            pdf_resp.raise_for_status()
            doc = fitz.open(stream=pdf_resp.content, filetype="pdf")
            page_texts = [doc[i].get_text() for i in range(doc.page_count)]
            doc.close()
        except Exception as e:
            print(f"  FAILED to fetch/extract {url}: {e}")
            continue
        write_stub(item["year"], item["month"], url, page_texts)
        new_count += 1

    print(f"Done. {new_count} new issue(s) indexed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
