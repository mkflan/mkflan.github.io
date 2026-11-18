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

## Writing posts in Obsidian

`tools/obsidian_to_zola.py` turns Obsidian notes into Zola posts (Python 3, no dependencies).

```sh
python3 tools/obsidian_to_zola.py ~/Vault/Blog            # every note in the folder with `publish: true`
python3 tools/obsidian_to_zola.py ~/Vault/Blog/My\ Note.md # one note, regardless of `publish`
python3 tools/obsidian_to_zola.py ~/Vault/Blog --dry-run   # preview without writing anything
```

Give a note these properties (all optional except where noted):

```yaml
---
title: My Post          # defaults to the first "# Heading", then the file name
date: 2026-11-20        # defaults to `created`, then the file's modified date
description: One line.
series: Building a Tiny Emulator
tags: [rust, emulation]
publish: true           # needed for folder conversion; ignored when you pass one file
draft: true             # keeps it out of the published site
---
```

What gets converted:

| In Obsidian | On the site |
|---|---|
| YAML properties | TOML front matter (`series` becomes a series, `tags` go in `extra.tags`) |
| `[[Other Post]]`, `[[Post#Heading\|text]]` | Zola internal links, checked at build time |
| `[[Note]]` that isn't a published post | plain text, with a warning |
| `![[image.png]]`, `![[image.png\|300]]` | copied to `static/images/<post>/`, with width if given |
| `> [!tip] Title` callouts | bold-titled blockquotes |
| `==highlight==` | `<mark>` |
| `%%comment%%`, `^block-ids` | removed |
| `{{`, `{%`, `{#` | escaped, since Zola runs post content through its template engine |

Posts are written to `content/posts/<slug>.md` and overwritten on each run, so edit the note, not the generated file. Not supported: note embeds (`![[Note]]`), math, Dataview, and canvas files.
