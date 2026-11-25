#!/usr/bin/env python3
"""
Build the site: turns Markdown files in content/ into a static website in _site/.

Usage:
    python build.py              build the site into _site/
    python build.py serve        build, then preview at http://localhost:8000
                                 (rebuilds automatically when you save a file)
    python build.py --drafts     also include articles marked `draft: true`

Options used by the GitHub Pages workflow (you normally don't need them):
    --base-path /repo-name       prefix for every link, if the site lives in a subfolder
    --base-url https://...       full site address, used in the RSS feed and sitemap
"""

import argparse
import datetime as dt
import html
import math
import random
import re
import shutil
import sys
import time
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
OUT = ROOT / "_site"


# ---------------------------------------------------------------- helpers

def read_config():
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def parse_markdown_file(path):
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    if not m:
        raise SystemExit(f"\n✗ {path.relative_to(ROOT)} has no front matter "
                         f"(the block between --- lines at the top).\n")
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, m.group(2)


def make_md():
    return markdown.Markdown(
        extensions=[
            "extra",            # tables, footnotes, attr_list, fenced code, md_in_html
            "toc",
            "smarty",
            "codehilite",
            "pymdownx.arithmatex",
            "pymdownx.tilde",
            "pymdownx.mark",
        ],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "highlight"},
            "pymdownx.arithmatex": {"generic": True},
            "footnotes": {"BACKLINK_TEXT": "↩"},
            "toc": {"permalink": False},
        },
        output_format="html5",
    )


# An image alone in a paragraph becomes a figure; its title becomes the caption:
#   ![Alt text](images/plot.svg "Caption shown under the figure")
FIGURE = re.compile(r'<p>\s*(<img [^>]*?alt="([^"]*)"[^>]*?>)\s*</p>')


def figures(body):
    def repl(m):
        img = m.group(1)
        t = re.search(r'title="([^"]*)"', img)
        cap = t.group(1) if t else ""
        img = re.sub(r'\s*title="[^"]*"', "", img)
        img = img.replace("<img ", '<img loading="lazy" ', 1)
        figcap = f"<figcaption>{cap}</figcaption>" if cap else ""
        return f"<figure>{img}{figcap}</figure>"
    return FIGURE.sub(repl, body)


def fix_relative_images(body, base):
    # Let authors write  images/foo.png  and have it work on every page.
    return re.sub(r'(<img [^>]*?src=")(?!https?://|/|data:)(?:\.\./)*(?:static/)?',
                  lambda m: m.group(1) + base + "/", body)


def slug_from(path):
    name = path.stem
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def to_date(value, path):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except Exception:
        raise SystemExit(f"\n✗ {path.relative_to(ROOT)}: date should look like 2026-11-25\n")


def tag_slug(tag):
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


# ------------------------------------------------- the signature waveform
# Every article gets its own trace, generated from its slug: a few rhythms
# with 1/f amplitudes plus one evoked response, like a single EEG epoch.

def waveform(seed, width=640, height=48, points=320):
    rng = random.Random(seed)
    comps = []
    for _ in range(9):
        freq = rng.uniform(1.2, 26.0)
        comps.append((freq, 1.0 / math.sqrt(freq), rng.uniform(0, 2 * math.pi)))
    event_at = rng.uniform(0.35, 0.75)
    event_amp = rng.choice([-1, 1]) * rng.uniform(1.4, 2.1)
    ys = []
    for i in range(points):
        x = i / (points - 1)
        y = sum(a * math.sin(2 * math.pi * f * x * 2 + p) for f, a, p in comps)
        y += rng.gauss(0, 0.08)
        y += event_amp * math.exp(-((x - event_at) ** 2) / (2 * 0.012 ** 2))
        y -= 0.6 * event_amp * math.exp(-((x - event_at - 0.05) ** 2) / (2 * 0.02 ** 2))
        ys.append(y)
    lo, hi = min(ys), max(ys)
    pad = 3
    coords = []
    for i, y in enumerate(ys):
        px = width * i / (points - 1)
        py = pad + (height - 2 * pad) * (1 - (y - lo) / (hi - lo))
        coords.append(f"{px:.1f},{py:.1f}")
    return {"d": "M" + " L".join(coords), "w": width, "h": height}


# ------------------------------------------------------------ the build

def load_articles(include_drafts, base):
    articles = []
    for path in sorted((CONTENT / "articles").glob("*.md")):
        meta, text = parse_markdown_file(path)
        if meta.get("draft") and not include_drafts:
            continue
        if "title" not in meta or "date" not in meta:
            raise SystemExit(f"\n✗ {path.relative_to(ROOT)} needs at least a "
                             f"`title:` and a `date:` in its front matter.\n")
        md = make_md()
        body = md.convert(text)
        body = fix_relative_images(figures(body), base)
        words = len(re.sub(r"<[^>]+>", " ", body).split())
        slug = meta.get("slug") or slug_from(path)
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        articles.append({
            "title": meta["title"],
            "date": to_date(meta["date"], path),
            "updated": to_date(meta["updated"], path) if meta.get("updated") else None,
            "summary": meta.get("summary", ""),
            "tags": [{"name": t, "slug": tag_slug(t)} for t in tags],
            "draft": bool(meta.get("draft")),
            "slug": slug,
            "url": f"{base}/articles/{slug}/",
            "body": body,
            "toc": md.toc if meta.get("toc") else "",
            "math": "arithmatex" in body,
            "minutes": max(1, round(words / 220)),
            "wave": waveform(slug),
            "source": path,
        })
    articles.sort(key=lambda a: a["date"], reverse=True)
    for i, a in enumerate(articles):
        a["newer"] = articles[i - 1] if i > 0 else None
        a["older"] = articles[i + 1] if i + 1 < len(articles) else None
    return articles


