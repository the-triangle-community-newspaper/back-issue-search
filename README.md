# The Triangle — back issue search

A free, text-only full-text search over every back issue of [The Triangle
Community Newspaper](https://thetriangle.org.au/) (Feb 2007 – present),
hosted entirely on GitHub Pages.

**Live search page:** set after first deploy — see below.

## How it works

- The PDFs themselves stay on thetriangle.org.au — nothing is copied or
  re-hosted here, and nothing is ever downloaded from the live site by this
  project.
- When a new issue is published, the publisher uploads the PDF here (see
  "Adding a new issue" below). `scripts/process_batch.py` extracts its full
  text and writes a small stub HTML page per issue into `site/issues/`,
  linking it to its live URL on thetriangle.org.au (looked up from
  `scripts/issues_manifest.json`). The PDF itself is never committed to the
  repo — only the extracted text stub.
- [Pagefind](https://pagefind.app/) indexes those stub pages into a compact,
  low-bandwidth search index (`site/pagefind/`) that runs entirely in the
  visitor's browser — no server, no hosting cost beyond GitHub Pages.
- `site/index.html` is the search page itself: a single text box, no filters
  or advanced options. Pressing Enter searches, and results are shown newest
  issue first, each linking straight to the original PDF on
  thetriangle.org.au.
- A GitHub Actions workflow (`.github/workflows/build-and-deploy.yml`)
  rebuilds the Pagefind index and redeploys the Pages site automatically on
  every push to `site/`. It does not fetch anything from thetriangle.org.au —
  it only rebuilds the search index from whatever stub pages are already
  committed.

## One-time setup after this repo is created

1. In the repo's **Settings → Pages**, set the source to **GitHub Actions**.
2. Run the **Build and deploy Triangle search index** workflow once manually
   (Actions tab → select the workflow → "Run workflow"), or just push a
   change to `site/`.
3. Once it finishes, the search page is live at the Pages URL shown in the
   workflow's deployment step (typically
   `https://<github-username>.github.io/<repo-name>/`).

## Adding a new issue

Each month (except January), once a new issue is published on
thetriangle.org.au:

1. Confirm the new issue's URL is listed on the
   [Back Issues](https://thetriangle.org.au/back-issues/) page, and add an
   entry for it to `scripts/issues_manifest.json` (year, month, url) if it
   isn't already there.
2. Put the issue's PDF in a folder locally and run:
   ```bash
   pip install -r scripts/requirements.txt
   python scripts/process_batch.py /path/to/folder-with-the-pdf
   ```
   This extracts the text and writes `site/issues/YYYY-MM.html` — it never
   uploads or transmits the PDF anywhere.
3. Commit and push the new/updated files in `site/issues/` and
   `scripts/issues_manifest.json`. The GitHub Actions workflow rebuilds the
   search index and redeploys automatically.

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
