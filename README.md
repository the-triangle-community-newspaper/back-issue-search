# The Triangle — back issue search

A free, text-only full-text search over every back issue of [The Triangle
Community Newspaper](https://thetriangle.org.au/) (Feb 2007 – present),
hosted entirely on GitHub Pages.

**Live search page:** set after first deploy — see below.

## How it works

- The PDFs themselves stay on thetriangle.org.au — nothing is copied or
  re-hosted here.
- `scripts/fetch_new_issues.py` reads the public
  [Back Issues](https://thetriangle.org.au/back-issues/) listing page (just
  that HTML page, not any PDFs), refreshes `scripts/issues_manifest.json`
  with the current set of issues and their live URLs, and compares it
  against what's already indexed in `site/issues/`. For any issue that's
  new, it downloads only that PDF, extracts its full text, writes a small
  stub HTML page, and immediately discards the PDF — nothing is ever stored
  in this repo except the extracted text. Already-indexed issues are never
  re-downloaded.
- A GitHub Actions workflow (`.github/workflows/build-and-deploy.yml`) runs
  this automatically at 20:00 UTC on the 1st of every month except January
  (≈6-7am on the 2nd in Sydney, year-round), commits any newly indexed
  issue, then rebuilds the Pagefind search index and redeploys the Pages
  site. It can also be triggered manually any time from the Actions tab.
- [Pagefind](https://pagefind.app/) indexes those stub pages into a compact,
  low-bandwidth search index (`site/pagefind/`) that runs entirely in the
  visitor's browser — no server, no hosting cost beyond GitHub Pages.
- `site/index.html` is the search page itself: a single text box, no filters
  or advanced options. Pressing Enter searches, and results are shown newest
  issue first, each linking straight to the original PDF on
  thetriangle.org.au. Each result also shows the page number the match was
  found on (e.g. "December 2019, p3").
- For a multi-word search (e.g. a person's name), the page automatically
  tries an exact-phrase match first, falling back to a normal search
  (every word required, in any order) only if the exact phrase isn't found
  anywhere. Searching for `Cobargo Hotel` will therefore prioritise pages
  where those two words actually appear together over pages that merely
  mention both words separately. Typing your own quotes (`"Cobargo
  Hotel"`) works the same way and is never double-wrapped.

## One-time setup after this repo is created

1. In the repo's **Settings → Pages**, set the source to **GitHub Actions**.
2. Run the **Build and deploy Triangle search index** workflow once manually
   (Actions tab → select the workflow → "Run workflow"), or just push a
   change to `site/`.
3. Once it finishes, the search page is live at the Pages URL shown in the
   workflow's deployment step (typically
   `https://<github-username>.github.io/<repo-name>/`).

## Adding a new issue

Normally nothing needs to be done — the monthly scheduled workflow picks up
any newly published issue automatically a day after it goes up.

If you ever want to index an issue immediately rather than waiting for the
schedule, either:

- Run the **Build and deploy Triangle search index** workflow manually from
  the Actions tab (it checks the back-issues page and indexes anything new
  it finds), or
- Process a local PDF directly:
  ```bash
  pip install -r scripts/requirements.txt
  python scripts/process_batch.py /path/to/folder-with-the-pdf
  ```
  then commit and push the resulting files in `site/issues/`.

## Embedding on the WordPress site

WordPress often strips inline `<script>` tags, so the simplest way to put
this on thetriangle.org.au is an iframe inside a **Custom HTML** block:

```html
<iframe
  src="https://<github-username>.github.io/<repo-name>/"
  title="Search The Triangle back issues"
  style="width:100%; min-height:640px; border:0;">
</iframe>
```

If the WordPress theme allows a raw HTML/Custom HTML block on a page, this
works without needing any plugin. If it doesn't, the GitHub Pages URL can
simply be linked to directly from the site instead.

## Rebuilding the search index locally

```bash
npx pagefind --site site --output-path site/pagefind
```

Then open `site/index.html` via a local static server (Pagefind's JS module
import needs http:// not file://), e.g. `python -m http.server --directory site`.