def load_pages(base):
    pages = []
    for path in sorted((CONTENT / "pages").glob("*.md")):
        meta, text = parse_markdown_file(path)
        body = fix_relative_images(figures(make_md().convert(text)), base)
        slug = meta.get("slug") or slug_from(path)
        pages.append({
            "title": meta.get("title", slug.title()),
            "subtitle": meta.get("subtitle", ""),
            "photo": f"{base}/{str(meta['photo']).lstrip('/').removeprefix('static/')}" if meta.get("photo") else "",
            "slug": slug,
            "url": f"{base}/{slug}/",
            "nav": meta.get("nav", True),
            "order": meta.get("order", 50),
            "body": body,
            "math": "arithmatex" in body,
        })
    pages.sort(key=lambda p: p["order"])
    return pages


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def pygments_css():
    light = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    dark = HtmlFormatter(style="github-dark").get_style_defs(".highlight")
    strip_bg = lambda css: re.sub(r"\.highlight\s*\{[^}]*\}", "", css)
    dark_scoped = "\n".join("  " + line for line in strip_bg(dark).splitlines())
    return (
        "/* generated by build.py, do not edit */\n"
        + strip_bg(light)
        + "\n@media (prefers-color-scheme: dark) {\n" + dark_scoped + "\n}\n"
    )


def build(args):
    t0 = time.time()
    config = read_config()
    base = (args.base_path if args.base_path is not None else config.get("base_path", "")).rstrip("/")
    site_url = (args.base_url or config.get("url", "")).rstrip("/")

    articles = load_articles(args.drafts, base)
    pages = load_pages(base)

    tags = {}
    for a in articles:
        for t in a["tags"]:
            tags.setdefault(t["slug"], {"name": t["name"], "slug": t["slug"], "articles": []})
            tags[t["slug"]]["articles"].append(a)
    tag_list = sorted(tags.values(), key=lambda t: (-len(t["articles"]), t["name"].lower()))

    by_year = []
    for a in articles:
        if not by_year or by_year[-1]["year"] != a["date"].year:
            by_year.append({"year": a["date"].year, "articles": []})
        by_year[-1]["articles"].append(a)

    env = Environment(loader=FileSystemLoader(TEMPLATES),
                      autoescape=select_autoescape(["html", "xml"]))
    env.filters["longdate"] = lambda d: f"{d.day} {d.strftime('%B %Y')}"
    env.filters["shortdate"] = lambda d: f"{d.day} {d.strftime('%b')}"
    env.filters["rfc822"] = lambda d: dt.datetime(d.year, d.month, d.day, 9, 0,
                                                 tzinfo=dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    common = {
        "site": config, "base": base, "site_url": site_url,
        "nav_pages": [p for p in pages if p["nav"]],
        "site_wave": waveform(config.get("title", "site"), width=900, height=64, points=420),
        "year": dt.date.today().year,
        "has_tags": bool(tag_list),
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    if STATIC.exists():
        shutil.copytree(STATIC, OUT, dirs_exist_ok=True)
    write(OUT / "highlight.css", pygments_css())

    render = lambda tpl, **kw: env.get_template(tpl).render(**common, **kw)

    write(OUT / "index.html", render("index.html", years=by_year, articles=articles, tags=tag_list))
    for a in articles:
        write(OUT / "articles" / a["slug"] / "index.html", render("article.html", article=a))
    for p in pages:
        write(OUT / p["slug"] / "index.html", render("page.html", page=p))
    write(OUT / "tags" / "index.html", render("tags.html", tags=tag_list))
    for t in tag_list:
        write(OUT / "tags" / t["slug"] / "index.html", render("tag.html", tag=t))
    write(OUT / "404.html", render("404.html"))
    write(OUT / "feed.xml", render("feed.xml", articles=articles[:20]))
    write(OUT / "sitemap.xml", render("sitemap.xml", articles=articles, pages=pages, tags=tag_list))
    write(OUT / ".nojekyll", "")

    drafts = sum(a["draft"] for a in articles)
    print(f"✓ Built {len(articles)} article{'s' * (len(articles) != 1)}"
          f"{f' ({drafts} draft)' if drafts else ''}, {len(pages)} page(s), "
          f"{len(tag_list)} tag(s) into _site/ in {time.time() - t0:.2f}s")


def snapshot():
    files = [p for d in (CONTENT, TEMPLATES, STATIC) for p in d.rglob("*") if p.is_file()]
    files.append(ROOT / "config.yaml")
    return {p: p.stat().st_mtime for p in files}


def serve(args):
    import functools
    import http.server
    import threading

    build(args)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))

    class Quiet(handler.func):
        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port),
                                            functools.partial(Quiet, directory=str(OUT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"→ Preview at http://localhost:{args.port}  (Ctrl+C to stop; saving a file rebuilds)")
    seen = snapshot()
    try:
        while True:
            time.sleep(0.7)
            now = snapshot()
            if now != seen:
                seen = now
                try:
                    build(args)
                except SystemExit as e:
                    print(e)
                except Exception as e:
                    print(f"✗ Build failed: {e}")
    except KeyboardInterrupt:
        server.shutdown()


def main():
    p = argparse.ArgumentParser(description="Build the article site.")
    p.add_argument("command", nargs="?", default="build", choices=["build", "serve"])
    p.add_argument("--drafts", action="store_true", help="include draft articles")
    p.add_argument("--base-path", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    if args.command == "serve":
        args.drafts = True   # the local preview always shows drafts
        serve(args)
    else:
        build(args)


if __name__ == "__main__":
    main()
