# Your article site

Write articles in Markdown, run one command, get a fast static website with equations, figures, footnote references, code highlighting, topics, an RSS feed and dark mode.

## 1. Set up once

You need Python 3.9 or newer.

```bash
cd article-site
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Then open `config.yaml` and set your title, tagline, description and footer links. Edit `content/pages/about.md`.

## 2. Write and preview

```bash
python build.py serve
```

Open http://localhost:8000. The site rebuilds whenever you save a file; refresh the browser to see changes. The preview also shows drafts.

New article: add a file to `content/articles/`, e.g. `2026-12-01-my-title.md`:

```markdown
---
title: "My title"
date: 2026-12-01
summary: "One or two sentences for the home page."
tags: [EEG, Exploration]
draft: true
---

Your text here. Inline math \(V(s)\), display math \[ \delta = r - V(s) \]
```

`WRITING-GUIDE.md` shows every formatting feature: equations, figures with captions, references, code, tables.

## 3. Publish free on GitHub Pages

1. Create a new repository on GitHub. Name it `your-username.github.io` for the address `https://your-username.github.io`, or any name for `https://your-username.github.io/name`.
2. Push this folder to it:
   ```bash
   git init && git add . && git commit -m "First version"
   git branch -M main
   git remote add origin https://github.com/your-username/REPO.git
   git push -u origin main
   ```
3. On GitHub, open **Settings → Pages** and set **Source** to **GitHub Actions**.

Every push to `main` now rebuilds and publishes the site in about a minute (progress is under the **Actions** tab). Links adjust automatically to whichever address you chose.

To use your own domain, add it under Settings → Pages → Custom domain and follow GitHub's DNS instructions.

## Folder map

| Path | What it is |
|---|---|
| `content/articles/` | Your articles (one `.md` file each) |
| `content/pages/` | Standalone pages such as About; each gets a link in the top menu |
| `static/images/` | Figures and images, referenced as `images/name.png` |
| `static/style.css` | All styling: colours and fonts are at the top |
| `templates/` | Page layouts (HTML) |
| `config.yaml` | Site title, description, links |
| `build.py` | The generator; you shouldn't need to touch it |
| `_site/` | The built website (generated, don't edit) |

## Front matter options

| Key | Required | Meaning |
|---|---|---|
| `title` | yes | Article title |
| `date` | yes | Publication date, `YYYY-MM-DD` |
| `summary` | | Shown on the home page, in link previews and search results |
| `tags` | | List of topics, e.g. `[EEG, BCI]` |
| `draft` | | `true` keeps it out of the published site |
| `toc` | | `true` adds a contents list from the headings |
| `updated` | | Date of a later revision |
| `slug` | | Custom web address, instead of the file name |

## Hosting elsewhere

`python build.py` writes plain HTML to `_site/`. Upload that folder to any static host (Netlify, Cloudflare Pages, a university web space). If the site lives in a subfolder, build with `python build.py --base-path /subfolder`.
