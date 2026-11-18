#!/usr/bin/env python3
"""Convert Obsidian notes into Zola posts.

    tools/obsidian_to_zola.py NOTE.md              # one note (always converted)
    tools/obsidian_to_zola.py ~/Vault/Blog         # a folder: converts notes with `publish: true`
    tools/obsidian_to_zola.py ~/Vault/Blog --all   # a folder: converts every note
    tools/obsidian_to_zola.py NOTE.md --dry-run    # show what would happen, write nothing

What it does (see README.md, "Writing posts in Obsidian"):
  * YAML properties -> TOML front matter (title, date, description, draft, series, tags)
  * [[wikilinks]] -> Zola internal links (@/posts/...), or plain text when the target isn't a post
  * ![[image.png]] and local image links -> copied to static/images/<slug>/ and re-linked
  * > [!note] callouts -> bold-labelled blockquotes, ==highlights== -> <mark>, %%comments%% removed
  * `{{`, `{%` and `{#` are escaped, because Zola runs post content through its template engine

Standard library only. Re-running overwrites the generated post, so edit the note, not the output.
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
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}
SKIP_DIRS = {".obsidian", ".trash", ".git"}
TERA_OPEN = re.compile(r"(\{\{|\{%|\{#)")


# ---------------------------------------------------------------- front matter

def split_frontmatter(text):
    """Return (properties dict, body) for a note with optional YAML properties."""
    text = text.lstrip("﻿")
    m = re.match(r"---[ \t]*\r?\n(.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|$)", text, re.S)
    if not m:
        return {}, text
    return parse_yaml(m.group(1)), text[m.end():]


def scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    low = value.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    return value


def parse_yaml(block):
    """Tiny YAML subset: `key: value`, `key: [a, b]`, and `- item` lists (what Obsidian writes)."""
    props, key = {}, None
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = re.match(r"\s+-\s+(.*)|-\s+(.*)", raw)
        if item and key is not None:
            if not isinstance(props.get(key), list):
                props[key] = []
            props[key].append(scalar(item.group(1) or item.group(2)))
            continue
        m = re.match(r"([A-Za-z0-9_\-]+)\s*:\s*(.*)$", raw)
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            props[key] = [scalar(v) for v in value[1:-1].split(",") if v.strip()]
        elif value == "":
            props[key] = []
        else:
            props[key] = scalar(value)
    return props


def as_list(value):
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        return [str(v).strip().lstrip("#") for v in value if str(v).strip()]
    return [v.strip().lstrip("#") for v in str(value).split(",") if v.strip()]


def toml_str(value):
    return json.dumps(str(value), ensure_ascii=False)


def toml_list(values):
    return "[" + ", ".join(toml_str(v) for v in values) + "]"


def pick_date(props, note_path):
    for key in ("date", "created", "published"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2})(?::(\d{2}))?)?", str(props.get(key, "")))
        if m:
            day, hm, sec = m.groups()
            return f"{day}T{hm}:{sec or '00'}" if hm else day
    return dt.date.fromtimestamp(note_path.stat().st_mtime).isoformat()


# ---------------------------------------------------------------------- helpers

def slugify(text):
    text = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", text).strip("-") or "post"


def heading_anchor(heading):
    """Approximates the id Zola gives a heading."""
    return slugify(heading)


def find_vault(start):
    for parent in [start, *start.parents]:
        if (parent / ".obsidian").is_dir():
            return parent
    return start


class Vault:
    """Finds attachments by file name anywhere in the vault, like Obsidian does."""

    def __init__(self, root):
        self.root = root
        self._index = None

    def find(self, name):
        if self._index is None:
            self._index = {}
            for p in self.root.rglob("*"):
                if p.is_file() and not (SKIP_DIRS & set(p.relative_to(self.root).parts)):
                    self._index.setdefault(p.name.lower(), p)
        return self._index.get(Path(name).name.lower())


def existing_posts(posts_dir):
    """Map lowercase note titles / file stems -> output file name for posts already in the site."""
    found = {}
    for p in posts_dir.glob("*.md"):
        if p.name == "_index.md":
            continue
        text = p.read_text(encoding="utf-8")
        if re.search(r"^draft\s*=\s*true", text, re.M):
            continue
        found.setdefault(p.stem.lower(), p.name)
        m = re.search(r'^title\s*=\s*"((?:[^"\\]|\\.)*)"', text, re.M)
        if m:
            found.setdefault(json.loads(f'"{m.group(1)}"').lower(), p.name)
    return found


# ------------------------------------------------------------------ body rewrite

def split_code(text):
    """Split into (is_code, chunk) so rewrites never touch fenced or inline code."""
    parts, pos = [], 0
    for m in re.finditer(r"(^|\n)(```|~~~)[^\n]*\n.*?(?:\n\2[^\n]*(?=\n|$)|\Z)", text, re.S):
        start = m.start() + len(m.group(1))
        parts.append((False, text[pos:start]))
        parts.append((True, text[start:m.end()]))
        pos = m.end()
    parts.append((False, text[pos:]))
    out = []
    for is_code, chunk in parts:
        if is_code:
            out.append((True, chunk))
            continue
        last = 0
        for m in re.finditer(r"(`+)(?:(?!\1).)+?\1", chunk, re.S):
            out.append((False, chunk[last:m.start()]))
            out.append((True, m.group(0)))
            last = m.end()
        out.append((False, chunk[last:]))
    return out


CALLOUT = re.compile(r"^(>[ \t]*)\[!([A-Za-z-]+)\][+-]?[ \t]*(.*)$", re.M)


class Converter:
    def __init__(self, slug, note_path, vault, post_map, drafts, images_dir, dry_run, warn):
        self.slug, self.note_path, self.vault = slug, note_path, vault
        self.drafts = drafts
        self.post_map, self.images_dir = post_map, images_dir
        self.dry_run, self.warn = dry_run, warn
        self.copied = []

    # attachments ---------------------------------------------------------------
    def attach(self, name):
        name = unquote(name)
        src = self.vault.find(name)
        if src is None:
            local = (self.note_path.parent / name)
            src = local if local.is_file() else None
        if src is None:
            self.warn(f"attachment not found: {name}")
            return None
        dest = self.images_dir / self.slug / src.name
        self.copied.append((src, dest))
        return f"/images/{self.slug}/{quote(src.name)}"

    # inline pieces -------------------------------------------------------------
    def wikilink_target(self, target, heading):
        key = target.strip().lower()
        fname = self.post_map.get(key)
        anchor = f"#{heading_anchor(heading)}" if heading else ""
        if fname:
            return f"@/posts/{quote(fname)}{anchor}"
        return None

    def embed(self, m):
        target, size = m.group(1).strip(), (m.group(3) or "").strip()
        ext = Path(target).suffix.lower()
        if ext in IMAGE_EXTS:
            url = self.attach(target)
            if url is None:
                return m.group(0)
            if re.fullmatch(r"\d+(x\d+)?", size):
                width = size.split("x")[0]
                return f'<img src="{url}" alt="{Path(target).stem}" width="{width}">'
            return f"![{size or Path(target).stem}]({url})"
        if ext:  # pdf, audio, video...
            url = self.attach(target)
            return f"[{Path(target).name}]({url})" if url else m.group(0)
        self.warn(f"note embeds (![[{target}]]) aren't supported; left as a link")
        link = self.wikilink_target(target, m.group(2))
        return f"[{target}]({link})" if link else target

    def wikilink(self, m):
        target, heading, alias = m.group(1).strip(), m.group(2), (m.group(3) or "").strip()
        if not target:  # [[#Heading]] links within the same note
            return f"[{alias or heading}](#{heading_anchor(heading)})"
        text = alias or (f"{target} > {heading}" if heading else target)
        link = self.wikilink_target(target, heading)
        if link:
            return f"[{text}]({link})"
        if target.strip().lower() in self.drafts:
            self.warn(f"[[{target}]] is a draft, so it can't be linked yet; kept as plain text")
        else:
            self.warn(f"[[{target}]] isn't a post on the site; kept as plain text")
        return text

    def local_image(self, m):
        alt, url = m.group(1), m.group(2).strip()
        if re.match(r"[a-z][a-z0-9+.-]*:|/|#", url, re.I) or Path(unquote(url)).suffix.lower() not in IMAGE_EXTS:
            return m.group(0)
        new = self.attach(url)
        return f"![{alt}]({new})" if new else m.group(0)

    # whole body ----------------------------------------------------------------
    def text_chunk(self, s):
        s = re.sub(r"%%.*?%%", "", s, flags=re.S)
        s = re.sub(r"!\[\[([^\]|#]+)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]", self.embed, s)
        s = re.sub(r"\[\[([^\]|#]*)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]", self.wikilink, s)
        s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", self.local_image, s)
        s = re.sub(r"==(?=\S)(.+?)(?<=\S)==", r"<mark>\1</mark>", s)
        s = re.sub(r"[ \t]+\^[A-Za-z0-9-]+$", "", s, flags=re.M)  # block ids
        s = CALLOUT.sub(lambda m: f"{m.group(1)}**{m.group(3).strip() or m.group(2).capitalize()}**\n{m.group(1).rstrip()}", s)
        return s

    def convert(self, body):
        body = "".join(c if is_code else self.text_chunk(c) for is_code, c in split_code(body))
        return TERA_OPEN.sub(r"{% raw %}\1{% endraw %}", body)


# ------------------------------------------------------------------------- main

def build_post(note, args, vault, post_map, drafts, warn_to):
    props, body = split_frontmatter(note.read_text(encoding="utf-8"))
    body = body.replace("\r\n", "\n").lstrip("\n")

    title = str(props.get("title") or "").strip()
    h1 = re.match(r"#[ \t]+(.+?)[ \t]*\n", body)
    if not title:
        title = h1.group(1).strip() if h1 else note.stem
    if h1 and h1.group(1).strip() == title:
        body = body[h1.end():].lstrip("\n")  # the post template already renders the title

    slug = str(props.get("slug") or slugify(title))
    conv = Converter(slug, note, vault, post_map, drafts, REPO / "static" / "images", args.dry_run,
                     lambda msg: warn_to.append(f"{note.name}: {msg}"))
    body = conv.convert(body)

    series, tags = as_list(props.get("series")), as_list(props.get("tags"))
    lines = ["+++", f"title = {toml_str(title)}", f"date = {pick_date(props, note)}"]
    if props.get("description"):
        lines.append(f"description = {toml_str(props['description'])}")
    if props.get("draft") is True or args.draft:
        lines.append("draft = true")
    if series:
        lines += ["", "[taxonomies]", f"series = {toml_list(series[:1])}"]
    if tags:
        lines += ["", "[extra]", f"tags = {toml_list(tags)}"]
    lines += ["+++", "", body.rstrip() + "\n"]
    return slug, "\n".join(lines), conv.copied


def collect(paths, convert_all):
    notes, skipped = [], 0
    for p in paths:
        if p.is_file():
            notes.append(p)
            continue
        for f in sorted(p.rglob("*.md")):
            if SKIP_DIRS & set(f.relative_to(p).parts):
                continue
            props, _ = split_frontmatter(f.read_text(encoding="utf-8"))
            if convert_all or props.get("publish") is True:
                notes.append(f)
            else:
                skipped += 1
    return notes, skipped


def main():
    ap = argparse.ArgumentParser(description="Convert Obsidian notes into Zola posts.")
    ap.add_argument("paths", nargs="+", type=Path, help="note files and/or folders")
    ap.add_argument("--all", action="store_true", help="in folders, convert notes even without `publish: true`")
    ap.add_argument("--draft", action="store_true", help="mark every converted post as a draft")
    ap.add_argument("--vault", type=Path, help="vault root for finding attachments (default: auto-detect)")
    ap.add_argument("--out", type=Path, default=REPO / "content" / "posts", help="output folder (default: content/posts)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be written, change nothing")
    args = ap.parse_args()

    paths = [p.expanduser().resolve() for p in args.paths]
    missing = [p for p in paths if not p.exists()]
    if missing:
        sys.exit(f"not found: {', '.join(map(str, missing))}")
    notes, skipped = collect(paths, args.all)
    if not notes:
        sys.exit("no notes to convert (notes in folders need `publish: true`, or pass --all)")

    vault = Vault((args.vault.expanduser().resolve() if args.vault else find_vault(paths[0] if paths[0].is_dir() else paths[0].parent)))
    post_map = existing_posts(args.out)
    # let notes in this batch link to each other by title or file name (drafts aren't linkable)
    drafts = set()
    for n in notes:
        props, body = split_frontmatter(n.read_text(encoding="utf-8"))
        h1 = re.match(r"\s*#[ \t]+(.+?)[ \t]*\n", body)
        title = str(props.get("title") or (h1.group(1).strip() if h1 else n.stem))
        names = {n.stem.lower(), title.lower()}
        if props.get("draft") is True or args.draft:
            drafts |= names
            for k in names:
                post_map.pop(k, None)
        else:
            out_name = f"{props.get('slug') or slugify(title)}.md"
            for k in names:
                post_map[k] = out_name

    warnings, images = [], 0
    for note in notes:
        slug, text, copied = build_post(note, args, vault, post_map, drafts, warnings)
        dest = args.out / f"{slug}.md"
        verb = "would write" if args.dry_run else ("overwrite" if dest.exists() else "write")
        print(f"{verb}: {dest.relative_to(REPO) if dest.is_relative_to(REPO) else dest}  <-  {note.name}")
        if not args.dry_run:
            args.out.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            for src, img_dest in copied:
                img_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, img_dest)
        images += len(copied)

    print(f"\n{len(notes)} post(s), {images} image(s)" + (f", {skipped} note(s) skipped (no `publish: true`)" if skipped else ""))
    for w in warnings:
        print(f"warning: {w}")


if __name__ == "__main__":
    main()
