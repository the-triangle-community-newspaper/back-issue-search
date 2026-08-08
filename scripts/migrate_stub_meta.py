#!/usr/bin/env python3
"""One-off migration: rewrite existing site/issues/*.html stub pages from the
old (broken) single-attribute comma-joined data-pagefind-meta format to the
new per-element format, without altering the extracted PDF text.

Old format (buggy -- Pagefind only honors the LAST inline key:value in a
comma list, so pdf/date after title got silently discarded):
  <main data-pagefind-body
        data-pagefind-meta="title:LABEL, pdf:URL, date:DATE"
        data-pagefind-filter="year:YEAR">
  <h1>LABEL</h1>
  <span data-pagefind-sort="date" data-pagefind-ignore style="display:none">DATE</span>
  <pre>TEXT</pre>
  </main>

New format:
  <main data-pagefind-body
        data-pagefind-filter="year:YEAR">
  <h1 data-pagefind-meta="title">LABEL</h1>
  <a data-pagefind-meta="pdf[href]" href="URL" data-pagefind-ignore style="display:none">PDF</a>
  <span data-pagefind-meta="date" data-pagefind-sort="date" data-pagefind-ignore style="display:none">DATE</span>
  <pre>TEXT</pre>
  </main>
"""
import re
import sys
from pathlib import Path

ISSUES_DIR = Path(__file__).resolve().parent.parent / "site" / "issues"

OLD_MAIN_RE = re.compile(
    r'<main data-pagefind-body\s*\n\s*data-pagefind-meta="title:(?P<title>.*?), pdf:(?P<pdf>.*?), date:(?P<date>[\d-]+)"\s*\n\s*data-pagefind-filter="year:(?P<year>\d+)">\n'
    r'<h1>(?P<h1>.*?)</h1>\n'
    r'<span data-pagefind-sort="date" data-pagefind-ignore style="display:none">(?P<sortdate>[\d-]+)</span>\n',
    re.DOTALL,
)


def migrate_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    m = OLD_MAIN_RE.search(text)
    if not m:
        return False  # already migrated or unexpected format

    new_main = (
        '<main data-pagefind-body\n'
        f'      data-pagefind-filter="year:{m.group("year")}">\n'
        f'<h1 data-pagefind-meta="title">{m.group("h1")}</h1>\n'
        f'<a data-pagefind-meta="pdf[href]" href="{m.group("pdf")}" data-pagefind-ignore style="display:none">PDF</a>\n'
        f'<span data-pagefind-meta="date" data-pagefind-sort="date" data-pagefind-ignore style="display:none">{m.group("sortdate")}</span>\n'
    )
    new_text = text[: m.start()] + new_main + text[m.end():]
    path.write_text(new_text, encoding="utf-8")
    return True


def main():
    files = sorted(ISSUES_DIR.glob("*.html"))
    migrated = 0
    skipped = 0
    for f in files:
        if migrate_file(f):
            migrated += 1
        else:
            skipped += 1
            print(f"  SKIPPED (no match / already migrated): {f.name}")
    print(f"Migrated {migrated} file(s), skipped {skipped} of {len(files)} total.")
    return 0 if skipped == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
