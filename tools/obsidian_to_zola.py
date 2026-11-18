#!/usr/bin/env python3
"""Convert one Obsidian note into a Zola post.

    python3 tools/obsidian_to_zola.py "My Note.md"
    python3 tools/obsidian_to_zola.py "My Note.md" --dry-run    # print the result, write nothing

The post is written to content/posts/<slug>.md (overwritten on every run, so edit the note, not the
output). Images referenced by the note are looked up next to it (including subfolders) and copied to
static/images/<slug>/. See README.md, "Writing posts in Obsidian", for what gets converted.

Standard library only.
"""

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, unquote

REPO = Path(__file__).resolve().parent.parent
POSTS = REPO / "content" / "posts"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}
TERA_OPEN = re.compile(r"(\{\{|\{%|\{#)")  # Zola runs post content through Tera, so escape these


# ---------------------------------------------------------------- front matter

def scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return {"true": True, "yes": True, "false": False, "no": False}.get(value.lower(), value)


def parse_properties(text):
    """Return (properties, body). Understands `key: value`, `key: [a, b]` and `- item` lists."""
    text = text.lstrip("﻿")
    m = re.match(r"---[ \t]*\r?\n(.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|$)", text, re.S)
    if not m:
        return {}, text
    props, key = {}, None
    for raw in m.group(1).splitlines():
        item = re.match(r"\s*-\s+(.*)", raw)
        if item and key:
            if not isinstance(props.get(key), list):
                props[key] = []
            props[key].append(scalar(item.group(1)))
            continue
        kv = re.match(r"([A-Za-z0-9_\-]+)\s*:\s*(.*)$", raw)
        if not kv:
            continue
        key, value = kv.group(1).lower(), kv.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            props[key] = [scalar(v) for v in value[1:-1].split(",") if v.strip()]
        else:
            props[key] = scalar(value) if value else []
    return props, text[m.end():]


def as_list(value):
    items = value if isinstance(value, list) else str(value or "").split(",")
    return [str(v).strip().lstrip("#") for v in items if str(v).strip()]


def toml_str(value):
    return json.dumps(str(value), ensure_ascii=False)


def toml_list(values):
    return "[" + ", ".join(toml_str(v) for v in values) + "]"


def pick_date(props, note):
    for key in ("date", "created", "published"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2})(?::(\d{2}))?)?", str(props.get(key, "")))
        if m:
            day, hm, sec = m.groups()
            return f"{day}T{hm}:{sec or '00'}" if hm else day
    return dt.date.fromtimestamp(note.stat().st_mtime).isoformat()


def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", text).strip("-") or "post"


# ------------------------------------------------------------------ body rewrite

def existing_posts():
    """Lowercase title / file stem -> file name, for published posts already on the site."""
    found = {}
    for p in POSTS.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if p.name == "_index.md" or re.search(r"^draft\s*=\s*true", text, re.M):
            continue
        found.setdefault(p.stem.lower(), p.name)
        m = re.search(r'^title\s*=\s*"((?:[^"\\]|\\.)*)"', text, re.M)
        if m:
            found.setdefault(json.loads(f'"{m.group(1)}"').lower(), p.name)
    return found


def split_code(text):
    """Yield (is_code, chunk) so fenced and inline code is never rewritten."""
    parts, pos = [], 0
    for m in re.finditer(r"(^|\n)(```|~~~)[^\n]*\n.*?(?:\n\2[^\n]*(?=\n|$)|\Z)", text, re.S):
        start = m.start() + len(m.group(1))
        parts += [(False, text[pos:start]), (True, text[start:m.end()])]
        pos = m.end()
    parts.append((False, text[pos:]))
    for is_code, chunk in parts:
        if is_code:
            yield True, chunk
            continue
        last = 0
        for m in re.finditer(r"(`+)(?:(?!\1).)+?\1", chunk, re.S):
            yield False, chunk[last:m.start()]
            yield True, m.group(0)
            last = m.end()
        yield False, chunk[last:]


