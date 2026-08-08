#!/usr/bin/env python3
"""
Process a batch of locally-supplied Triangle newspaper PDFs:
- find every real PDF in a given directory (recursively, ignoring
  macOS zip cruft like __MACOSX and ._ files)
- work out which year/month each one is from its filename
- look up the matching public URL on thetriangle.org.au from
  issues_manifest.json (scraped once from the back-issues page)
- extract full text and write a Pagefind-ready stub page into site/issues/

Usage: python scripts/process_batch.py <directory-with-pdfs>
"""
import json
import re
import sys
from pathlib import Path
from html import escape

import os

import fitz  # pymupdf

FORCE = os.environ.get("FORCE_REPROCESS") == "1"

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"
ISSUES_DIR = SITE_DIR / "issues"
MANIFEST_PATH = Path(__file__).resolve().parent / "issues_manifest.json"
UNMATCHED_LOG = Path(__file__).resolve().parent / "unmatched.json"

MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH_FULL = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
MONTH_NAMES = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
               7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}


def load_manifest():
    manifest = json.loads(MANIFEST_PATH.read_text())
    lookup = {(i["year"], i["month"]): i["url"] for i in manifest}
    return lookup


def guess_year_month(filename):
    """Try to pull a (year, month) out of a filename like
    '51-Triangle-Feb-07.pdf', 'April-2011.pdf', '2013.031.pdf', etc."""
    name = filename.lower()

    # YYYY.MM(.extra) pattern, e.g. 2013.031.pdf -> 2013, 03
    m = re.search(r"(20\d{2})[.\-_](\d{2})", name)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return year, month

    # full month name + year, e.g. April-2011 or 2011-april
    for mname, mnum in MONTH_FULL.items():
        if mname in name:
            y = re.search(r"(20\d{2})", name)
            if y:
                return int(y.group(1)), mnum

    # full month name + 2-digit year, e.g. April-23, June-23, July-23
    for mname, mnum in MONTH_FULL.items():
        m = re.search(rf"{mname}[-_]?(\d{{2}})\b", name)
        if m:
            yy = int(m.group(1))
            year = 2000 + yy if yy < 90 else 1900 + yy
            return year, mnum

    # abbreviated month + 2-digit year, e.g. Feb-07, Aug-08
    for mabbr, mnum in MONTH_ABBR.items():
        m = re.search(rf"{mabbr}[-_]?(\d{{2}})\b", name)
        if m:
            yy = int(m.group(1))
            year = 2000 + yy if yy < 90 else 1900 + yy
            return year, mnum

    return None, None


def iter_pdfs(directory):
    for p in sorted(Path(directory).rglob("*.pdf")):
        if "__MACOSX" in p.parts or p.name.startswith("._"):
            continue
        yield p


def process_pdf(path, lookup, unmatched):
    year, month = guess_year_month(path.name)
    if year is None:
        unmatched.append({"file": str(path), "reason": "could not parse year/month from filename"})
        print(f"  SKIP (no date match): {path.name}")
        return False

    stub_path = ISSUES_DIR / f"{year:04d}-{month:02d}.html"
    if stub_path.exists() and not FORCE:
        print(f"  already indexed: {MONTH_NAMES[month]} {year} ({path.name})")
        return True

    url = lookup.get((year, month))
    if not url:
        unmatched.append({
            "file": str(path), "year": year, "month": month,
            "reason": "no matching URL found on back-issues page for this year/month",
        })
        print(f"  WARNING no public URL for {MONTH_NAMES[month]} {year} ({path.name}) -- indexing without a link")
        url = ""

    label = f"{MONTH_NAMES[month]} {year}"
    date_str = f"{year:04d}-{month:02d}-01"

    try:
        doc = fitz.open(path)
        page_texts = [doc[i].get_text() for i in range(doc.page_count)]
        doc.close()
    except Exception as e:
        unmatched.append({"file": str(path), "reason": f"failed to read PDF: {e}"})
        print(f"  FAILED to read {path.name}: {e}")
        return False

    pages_html = "\n".join(
        f'<h2 id="page-{i}">Page {i}</h2>\n<pre>{escape(text)}</pre>'
        for i, text in enumerate(page_texts, start=1)
    )
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
{pages_html}
</main>
</body>
</html>
"""
    full_text = "\n\n".join(page_texts)
    stub_path.write_text(html, encoding="utf-8")
    print(f"  indexed {label} ({len(page_texts)} pages, {len(full_text)} chars) -> {path.name}")
    return True


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/process_batch.py <directory-with-pdfs>")
        return 1

    directory = sys.argv[1]
    lookup = load_manifest()
    unmatched = json.loads(UNMATCHED_LOG.read_text()) if UNMATCHED_LOG.exists() else []

    pdfs = list(iter_pdfs(directory))
    print(f"Found {len(pdfs)} PDF file(s) in {directory}")

    ok_count = 0
    for p in pdfs:
        if process_pdf(p, lookup, unmatched):
            ok_count += 1

    UNMATCHED_LOG.write_text(json.dumps(unmatched, indent=2))
    print(f"\nDone. {ok_count}/{len(pdfs)} succeeded. "
          f"{len(unmatched)} total unmatched/problem entries logged in {UNMATCHED_LOG.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
