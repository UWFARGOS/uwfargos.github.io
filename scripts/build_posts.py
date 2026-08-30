"""
build_posts.py — turn markdown files in content/ into published pages.

    python scripts/build_posts.py

You never have to run this yourself. The GitHub Action runs it on every push,
which means the real workflow is: create a .md file in content/ using GitHub's
web editor, commit, done. No terminal, no local setup.

Front matter goes at the top of each file between --- lines:

    ---
    title: Why finance recruits 18 months early
    date: 2026-09-03
    summary: One paragraph shown on the index page.
    tags: recruiting, timeline
    ---

    Your post in ordinary markdown.
"""

import html
import json
import pathlib
import re
from datetime import date

import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "site" / "posts"

MD = markdown.Markdown(extensions=["extra", "sane_lists", "smarty", "toc"])


def parse(path):
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw

    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        body = m.group(2)

    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    MD.reset()
    return {
        "slug": slug,
        "title": meta.get("title") or path.stem.replace("-", " ").title(),
        "date": meta.get("date", date.today().isoformat()),
        "summary": meta.get("summary", ""),
        "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
        "html": MD.convert(body),
        "words": len(body.split()),
    }


PAGE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Argo Internship Board</title>
<meta name="description" content="{summary}">
<link rel="stylesheet" href="../post.css">
</head><body>
<header class="bar"><div class="wrap">
  <a class="home" href="../index.html">← Argo Internship Board</a>
  <a class="alt" href="../learn.html">All guides</a>
</div></header>
<article class="wrap post">
  <p class="kicker">{date} · {mins} min read</p>
  <h1>{title}</h1>
  {tags}
  {body}
  <hr>
  <p class="cta">Screened internship and entry-level postings, updated daily —
     <a href="../index.html">see the board</a>.</p>
</article>
</body></html>
"""


def main():
    CONTENT.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    files = sorted(f for f in CONTENT.glob("*.md") if "draft" not in f.stem.lower())
    posts = []

    for f in files:
        p = parse(f)
        tags = ("<p class='tags'>" +
                "".join(f"<span>{html.escape(t)}</span>" for t in p["tags"]) +
                "</p>") if p["tags"] else ""
        (OUT / f"{p['slug']}.html").write_text(PAGE.format(
            title=html.escape(p["title"]),
            summary=html.escape(p["summary"]),
            date=p["date"], mins=max(1, round(p["words"] / 220)),
            tags=tags, body=p["html"]), encoding="utf-8")
        posts.append({k: p[k] for k in ("slug", "title", "date", "summary", "tags")}
                     | {"mins": max(1, round(p["words"] / 220))})

    posts.sort(key=lambda p: p["date"], reverse=True)
    (ROOT / "site" / "posts.json").write_text(json.dumps(
        {"count": len(posts), "posts": posts}, indent=1))

    for p in posts:
        print(f"  {p['date']}  {p['title']}")
    print(f"{len(posts)} post(s) built")


if __name__ == "__main__":
    main()