class Converter:
    def __init__(self, note, slug):
        self.note, self.slug = note, slug
        self.posts = existing_posts()
        self.images = []  # (source, destination)
        self.warnings = []

    def attach(self, name):
        name = unquote(name)
        direct = self.note.parent / name
        src = direct if direct.is_file() else next(self.note.parent.rglob(Path(name).name), None)
        if src is None or not src.is_file():
            self.warnings.append(f"image not found next to the note: {name}")
            return None
        self.images.append((src, REPO / "static" / "images" / self.slug / src.name))
        return f"/images/{self.slug}/{quote(src.name)}"

    def embed(self, m):
        target, size = m.group(1).strip(), (m.group(3) or "").strip()
        if Path(target).suffix.lower() not in IMAGE_EXTS:
            self.warnings.append(f"embed ![[{target}]] isn't supported; left as text")
            return target
        url = self.attach(target)
        if url is None:
            return m.group(0)
        if re.fullmatch(r"\d+(x\d+)?", size):
            return f'<img src="{url}" alt="{Path(target).stem}" width="{size.split("x")[0]}">'
        return f"![{size or Path(target).stem}]({url})"

    def wikilink(self, m):
        target, heading, alias = m.group(1).strip(), m.group(2), (m.group(3) or "").strip()
        anchor = f"#{slugify(heading)}" if heading else ""
        if not target:  # [[#Heading]]: a link within this note
            return f"[{alias or heading}]({anchor})"
        text = alias or (f"{target} > {heading}" if heading else target)
        fname = self.posts.get(target.lower())
        if fname:
            return f"[{text}](@/posts/{quote(fname)}{anchor})"
        self.warnings.append(f"[[{target}]] isn't a published post on the site; kept as plain text")
        return text

    def local_image(self, m):
        alt, url = m.group(1), m.group(2).strip()
        if re.match(r"[a-z][a-z0-9+.-]*:|/|#", url, re.I) or Path(unquote(url)).suffix.lower() not in IMAGE_EXTS:
            return m.group(0)
        new = self.attach(url)
        return f"![{alt}]({new})" if new else m.group(0)

    def text(self, s):
        s = re.sub(r"%%.*?%%", "", s, flags=re.S)  # comments
        s = re.sub(r"!\[\[([^\]|#]+)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]", self.embed, s)
        s = re.sub(r"\[\[([^\]|#]*)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]", self.wikilink, s)
        s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", self.local_image, s)
        s = re.sub(r"==(?=\S)(.+?)(?<=\S)==", r"<mark>\1</mark>", s)
        s = re.sub(r"[ \t]+\^[A-Za-z0-9-]+$", "", s, flags=re.M)  # block ids
        # callouts: "> [!tip] Title" -> a bold title line inside the blockquote
        s = re.sub(r"^(>[ \t]*)\[!([A-Za-z-]+)\][+-]?[ \t]*(.*)$",
                   lambda m: f"{m.group(1)}**{m.group(3).strip() or m.group(2).capitalize()}**\n{m.group(1).rstrip()}",
                   s, flags=re.M)
        return s

    def convert(self, body):
        body = "".join(c if code else self.text(c) for code, c in split_code(body))
        return TERA_OPEN.sub(r"{% raw %}\1{% endraw %}", body)


# ------------------------------------------------------------------------- main

def main():
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to a legacy code page
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Convert one Obsidian note into a Zola post.")
    ap.add_argument("note", type=Path, help="the Obsidian note (.md)")
    ap.add_argument("--dry-run", action="store_true", help="print the post instead of writing files")
    args = ap.parse_args()

    note = args.note.expanduser().resolve()
    if not note.is_file():
        sys.exit(f"not found: {note}")

    props, body = parse_properties(note.read_text(encoding="utf-8"))
    body = body.replace("\r\n", "\n").lstrip("\n")

    h1 = re.match(r"#[ \t]+(.+?)[ \t]*\n", body)
    title = str(props.get("title") or (h1.group(1).strip() if h1 else note.stem)).strip()
    if h1 and h1.group(1).strip() == title:
        body = body[h1.end():].lstrip("\n")  # the post template already renders the title
    slug = str(props.get("slug") or slugify(title))

    conv = Converter(note, slug)
    body = conv.convert(body)

    series, tags = as_list(props.get("series")), as_list(props.get("tags"))
    lines = ["+++", f"title = {toml_str(title)}", f"date = {pick_date(props, note)}"]
    if props.get("description"):
        lines.append(f"description = {toml_str(props['description'])}")
    if props.get("draft") is True:
        lines.append("draft = true")
    if series:
        lines += ["", "[taxonomies]", f"series = {toml_list(series[:1])}"]
    if tags:
        lines += ["", "[extra]", f"tags = {toml_list(tags)}"]
    post = "\n".join(lines + ["+++", "", body.rstrip() + "\n"])

    dest = POSTS / f"{slug}.md"
    if args.dry_run:
        print(f"# would write {dest.relative_to(REPO)} and copy {len(conv.images)} image(s)\n")
        print(post)
    else:
        existed = dest.exists()
        POSTS.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:  # LF endings, even on Windows
            f.write(post)
        for src, img_dest in conv.images:
            img_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, img_dest)
        print(f"{'overwrote' if existed else 'wrote'} {dest.relative_to(REPO)} ({len(conv.images)} image(s) copied)")
    for w in conv.warnings:
        print(f"warning: {w}")


if __name__ == "__main__":
    main()
