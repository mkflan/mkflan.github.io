# my blog website


## Post series

To make a post part of a series, add a `[taxonomies]` table to its front matter:

```toml
+++
title = "Part 2: Decoding instructions"
date = 2026-11-09

[taxonomies]
series = ["Building a Tiny Emulator"]
+++
```

Posts with the same series name are grouped automatically and ordered by `date`. Each post shows a "Part X of N" box and previous/next links, the post list shows the series name, and every series gets a page under `/series/`. The "series" link in the header only appears once at least one published post belongs to a series.

The `demo-emulator-*.md` posts are drafts that show the feature. Preview them locally with `zola serve --drafts`; they are left out of normal builds. Delete them before or after merging.

## Windows

Install Zola with `winget install getzola.zola` (or `scoop install zola` / `choco install zola`) and Python with `winget install Python.Python.3.12`, then open a new terminal. Use `py` in place of `python3` (for example `py tools\obsidian_to_zola.py "My Note.md"`). Preview with `zola serve --drafts`.

## Writing posts in Obsidian

`tools/obsidian_to_zola.py` turns one Obsidian note into a Zola post (Python 3, no dependencies).

```sh
python3 tools/obsidian_to_zola.py "My Note.md"            # writes content/posts/<slug>.md
python3 tools/obsidian_to_zola.py "My Note.md" --dry-run  # print the result, write nothing
```

Put the note's images next to it (a subfolder is fine); they are copied to `static/images/<slug>/`. Optional properties on the note:

```yaml
---
title: My Post          # defaults to the first "# Heading", then the file name
date: 2026-11-20        # defaults to `created`, then the file's modified date
description: One line.
series: Building a Tiny Emulator
tags: [rust, emulation]
draft: true             # keeps it out of the published site
---
```

What gets converted:

| In Obsidian | On the site |
|---|---|
| YAML properties | TOML front matter (`series` becomes a series, `tags` go in `extra.tags`) |
| `[[Other Post]]`, `[[Post#Heading\|text]]` | Zola internal links, checked at build time |
| `[[Note]]` that isn't a published post | plain text, with a warning |
| `![[image.png]]`, `![[image.png\|300]]` | copied image, with width if given |
| `> [!tip] Title` callouts | bold-titled blockquotes |
| `==highlight==` | `<mark>` |
| `%%comment%%`, `^block-ids` | removed |
| `{{`, `{%`, `{#` | escaped, since Zola runs post content through its template engine |

The post is overwritten on each run, so edit the note, not the generated file. Not supported: note embeds (`![[Note]]`), math, and Dataview.
